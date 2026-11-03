"""Редкие локальные реплики CS2: без вызовов языковой модели."""
import random
import time
import threading

class Commentator:
    def __init__(self,chance=.10,cooldown=20,clock=time.monotonic,rng=random.random):
        self.chance=chance;self.cooldown=cooldown;self.clock=clock;self.rng=rng
        self.kill_baseline=None;self.previous=None;self.last_spoken=-1e9;self.lock=threading.Lock()

    def update(self,data,quiet=False):
        with self.lock:return self._update(data,quiet)

    def _update(self,data,quiet):
        player=data.get('player',{});game=data.get('map',{});provider=data.get('provider',{});round_=data.get('round',{})
        if (str(provider.get('appid'))!='730' or not provider.get('steamid') or player.get('steamid')!=provider['steamid'] or
            game.get('phase')!='live' or player.get('activity')!='playing'):
            return None
        total=player.get('match_stats',{}).get('kills')
        roundkills=player.get('state',{}).get('round_kills')
        counter=total if isinstance(total,int) else roundkills
        counter_key=(game.get('name'),player['steamid'],'match' if isinstance(total,int) else game.get('round'))
        old_counter=self.kill_baseline
        if isinstance(counter,int):self.kill_baseline=(counter_key,counter)
        delta=0
        if isinstance(counter,int) and old_counter and old_counter[0]==counter_key:
            delta=max(0,counter-old_counter[1])
        if delta and not quiet:
            self.previous=((game.get('name'),game.get('round'),player['steamid']),roundkills,player.get('state',{}).get('health'),round_.get('phase'))
            phrases={1:'Минус один.',2:'Двойное убийство.',3:'Тройное убийство!',4:'Четверо!'}
            events=[]
            for i in range(delta):
                number=roundkills-delta+i+1 if isinstance(roundkills,int) else 1
                events.append({'type':'kill','text':phrases.get(number,'Ещё один минус!')})
            return events
        state=player.get('state',{});kills=state.get('round_kills');health=state.get('health');number=game.get('round')
        if not all(isinstance(v,int) for v in (kills,health,number)):return None
        key=(game.get('name'),number,player['steamid'])
        current=(key,kills,health,round_.get('phase'))
        old=self.previous;self.previous=current
        if old is None or old[0]!=key:return None
        phrase=None
        if round_.get('phase')=='over' and old[3]!='over':
            winner=round_.get('win_team')
            if winner in ('CT','T') and player.get('team') in ('CT','T'):
                phrase='Раунд наш. Красиво сработано.' if winner==player['team'] else 'Раунд отдали. Следующий забираем.'
        elif round_.get('phase')=='live':
            if health==0 and old[2]>0:phrase='Бывает, сэр. Следующий раунд — новая попытка.'
            elif kills>old[1]:phrase=('Три за раунд. Хороший темп, сэр.' if kills==3 else 'Четверо. Остался последний.' if kills==4 else 'Хороший выстрел, сэр.')
        now=self.clock()
        if quiet:
            self.last_spoken=now;return None
        if phrase and now-self.last_spoken>=self.cooldown and self.rng()<self.chance:
            self.last_spoken=now;return phrase
        return None
