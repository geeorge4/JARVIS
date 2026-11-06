"""Настройки, первый запуск и заметки к версии."""
import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

VERSION = '2.6.0'
CHANGES = ('Тренер Dust2 сохраняет раскидки со скринами, ищет их из оверлея и помогает тренироваться по памяти.')
PREFS = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'JARVISASSISTENT' / 'settings.json'

def load():
    try:
        data = json.loads(PREFS.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def save(**changes):
    data = load(); data.update(changes)
    PREFS.parent.mkdir(parents=True, exist_ok=True)
    temp = PREFS.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    temp.replace(PREFS)

def welcome(force=False):
    prefs = load()
    if prefs.get('setup_done') and not force: return True
    window = tk.Tk(); window.title('Добро пожаловать в JARVIS')
    window.geometry('520x470'); window.configure(bg='#181818')
    result = False
    tk.Label(window, text='Давайте настроим всё\nпо вашему вкусу', bg='#181818', fg='white',
             font=('Segoe UI', 20, 'bold')).pack(pady=20)
    from user_memory import Memory
    memory = Memory()
    tk.Label(window, text='Как к вам обращаться? (необязательно)', bg='#181818', fg='#bbb').pack()
    name = tk.Entry(window, font=('Segoe UI',12)); name.insert(0,memory.name); name.pack(pady=8)
    voice = tk.BooleanVar(value=prefs.get('voice_output',True))
    wake = tk.BooleanVar(value=prefs.get('wake_enabled',True))
    for text,var in [('Озвучивать ответы локальным голосом',voice),('Слушать слово «Джарвис» в фоне',wake)]:
        tk.Checkbutton(window,text=text,variable=var,bg='#181818',fg='white',selectcolor='#333').pack(pady=6)
    tk.Label(window,text='Микрофон и распознавание работают локально.',bg='#181818',fg='#999').pack()
    tk.Label(window,text='Показать поверх окон — сочетание клавиш',bg='#181818',fg='#bbb').pack(pady=(15,5))
    key=tk.Entry(window,font=('Segoe UI',12));key.insert(0,prefs.get('hotkey','Ctrl+J'));key.pack()
    def finish():
        nonlocal result
        try:
            from hotkey import parse
            parse(key.get())
            memory.name=name.get().strip()[:80];memory.save()
            save(setup_done=True,voice_output=voice.get(),wake_enabled=wake.get(),hotkey=key.get().strip())
        except (OSError,ValueError) as exc:
            messagebox.showerror('Настройка',str(exc),parent=window);return
        result=True;window.destroy()
    tk.Button(window,text='Готово — начать',command=finish,font=('Segoe UI',12)).pack(pady=20)
    window.mainloop();return result

def whats_new(parent, force=False):
    if load().get('seen_version') == VERSION and not force: return
    window=tk.Toplevel(parent);window.title('Что нового — JARVIS '+VERSION)
    window.geometry('520x320');window.configure(bg='#181818');window.transient(parent)
    tk.Label(window,text='Что нового · '+VERSION,bg='#181818',fg='white',font=('Segoe UI',19,'bold')).pack(pady=20)
    tk.Label(window,text=CHANGES,bg='#181818',fg='#ccc',wraplength=470,justify='left',font=('Segoe UI',11)).pack(padx=25,pady=10)
    def close():
        try:save(seen_version=VERSION)
        except OSError as exc:messagebox.showerror('Ошибка',str(exc),parent=window);return
        window.destroy()
    tk.Button(window,text='Понятно',command=close).pack(pady=15)
    window.protocol('WM_DELETE_WINDOW',close)
