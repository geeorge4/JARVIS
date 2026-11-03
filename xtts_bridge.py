import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import wave

ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'JARVISASSISTENT'

class VoiceNotCached(RuntimeError):pass

class XttsVoice:
    def __init__(self):self.process=None;self.timer=None;self.lock=threading.Lock()
    def cancel(self):
        if self.timer:self.timer.cancel();self.timer=None
        process=self.process;self.process=None
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill()
    def render(self,text,speed=1.0,cache_only=False):
        import numpy as np
        # Умеренный темп модели, английская фраза эйса — на английском.
        language='en' if text.isascii() and any(c.isalpha() for c in text) else 'ru'
        key=hashlib.sha256(json.dumps([text,speed,language,'ref-v3'],ensure_ascii=False).encode()).hexdigest()
        cache=DATA/'xtts-cache';cache.mkdir(parents=True,exist_ok=True);target=cache/(key+'.wav')
        with self.lock:
            if self.timer:self.timer.cancel();self.timer=None
            if not target.exists():
                if cache_only:raise VoiceNotCached('Фраза не кеширована; тяжёлый синтез пропущен ради FPS.')
                if self.process is None or self.process.poll() is not None:
                    log=(DATA/'xtts.log').open('ab')
                    try:
                        self.process=subprocess.Popen([str(ROOT/'xtts-runtime'/'Scripts'/'python.exe'),str(ROOT/'xtts_worker.py'),str(ROOT/'xtts-model'),str(ROOT/'xtts-reference.wav')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    finally:log.close()
                process=self.process
                temp=target.with_suffix('.part.wav')
                watchdog=threading.Timer(180,self.cancel);watchdog.daemon=True;watchdog.start()
                try:
                    process.stdin.write(json.dumps({'text':text,'language':language,'speed':speed,'output':str(temp)},ensure_ascii=True)+'\n');process.stdin.flush()
                    line=process.stdout.readline()
                finally:watchdog.cancel()
                if not line:raise RuntimeError('XTTS остановлен или не смог загрузиться.')
                result=json.loads(line)
                if not result.get('ok'):raise RuntimeError(result.get('error','Ошибка XTTS'))
                temp.replace(target)
            self.timer=threading.Timer(45,self.cancel);self.timer.daemon=True;self.timer.start()
            with wave.open(str(target),'rb') as wav:
                audio=np.frombuffer(wav.readframes(wav.getnframes()),np.int16).astype(np.float32)/32768
                return audio,wav.getframerate()
