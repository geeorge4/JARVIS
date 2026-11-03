"""Дополнительные локальные команды без генерации shell-кода."""
import ctypes
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
import urllib.parse
import webbrowser

SITES={'ютуб':'https://www.youtube.com','гугл':'https://www.google.com',
 'яндекс':'https://ya.ru','википедию':'https://ru.wikipedia.org','гитхаб':'https://github.com',
 'роблокс':'https://www.roblox.com','твич':'https://www.twitch.tv','дискорд сайт':'https://discord.com/app',
 'телеграм сайт':'https://web.telegram.org','почту gmail':'https://mail.google.com',
 'яндекс музыку':'https://music.yandex.ru','яндекс карты':'https://yandex.ru/maps',
 'гугл переводчик':'https://translate.google.com','гугл диск':'https://drive.google.com'}
SETTINGS={'настройки звука':'sound','настройки микрофона':'privacy-microphone',
 'настройки экрана':'display','настройки блютуза':'bluetooth','настройки вайфая':'network-wifi',
 'настройки сети':'network','настройки мыши':'mousetouchpad','настройки клавиатуры':'typing',
 'настройки громкости':'apps-volume','настройки персонализации':'personalization',
 'настройки приложений':'appsfeatures','настройки уведомлений':'notifications',
 'настройки питания':'powersleep','обновления windows':'windowsupdate'}
FOLDERS={'фото':'Pictures','видео':'Videos','музыку':'Music','загрузки':'Downloads',
 'документы':'Documents','рабочий стол':'Desktop'}
MEDIA={'громче':0xAF,'тише':0xAE,'выключи звук':0xAD,'включи звук':0xAD,
 'переключи звук':0xAD,'музыка пауза':0xB3,'музыка играть':0xB3,
 'следующий трек':0xB0,'предыдущий трек':0xB1,'останови музыку':0xB2}
# Команды mute и play/pause — переключатели, как мультимедийные клавиши.
FIXED=['который час','какая дата','какой день недели','сколько места на диске',
 'информация о компьютере','сколько оперативной памяти','заряд батареи',
 'открой диспетчер задач','открой сведения о системе','сделай скриншот',
 'открой папку скриншотов','запиши заметку купить молоко','покажи заметки',
 'найди заметку молоко','поставь таймер на 5 минут','список таймеров','отмени таймеры',
 'найди в интернете Python','найди на ютубе музыка']
CATALOG=([f'открой {n}' for n in SITES]+[f'открой {n}' for n in SETTINGS]+
         [f'открой папку {n}' for n in FOLDERS]+list(MEDIA)+FIXED)

def norm(text):return re.sub(r'\s+',' ',text.lower().replace('ё','е')).strip(' .!?')

