"""Windows RegisterHotKey: без перехвата клавиатуры."""
import ctypes
from ctypes import wintypes
import queue
import threading

def parse(value):
    parts = [p.strip().upper() for p in value.split('+')]
    modifiers = {'CTRL': 2, 'ALT': 1, 'SHIFT': 4, 'WIN': 8}
    if len(parts) < 2 or len(set(parts)) != len(parts):
        raise ValueError('Пример: Ctrl+J или Ctrl+Shift+J')
    mask = 0
    for part in parts[:-1]:
        if part not in modifiers:
            raise ValueError('Используй Ctrl, Alt, Shift или Win.')
        mask |= modifiers[part]
    key = parts[-1]
    if len(key) == 1 and key in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789':
        vk = ord(key)
    elif key.startswith('F') and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        vk = 111 + int(key[1:])
    else:
        raise ValueError('Последняя клавиша: латинская буква, цифра или F1–F24.')
    return mask | 0x4000, vk

class Hotkey:
    def __init__(self, callback):
        self.callback = callback
        self.requests = queue.Queue()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def set(self, value):
        modifiers, key = parse(value)
        done = threading.Event()
        result = []
        self.requests.put((modifiers, key, done, result))
        if not done.wait(2):
            raise RuntimeError('Служба сочетаний не ответила.')
        if not result[0]:
            raise ValueError('Сочетание занято другой программой. Выбери другое.')

    def run(self):
        user32 = ctypes.windll.user32
        active = None
        current_id = 1
        msg = wintypes.MSG()
        try:
            while not self.stop_event.is_set():
                try:
                    modifiers, key, done, result = self.requests.get_nowait()
                    if active == (modifiers, key):
                        ok = True
                    else:
                        new_id = 2 if current_id == 1 else 1
                        ok = bool(user32.RegisterHotKey(None, new_id, modifiers, key))
                        if ok:
                            if active is not None:
                                user32.UnregisterHotKey(None, current_id)
                            active = (modifiers, key)
                            current_id = new_id
                    result.append(ok)
                    done.set()
                except queue.Empty:
                    pass
                while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    if msg.message == 0x0312:
                        self.callback()
                self.stop_event.wait(.04)
        finally:
            if active is not None:
                user32.UnregisterHotKey(None, current_id)

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=1)
