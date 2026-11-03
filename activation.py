"""Простая локальная активация, без сервера лицензий."""
import hashlib
import json
import os
from pathlib import Path
import tkinter as tk

KEYS = {hashlib.sha256(s.encode()).hexdigest() for s in
        ('activation-1', 'activation-2', 'BANGBANGCHICKENGANG')}
STATE = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'JARVISASSISTENT' / 'activation.json'

def valid(key):
    return hashlib.sha256(key.strip().encode()).hexdigest() in KEYS

def mode():
    try:
        data = json.loads(STATE.read_text(encoding='utf-8'))
        if data.get('license') in KEYS:
            return 'full'
        if data.get('mode') == 'free':
            return 'free'
    except (OSError, ValueError, AttributeError):
        pass
    return None

def save(data):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix('.tmp')
    temporary.write_text(json.dumps(data), encoding='utf-8')
    temporary.replace(STATE)

def reset():
    save({'mode': 'free'})

def activate(force=False):
    saved = mode()
    if saved and not force:
        return saved
    success = None
    window = tk.Tk()
    window.title('Активация JARVIS')
    window.geometry('440x340')
    window.resizable(False, False)
    window.configure(bg='#202020')
    tk.Label(window, text='Активация продукта', font=('Segoe UI', 19),
             bg='#202020', fg='white').pack(pady=(25, 10))
    tk.Label(window, text='Введите ключ активации JARVIS', bg='#202020',
             fg='#bcbcbc').pack()
    entry = tk.Entry(window, font=('Segoe UI', 13), bg='#363636', fg='white',
                     insertbackground='white', relief='flat')
    entry.pack(fill='x', padx=30, pady=15, ipady=7)
    message = tk.StringVar()
    tk.Label(window, textvariable=message, bg='#202020', fg='#ffb0a0').pack()
    def submit(event=None):
        nonlocal success
        key = entry.get().strip()
        if not valid(key):
            message.set('Неверный ключ. Проверьте ввод.')
            return
        try:
            save({'license': hashlib.sha256(key.encode()).hexdigest(), 'mode': 'full'})
        except OSError:
            message.set('Не удалось сохранить активацию. Попробуйте снова.')
            return
        success = 'full'
        window.destroy()
    tk.Button(window, text='Активировать', command=submit, bg='#465b6b',
              fg='white', relief='flat', font=('Segoe UI', 11)).pack(pady=8)
    def without_key():
        nonlocal success
        try:
            reset()
        except OSError:
            message.set('Не удалось сохранить режим.')
            return
        success = 'free'
        window.destroy()
    tk.Button(window, text='Без ключа — YouTube и вопросы', command=without_key,
              bg='#363636', fg='white', relief='flat').pack(pady=5)
    entry.bind('<Return>', submit)
    entry.focus_set()
    window.mainloop()
    return success
