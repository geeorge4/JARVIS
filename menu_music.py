"""CS2 menu-only looping audio, 30% sample amplitude."""
from pathlib import Path
import threading
import time
import wave
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'speech-deps'))
def in_menu(data):
    provider=data.get('provider',{});player=data.get('player',{});game=data.get('map',{})
    return (str(provider.get('appid'))=='730' and player.get('steamid')==provider.get('steamid') and bool(provider.get('steamid')) and player.get('activity')=='menu' and game.get('phase') not in ('live','warmup','intermission','gameover'))
class MenuMusic:
    def __init__(self,on_error=lambda text:None):
        self.active=threading.Event();self.closed=threading.Event();self.last_packet=0;self.on_error=on_error
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def update(self,enabled):
        self.last_packet=time.monotonic()
        if enabled:self.active.set()
        else:self.active.clear()
    def close(self):self.active.clear();self.closed.set()
    def run(self):
        import numpy as np
        import sounddevice as sd
        while not self.closed.is_set():
            if not self.active.wait(.2):continue
            try:
                with wave.open(str(Path(__file__).with_name('round-drops')/'menu.wav'),'rb') as wav:
                    with sd.RawOutputStream(samplerate=wav.getframerate(),channels=wav.getnchannels(),dtype='int16') as stream:
                        while self.active.is_set() and not self.closed.is_set():
                            if time.monotonic()-self.last_packet>25:self.active.clear();break
                            block=wav.readframes(2048)
                            if not block:wav.rewind();continue
                            samples=np.frombuffer(block,dtype='<i2')
                            stream.write((samples.astype(np.float32)*.3).astype('<i2').tobytes())
            except Exception as exc:
                self.active.clear();self.on_error('Музыка меню: '+str(exc))
