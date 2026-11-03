"""Separate audio stream: kill effect does not cancel a victory anthem."""
from pathlib import Path
import queue
import threading
import wave
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'speech-deps'))
def amplify_pcm(block):
    import numpy as np
    samples=np.frombuffer(block,dtype='<i2').astype(np.int32)
    return np.clip(samples*2,-32768,32767).astype('<i2').tobytes()

class KillSound:
    def __init__(self,on_error=lambda text:None):
        self.jobs=queue.Queue(maxsize=8);self.closed=threading.Event();self.on_error=on_error
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def play(self):
        try:self.jobs.put_nowait(True)
        except queue.Full:pass
    def close(self):self.closed.set()
    def run(self):
        while not self.closed.is_set():
            try:self.jobs.get(timeout=.2)
            except queue.Empty:continue
            try:
                import sounddevice as sd
                with wave.open(str(Path(__file__).with_name('round-drops')/'kill.wav'),'rb') as wav:
                    with sd.RawOutputStream(samplerate=wav.getframerate(),channels=wav.getnchannels(),dtype='int16') as stream:
                        while not self.closed.is_set():
                            block=wav.readframes(2048)
                            if not block:break
                            stream.write(amplify_pcm(block))
            except Exception as exc:self.on_error('Звук килла: '+str(exc))
