"""Local, bounded round-win sound playback (Windows mixer)."""
from pathlib import Path
import random
import winsound
import threading
import time
import wave
import json
from collections import deque

_music_until=0.0
_ace_generation=0
_recent_music=deque(maxlen=10)
_last_clip=None
_play_lock=threading.Lock()
class RoundWins:
    def __init__(self):self.last=None;self.seen=set()
    def update(self,data):
        game=data.get('map',{});player=data.get('player',{});provider=data.get('provider',{});round_=data.get('round',{})
        if str(provider.get('appid'))!='730' or not provider.get('steamid') or player.get('steamid')!=provider.get('steamid'):return False
        team=player.get('team')
        if team not in ('CT','T') or game.get('phase') not in ('live','gameover'):return False
        if game.get('mode') not in ('competitive','scrimcomp2v2','casual'):return False
        scores=tuple(game.get('team_'+side.lower(),{}).get('score') for side in ('CT','T'))
        current=(game.get('name'),player.get('steamid'),team,scores,round_.get('phase'),game.get('round'))
        old=self.last;self.last=current
        if not old or old[:3]!=current[:3]:return False
        index=0 if team=='CT' else 1
        scored=(all(isinstance(v,int) for v in scores+old[3]) and scores[index]==old[3][index]+1 and scores[1-index]==old[3][1-index])
        ended=round_.get('phase')=='over' and old[4] in ('live','freezetime') and round_.get('win_team')==team
        if not (scored or ended):return False
        # Scores identify a completed round even when map.round changes in the over packet.
        key=(current[0],current[1],sum(scores)) if all(isinstance(v,int) for v in scores) else (current[0],current[1],old[5] if ended else current[5])
        if key in self.seen:return False
        if len(self.seen)>256:self.seen.clear()
        self.seen.add(key);return True

def play():
    global _last_clip,_music_until
    with _play_lock:
        clips=list(Path(__file__).with_name('round-drops').glob('drop-*.wav'))
        if not clips:raise RuntimeError('Музыкальные фрагменты не найдены.')
        candidates=[path for path in clips if path!=_last_clip] or clips
        special=Path(__file__).with_name('round-drops')/'match-perfect-world.wav'
        path=special if special.is_file() and special!=_last_clip and random.random()<0.5 else random.choice(candidates)
        winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
        with wave.open(str(path)) as audio:_music_until=time.monotonic()+audio.getnframes()/audio.getframerate()
        _last_clip=path
        _recent_music.append(path.name)
        return path.name

def stop():
    global _ace_generation,_music_until
    with _play_lock:
        _ace_generation+=1;_music_until=0.0
        winsound.PlaySound(None,0)

class MatchWins:
    def __init__(self):
        self.key=None;self.armed=False;self.fired=False;self.team=None;self.mode=None;self.finished=False
    def update(self,data):
        game=data.get('map',{});player=data.get('player',{});provider=data.get('provider',{})
        if str(provider.get('appid'))!='730' or not provider.get('steamid'):return False
        # End-of-match scoreboard packets may omit player/team. Never adopt a spectator's team.
        if player.get('steamid') not in (None,provider.get('steamid')):return False
        if not game.get('name'):return False
        key=(game['name'],provider['steamid'])
        if key!=self.key or game.get('phase')=='warmup':
            self.key=key;self.armed=False;self.fired=False;self.team=None;self.mode=None;self.finished=False
        if game.get('mode'):self.mode=game['mode']
        if self.mode not in ('competitive','scrimcomp2v2','casual'):return False
        if player.get('steamid')==provider['steamid'] and player.get('team') in ('CT','T'):
            self.team=player['team']
        if game.get('phase')=='live':
            self.armed=True
        if game.get('phase')=='gameover':self.finished=True
        if not self.finished or not self.armed or self.fired or self.team not in ('CT','T'):return False
        scores={side:game.get('team_'+side.lower(),{}).get('score') for side in ('CT','T')}
        if not all(isinstance(v,int) for v in scores.values()):return False
        other='T' if self.team=='CT' else 'CT'
        # A tied/old terminal snapshot may be followed by the actual final score.
        if scores[self.team]<=scores[other]:return False
        self.fired=True
        return True

def play_match():
    global _music_until
    name='match-win.wav'
    path=Path(__file__).with_name('round-drops')/name
    if not path.is_file():raise RuntimeError('Гимн победы в матче не найден: '+name)
    with _play_lock:
        winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
        with wave.open(str(path)) as audio:_music_until=time.monotonic()+audio.getnframes()/audio.getframerate()
        _recent_music.append(path.name)
    return path.name

def after_ace(on_error=lambda text:None):
    global _ace_generation
    with _play_lock:
        _ace_generation+=1;generation=_ace_generation
    def worker():
        # The ace can precede the round result. Allow time for the anthem to begin.
        wait_for_anthem=time.monotonic()+20
        heard_music=False
        while True:
            with _play_lock:
                if generation!=_ace_generation:return
                now=time.monotonic()
                if _music_until>now:heard_music=True
                if (heard_music and now>=_music_until) or (not heard_music and now>=wait_for_anthem):
                    try:
                        path=Path(__file__).with_name('round-drops')/'ace.wav'
                        winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
                    except (OSError,RuntimeError) as exc:on_error('Звук эйса: '+str(exc))
                    return
            time.sleep(.1)
    threading.Thread(target=worker,daemon=True).start()

def track_name(filename):
    special={'match-perfect-world.wav':'Ay Hey — Perfect World','match-win.wav':'Bang Bang Bang — победа в матче'}
    if filename in special:return special[filename]
    try:
        items=json.loads((Path(__file__).with_name('round-drops')/'clips.json').read_text(encoding='utf-8'))
        for item in items:
            if item.get('file')==filename:return Path(item['source']).stem
    except (OSError,ValueError,KeyError):pass
    return filename

def music_command(text):
    global _music_until
    low=text.casefold().replace('ё','е').strip(' .!?')
    with _play_lock:
        if low=='останови музыку джарвиса':
            pass
        elif low in ('что за гимн','что сейчас играло','какой гимн играл'):
            return 'Последний гимн: '+track_name(_recent_music[-1]) if _recent_music else 'Гимны ещё не играли после запуска JARVIS.'
        elif low=='история гимнов':
            return '\n'.join(str(i+1)+'. '+track_name(name) for i,name in enumerate(reversed(_recent_music))) if _recent_music else 'История гимнов пока пуста.'
        elif low=='повтори гимн':
            if not _recent_music:return 'Сначала выиграй раунд — затем смогу повторить его гимн.'
            path=Path(__file__).with_name('round-drops')/_recent_music[-1]
            winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
            with wave.open(str(path)) as audio:_music_until=time.monotonic()+audio.getnframes()/audio.getframerate()
            return 'Повторяю: '+track_name(path.name)
        else:return None
    stop();return 'Музыка Джарвиса остановлена.'