class Extras:
    def __init__(self,notify):
        self.notify=notify;self.started=time.monotonic();self.timers={};self.lock=threading.Lock();self.next_id=1
        self.data=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'JARVISASSISTENT'

    def notes(self):
        try:
            data=json.loads((self.data/'notes.json').read_text(encoding='utf-8'))
            return data if isinstance(data,list) else []
        except (OSError,ValueError):return []

    def recognized(self,text):
        s=norm(text)
        return (s in CATALOG or s in ('громкость выше','громкость ниже','дата','время','снимок экрана') or
          s.startswith(('запиши заметку ','найди заметку ','поставь таймер ','таймер ',
                        'найди в интернете ','найди на ютубе ','поиск в интернете ')))

    def handle(self,text):
        s=norm(text)
        if s.startswith('открой '):
            name=s[7:]
            if name in SITES:webbrowser.open(SITES[name]);return 'Открываю сайт.'
            if name in SETTINGS:os.startfile('ms-settings:'+SETTINGS[name]);return 'Открываю параметры Windows.'
            if name.startswith('папку ') and name[6:] in FOLDERS:
                path=Path.home()/FOLDERS[name[6:]]
                if not path.is_dir():return 'Папка не найдена по стандартному пути: '+str(path)
                os.startfile(str(path));return 'Открываю папку.'
        if s in MEDIA or s in ('громкость выше','громкость ниже'):
            key=MEDIA.get(s,0xAF if s=='громкость выше' else 0xAE)
            ctypes.windll.user32.keybd_event(key,0,0,0);ctypes.windll.user32.keybd_event(key,0,2,0)
            return 'Отправил мультимедийную команду.'
        now=dt.datetime.now()
        if s in ('который час','время'):return now.strftime('%H:%M')
        if s in ('какая дата','дата'):return now.strftime('%d.%m.%Y')
        if s=='какой день недели':return ['Понедельник','Вторник','Среда','Четверг','Пятница','Суббота','Воскресенье'][now.weekday()]
        if s=='сколько места на диске':
            disk=shutil.disk_usage(Path.home().anchor);return f'На диске свободно {disk.free/2**30:.1f} ГБ из {disk.total/2**30:.1f} ГБ.'
        if s in ('информация о компьютере','сколько оперативной памяти','заряд батареи'):
            import sys
            sys.path.insert(0,str(self.data/'app-deps'))
            import psutil,platform
            if s=='информация о компьютере':return f'{platform.system()} {platform.release()}, процессор: {platform.processor()}, логических ядер: {os.cpu_count()}.'
            if s=='сколько оперативной памяти':
                ram=psutil.virtual_memory();return f'ОЗУ: {ram.total/2**30:.1f} ГБ, доступно {ram.available/2**30:.1f} ГБ.'
            battery=psutil.sensors_battery()
            return (f'Заряд {battery.percent:.0f}%, '+('питание подключено.' if battery.power_plugged else 'работа от батареи.')) if battery else 'Батарея не обнаружена.'
        if s in ('открой диспетчер задач','открой сведения о системе'):
            subprocess.Popen(['taskmgr.exe' if s=='открой диспетчер задач' else 'msinfo32.exe']);return 'Отправил команду запуска.'
        screenshots=self.data/'Screenshots'
        if s=='открой папку скриншотов':screenshots.mkdir(parents=True,exist_ok=True);os.startfile(str(screenshots));return 'Открываю скриншоты.'
        if s in ('сделай скриншот','снимок экрана'):
            import sys
            sys.path.insert(0,str(Path(__file__).resolve().parent/'tray-deps'))
            from PIL import ImageGrab
            screenshots.mkdir(parents=True,exist_ok=True);path=screenshots/(now.strftime('%Y-%m-%d_%H-%M-%S_%f')+'.png')
            ImageGrab.grab(all_screens=True).save(path);return 'Скриншот сохранён: '+str(path)
        if s.startswith('запиши заметку '):
            value=text.strip()[len('запиши заметку '):].strip()
            if not value:return 'Продиктуй текст заметки.'
            notes=self.notes();notes.append({'text':value[:4000],'date':now.isoformat(timespec='seconds')});notes=notes[-200:]
            self.data.mkdir(parents=True,exist_ok=True);p=self.data/'notes.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(notes,ensure_ascii=False),encoding='utf-8');tmp.replace(p)
            return 'Заметка записана.'
        if s=='покажи заметки' or s.startswith('найди заметку '):
            notes=self.notes();query=s[len('найди заметку '):] if s.startswith('найди заметку ') else ''
            matches=[n for n in notes if isinstance(n,dict) and query in norm(str(n.get('text','')))][-10:]
            return '\n'.join(f"{i+1}. {n['text']}" for i,n in enumerate(matches)) or 'Заметки не найдены.'
        if s.startswith(('найди в интернете ','поиск в интернете ','найди на ютубе ')):
            youtube=s.startswith('найди на ютубе ');prefix='найди на ютубе ' if youtube else ('найди в интернете ' if s.startswith('найди в интернете ') else 'поиск в интернете ')
            query=text.strip()[len(prefix):].strip()
            webbrowser.open(('https://www.youtube.com/results?search_query=' if youtube else 'https://www.google.com/search?q=')+urllib.parse.quote_plus(query));return 'Открываю результаты поиска.'
        if s.startswith(('таймер ','поставь таймер ')):
            numbers={'один':'1','одну':'1','одна':'1','два':'2','две':'2','три':'3','четыре':'4','пять':'5','шесть':'6','семь':'7','восемь':'8','девять':'9','десять':'10','пятнадцать':'15','тридцать':'30'}
            for word,value in numbers.items():s=re.sub(r'\b'+word+r'\b',value,s)
            match=re.fullmatch(r'(?:поставь )?таймер (?:на )?(\d+)\s*(секунд[аыу]?|сек|минут[ауы]?|мин|час(?:а|ов)?)',s)
            if not match:return 'Пример: таймер 30 секунд, таймер 5 минут или таймер 1 час.'
            amount=int(match.group(1));unit=match.group(2);seconds=amount*(3600 if unit.startswith('час') else 60 if unit.startswith('мин') else 1)
            if not 1<=seconds<=86400:return 'Таймер можно поставить от 1 секунды до 24 часов.'
            with self.lock:
                if len(self.timers)>=20:return 'Уже работают 20 таймеров.'
                identifier=self.next_id;self.next_id+=1
                def done():
                    with self.lock:
                        if identifier not in self.timers:return
                        self.timers.pop(identifier)
                    self.notify(f'Таймер {identifier} завершён: {amount} {unit}.')
                timer=threading.Timer(seconds,done);timer.daemon=True;self.timers[identifier]=(timer,time.monotonic()+seconds);timer.start()
            return f'Таймер {identifier} поставлен на {amount} {unit}.'
        if s=='список таймеров':
            with self.lock:return '\n'.join(f'{i}: осталось {max(0,int(end-time.monotonic()))} сек.' for i,(_,end) in self.timers.items()) or 'Активных таймеров нет.'
        if s=='отмени таймеры':self.close();return 'Все таймеры отменены.'
        return None

    def close(self):
        with self.lock:
            for timer,_ in self.timers.values():timer.cancel()
            self.timers.clear()
