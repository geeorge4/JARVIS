"""Локальный голос Piper и распознавание faster-whisper."""
import io
import threading
import time
from collections import deque
import wave
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / 'speech-deps'))
import numpy as np
import sounddevice as sd
from native_audio import pcm_rms
from piper import PiperVoice, SynthesisConfig


ROOT = Path(__file__).resolve().parent / 'speech-models'

class Speech:
    def __init__(self):
        self.tts = PiperVoice.load(str(ROOT / 'ru_RU-denis-medium.onnx'))
        from xtts_bridge import XttsVoice
        self.xtts=XttsVoice()
        self.on_error=lambda message:print(message)
        self.stt = None
        self.wake_stt = None
        self.wake_new_peak = 0.0
        self.generation = 0
        self.duck_until = 0
        self.closed = threading.Event()
        self.cache_notice=False
        self.tts_lock = threading.Lock()
        self.speaking = threading.Event()
        self.wake_stream = None
        self.wake_audio = deque(maxlen=30)
        self.wake_lock = threading.Lock()
        self.wake_last = 0
        self.wake_allowed = threading.Event(); self.wake_allowed.set()
        self.wake_control = threading.RLock()

    def interrupt(self, cancel_synthesis=True):
        if cancel_synthesis:self.xtts.cancel()
        self.generation += 1
        self.stop_wake()
        sd.stop()

    def speak(self, text, style="normal"):
        if self.closed.is_set():return
        self.interrupt(cancel_synthesis=self.speaking.is_set())
        generation = self.generation
        threading.Thread(target=self._speak, args=(text, generation, style), daemon=True).start()

    def _speak(self, text, generation, style="normal"):
        try:
            with self.tts_lock:
                if generation != self.generation or self.closed.is_set():return
                self.speaking.set()
                try:
                    from product import load
                    prefs=load()
                    volume=max(0.0,min(1.0,float(prefs.get('speech_volume',0.9))))
                    speed=max(0.7,min(1.5,float(prefs.get('speech_speed',1.0))))
                    base_speed=speed
                    if prefs.get('dynamic_voice',True):
                        if style=='victory':speed=min(1.5,speed*1.08)
                        elif style=='warning':speed=max(.7,speed*.9);volume*=.8
                        if time.monotonic()<self.duck_until:volume*=.25
                    if prefs.get('voice_engine','xtts')=='xtts':
                        try:
                            cache_only=prefs.get('gaming_lightweight',True) and (prefs.get('game_mode',False) or style in ('victory','warning'))
                            audio,rate=self.xtts.render(str(text),base_speed,cache_only=cache_only)
                            if generation != self.generation or self.closed.is_set():return
                            sd.play(audio*volume,int(rate*speed/base_speed));sd.wait();return
                        except Exception as exc:
                            from xtts_bridge import VoiceNotCached
                            if isinstance(exc,VoiceNotCached):
                                if not self.cache_notice:self.on_error(str(exc));self.cache_notice=True
                                # Cheap local fallback instead of silently dropping the answer.
                            elif generation != self.generation or self.closed.is_set():return
                            if not isinstance(exc,VoiceNotCached):
                                self.on_error('XTTS недоступен, использую запасной Denis: '+str(exc))
                    config=SynthesisConfig(volume=volume,length_scale=1.0/speed)
                    for chunk in self.tts.synthesize(str(text),syn_config=config):
                        if generation != self.generation or self.closed.is_set():return
                        sd.play(chunk.audio_float_array, chunk.sample_rate)
                        sd.wait()
                finally:self.speaking.clear()
        except Exception as exc:
            self.on_error('Ошибка озвучки: '+str(exc))

    def close(self):
        self.closed.set()
        self.wake_allowed.clear()
        self.interrupt()

    def prepare(self):
        if self.stt is None:
            from faster_whisper import WhisperModel
            self.stt = WhisperModel(str(ROOT / 'whisper-base'), device='cpu',
                                   compute_type='int8', cpu_threads=2,
                                   local_files_only=True)

    def prepare_wake(self):
        if self.wake_stt is None:
            from faster_whisper import WhisperModel
            model = ROOT / 'whisper-tiny'
            if not (model / 'model.bin').is_file():
                self.prepare()
                return self.stt
            self.wake_stt = WhisperModel(str(model), device='cpu', compute_type='int8',
                                         cpu_threads=1, local_files_only=True)
        return self.wake_stt

    def transcribe(self, audio, initial_prompt=None):
        self.prepare()
        segments, _ = self.stt.transcribe(audio, language='ru', beam_size=3,
                                          vad_filter=True, condition_on_previous_text=False,
                                          initial_prompt=initial_prompt)
        return ' '.join(s.text.strip() for s in segments).strip()

    def set_wake(self, enabled):
        if enabled:
            self.wake_allowed.set()
        else:
            self.wake_allowed.clear()
            self.stop_wake()

    def stop_wake(self):
        with self.wake_control:
            stream = self.wake_stream
            self.wake_stream = None
            if stream is not None:
                stream.close()
            with self.wake_lock:
                self.wake_audio.clear()
                self.wake_new_peak = 0.0

    @staticmethod
    def extract_wake(text):
        import re
        match = re.search(r'(?<!\w)(?:дж[аеэ]р[вф][иеы]с|jarvis|jervis)(?!\w)', text, re.I)
        return text[match.end():].strip(' ,.!?') if match else None

    def wake_phrase(self):
        if self.closed.is_set() or self.speaking.is_set() or not self.wake_allowed.is_set():
            return None
        model = self.prepare_wake()
        with self.wake_control:
            if not self.wake_allowed.is_set(): return None
            if self.wake_stream is None:
                def capture(indata, frames, timing, status):
                    block = indata[:, 0].copy()
                    peak = pcm_rms(block)
                    with self.wake_lock:
                        self.wake_audio.append(block)
                        self.wake_new_peak = max(self.wake_new_peak, peak)
                self.wake_stream = sd.InputStream(samplerate=16000, channels=1,
                    dtype='float32', blocksize=1600, callback=capture)
                self.wake_stream.start()
                self.wake_last = time.monotonic()
                return None
        if time.monotonic() - self.wake_last < 0.8:
            return None
        self.wake_last = time.monotonic()
        with self.wake_lock:
            if len(self.wake_audio) < 8:
                return None
            peak = self.wake_new_peak
            self.wake_new_peak = 0.0
            if peak < 0.0015:
                return None
            audio = np.concatenate(list(self.wake_audio))
        segments, _ = model.transcribe(audio, language='ru', beam_size=3,
            vad_filter=False, condition_on_previous_text=False,
            initial_prompt='Имя ассистента: Джарвис. Jarvis.')
        result = self.extract_wake(' '.join(segment.text for segment in segments))
        if not self.wake_allowed.is_set():
            return None
        if result is not None:
            self.stop_wake()
            if result and model is self.wake_stt:
                command = self.extract_wake(self.transcribe(audio, initial_prompt='Джарвис,'))
                result = command or ''
        return result

    def listen(self):
        self.interrupt()
        self.prepare()
        from voice_endpoint import EndOfSpeech
        endpoint=EndOfSpeech()
        blocks=[]
        with sd.InputStream(samplerate=16000,channels=1,dtype='float32',blocksize=1600) as stream:
            while not self.closed.is_set():
                data,overflowed=stream.read(1600)
                block=data[:,0].copy();blocks.append(block)
                if endpoint.feed(pcm_rms(block)):break
        if not endpoint.heard or self.closed.is_set():return ''
        return self.transcribe(np.concatenate(blocks))
