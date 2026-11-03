"""Bounded local game journal and observed CS2 session, no polling."""
import json
import os
from pathlib import Path
import threading
import time
from datetime import datetime
ROOT=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'JARVISASSISTANT'
LOCK=threading.RLock()
COMMANDS=('отчет сессии','отчет игры','игровой журнал','покажи игровой журнал','начать игровую сессию','завершить игровую сессию')
PREFIX='заметка о матче '
def read(name,default):
    try:return json.loads((ROOT/name).read_text(encoding='utf-8'))
    except (OSError,ValueError):return default
def write(name,data):
    ROOT.mkdir(parents=True,exist_ok=True);target=ROOT/name;temp=target.with_suffix('.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(target)
def fresh():
    return {'started':datetime.now().astimezone().isoformat(timespec='seconds'),'active_seconds':0,'kills':0,'deaths':0,'maps':[],'samples':0}
class Session:
    def __init__(self):self.data=read('game-session.json',{});self.previous=None;self.last_time=None;self.saved=0
    def update(self,packet):
        player=packet.get('player',{});provider=packet.get('provider',{});game=packet.get('map',{})
        if str(provider.get('appid'))!='730' or not provider.get('steamid') or player.get('steamid')!=provider['steamid'] or player.get('activity')!='playing':return
        if game.get('phase') not in ('live','gameover'):return
        with LOCK:
            if not self.data or self.data.get('ended'):self.data=fresh();self.previous=None;self.last_time=None
            now=time.monotonic();stats=player.get('match_stats',{});key=(game.get('name'),provider['steamid'])
            counter=tuple(stats.get(n) for n in ('kills','deaths'))
            if self.last_time is not None:self.data['active_seconds']+=min(15,max(0,now-self.last_time))
            if self.previous and self.previous[0]==key:
                for i,name in enumerate(('kills','deaths')):
                    old=self.previous[1][i];new=counter[i]
                    if isinstance(old,int) and isinstance(new,int):self.data[name]+=max(0,new-old)
            self.previous=(key,counter);self.last_time=now
            if game.get('name') and game['name'] not in self.data['maps']:self.data['maps'].append(game['name']);self.data['maps']=self.data['maps'][-30:]
            self.data['samples']+=1
            if now-self.saved>=30:self.save();self.saved=now
    def save(self):
        if self.data:write('game-session.json',self.data)
    def report(self):
        with LOCK:
            if not self.data:return 'Пока нет данных сессии. Запусти CS2 и зайди в матч.'
            self.save();d=self.data
            return ('Игровая сессия с '+d['started']+'\nНаблюдаемое игровое время: '+str(int(d['active_seconds']//60))+' мин.\nКиллы: '+str(d['kills'])+' · смерти: '+str(d['deaths'])+'\nКарты: '+(', '.join(d['maps']) or 'нет данных')+'\nУчитываются только изменения после подключения JARVIS. Время приблизительное; FPS и итоги матчей здесь не измеряются.')
session=Session()
def recognized(text):
    low=text.casefold().replace('ё','е').strip(' .!?')
    return low in COMMANDS or low.startswith(PREFIX)
def handle(text):
    low=text.casefold().replace('ё','е').strip(' .!?')
    with LOCK:
        if low.startswith(PREFIX):
            note=text.strip()[len(PREFIX):].strip()[:2000]
            if not note:return 'Продиктуй или напиши текст после «заметка о матче».'
            items=read('game-journal.json',[])
            if not isinstance(items,list):items=[]
            items.append({'date':datetime.now().astimezone().isoformat(timespec='seconds'),'text':note})
            write('game-journal.json',items[-200:]);return 'Заметка о матче сохранена локально.'
        if low in ('игровой журнал','покажи игровой журнал'):
            items=read('game-journal.json',[])
            return '\n\n'.join(str(item['date'])+'\n'+str(item['text']) for item in items[-10:]) if isinstance(items,list) and items else 'Игровой журнал пока пуст.'
        if low=='начать игровую сессию':
            session.data=fresh();session.previous=None;session.last_time=None;session.save();return 'Новая игровая сессия начата.'
        if low=='завершить игровую сессию':
            if session.data:session.data['ended']=datetime.now().astimezone().isoformat(timespec='seconds')
            return session.report()
        return session.report()
