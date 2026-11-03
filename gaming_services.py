"""Фоновые службы: локальная телеметрия WT и контроль ресурсов."""
import csv
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import product

def get_json(path):
    with urllib.request.urlopen('http://127.0.0.1:8111/'+path,timeout=.7) as r:return json.load(r)

class WTDetector:
    def __init__(self):self.seen=set();self.initial=True;self.last=-1e9;self.last_crash=-1e9
    def update(self,data,now=None):
        now=time.monotonic() if now is None else now;result=[]
        for group in ('events','damage'):
            for event in data.get(group,[]):
                if not isinstance(event,dict):continue
                key=(group,event.get('id'),event.get('time'),event.get('msg'))
                if key in self.seen:continue
                self.seen.add(key)
                if self.initial:continue
                text=re.sub(r'<[^>]+>','',str(event.get('msg',''))).lower()
                phrase=None
                if any(t in text for t in ('you have crashed','you crashed','вы разбились','вы столкнулись','ваш самолет разбился','ваш самолёт разбился')):
                    if now-self.last_crash>=15:
                        result.append(('Skill issue, back to the garage','crash'));self.last_crash=now
                    continue
                elif any(t in text for t in ('mission accomplished','victory','победа','миссия выполнена')):phrase=('Победа, сэр. Отличная работа.','victory')
                elif any(t in text for t in ('target destroyed','aircraft destroyed','цель уничтожена','техника уничтожена','самолет уничтожен')):phrase=('Skill issue, back to the garage','destroyed')
                elif any(t in text for t in ('critical hit','критическое попадание','критический урон')):phrase=('Критическое попадание. Так держать.','victory')
                elif any(t in text for t in ('mission failed','поражение','миссия провалена')):phrase=('Не наш бой. Сделаем выводы и попробуем снова.','warning')
                if phrase and now-self.last>=15:result.append(phrase);self.last=now
        self.initial=False
        if len(self.seen)>2000:self.seen=set(list(self.seen)[-1000:])
        return result

def fps_from_csv(path):
    if not path:return None
    p=Path(path)
    if not p.is_file() or time.time()-p.stat().st_mtime>15:return None
    with p.open('r',encoding='utf-8-sig',errors='replace') as f:
        header=f.readline();size=p.stat().st_size
        if size>65536:f.seek(max(len(header),size-65536));f.readline()
        rows=list(csv.DictReader(io.StringIO(header+f.read())))[-120:]
    values=[]
    for row in rows:
        try:
            value=float(row.get('msBetweenPresents') or row.get('FrameTime') or row.get('CPUFrameTime') or 0)
            if 0<value<1000:values.append(value)
        except (ValueError,TypeError):pass
    return round(1000/(sum(values)/len(values))) if values else None

def sample_metrics(fps_path=''):
    sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'JARVISASSISTENT'/'app-deps'))
    import psutil
    result={'cpu':psutil.cpu_percent(),'ram':psutil.virtual_memory().percent,'gpu':None,'gpu_temp':None,'cpu_temp':None,'fps':None}
    sensors=getattr(psutil,'sensors_temperatures',lambda:{})()
    temps=[s.current for name,items in sensors.items() if 'cpu' in name.lower() or 'coretemp' in name.lower() for s in items]
    if temps:result['cpu_temp']=max(temps)
    executable=shutil.which('nvidia-smi')
    if executable:
        try:
            r=subprocess.run([executable,'--query-gpu=temperature.gpu,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=3,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            temp,load=r.stdout.strip().splitlines()[0].split(',');result['gpu_temp']=float(temp);result['gpu']=float(load)
        except (OSError,ValueError,IndexError,subprocess.TimeoutExpired):pass
    try:result['fps']=fps_from_csv(fps_path)
    except (OSError,ValueError):pass
    return result

class Guard:
    def __init__(self):self.paused=False;self.high_count=0;self.cool_count=0;self.gpu_hot=False;self.cpu_hot=False
    def update(self,m):
        if (m.get('gpu_temp') or 0)>=85:self.gpu_hot=True
        if (m.get('cpu_temp') or 0)>=95:self.cpu_hot=True
        hot=(m.get('gpu_temp') or 0)>=85 or (m.get('cpu_temp') or 0)>=95
        loaded=m.get('cpu',0)>=95 or m.get('ram',0)>=92
        self.high_count=self.high_count+1 if loaded else 0
        if hot or self.high_count>=3:self.paused=True;self.cool_count=0
        elif self.paused:
            cool=(not self.gpu_hot or (m.get('gpu_temp') is not None and m['gpu_temp']<80)) and (not self.cpu_hot or (m.get('cpu_temp') is not None and m['cpu_temp']<85)) and m.get('cpu',0)<85 and m.get('ram',0)<88
            self.cool_count=self.cool_count+1 if cool else 0
            if self.cool_count>=3:self.paused=False;self.gpu_hot=False;self.cpu_hot=False
        return self.paused

class Services:
    def __init__(self,events):
        self.events=events;self.stop=threading.Event();self.wt=WTDetector();self.guard=Guard()
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def run(self):
        last_metrics=0;last_wt=0
        while not self.stop.is_set():
            prefs=product.load();now=time.monotonic()
            if prefs.get('wt_mode',True) and now-last_wt>=4:
                last_wt=now
                try:
                    data=get_json('hudmsg?lastEvt=-1&lastDmg=-1')
                    for phrase,style in self.wt.update(data):self.events.put(('wt_comment',(phrase,style)))
                    self.events.put(('wt_status','War Thunder: подключён'))
                except (OSError,ValueError,TypeError,AttributeError):
                    self.events.put(('wt_status','War Thunder: ожидаю запуск игры'));self.wt=WTDetector();last_wt=now+5
            if prefs.get('performance_guard',True) and now-last_metrics>=15:
                last_metrics=now
                try:
                    metrics=sample_metrics(prefs.get('fps_csv',''));paused=self.guard.update(metrics)
                    self.events.put(('metrics',(metrics,paused)))
                except Exception:self.events.put(('metrics_error','Датчики недоступны'))
            elif not prefs.get('performance_guard',True):self.guard=Guard();self.events.put(('guard_off',''))
            self.stop.wait(1)
    def close(self):self.stop.set();self.thread.join(timeout=4)
