import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

ROOT=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'JARVISASSISTENT'
DEFAULTS={'я играю':['игровой режим вкл','открой Steam','открой Discord'],
          'я работаю':['игровой режим выкл','открой Visual Studio Code','открой браузер']}

def load(name, default):
    try:
        data=json.loads((ROOT/name).read_text(encoding='utf-8'))
        return data if isinstance(data,type(default)) else default
    except (OSError,ValueError):return default

def save(name,data):
    ROOT.mkdir(parents=True,exist_ok=True);p=ROOT/name;t=p.with_suffix('.tmp')
    t.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');t.replace(p)

def scenarios():return load('scenarios.json',DEFAULTS.copy())

def validate(lines):
    actions=[line.strip() for line in lines.splitlines() if line.strip()]
    if not actions or len(actions)>12:raise ValueError('Нужно от 1 до 12 действий.')
    for action in actions:
        if action not in ('игровой режим вкл','игровой режим выкл') and not action.lower().startswith(('открой ','запусти ')):
            raise ValueError('Допустимо: открой название, запусти название, игровой режим вкл/выкл.')
    return actions

def editor(app):
    w=tk.Toplevel(app.root);w.title('Сценарии');w.geometry('560x460');w.configure(bg='#181818')
    tk.Label(w,text='Фраза запуска',bg='#181818',fg='white').pack(pady=8)
    name=tk.Entry(w,font=('Segoe UI',12));name.pack(fill='x',padx=20)
    choices=tk.Listbox(w,height=4);choices.pack(fill='x',padx=20,pady=8)
    actions=tk.Text(w,height=8,font=('Segoe UI',11));actions.pack(fill='both',expand=True,padx=20)
    tk.Label(w,text='Одна команда на строку. Пример: открой Telegram',bg='#181818',fg='#aaa').pack(pady=5)
    def refresh():
        choices.delete(0,'end')
        for key in scenarios():choices.insert('end',key)
    def select(event):
        if not choices.curselection():return
        key=choices.get(choices.curselection()[0]);name.delete(0,'end');name.insert(0,key)
        actions.delete('1.0','end');actions.insert('1.0','\n'.join(scenarios()[key]))
    choices.bind('<<ListboxSelect>>',select)
    def store():
        try:
            key=name.get().strip().lower()
            if not key:raise ValueError('Укажи фразу запуска.')
            data=scenarios();data[key]=validate(actions.get('1.0','end'));save('scenarios.json',data);refresh()
        except (ValueError,OSError) as exc:messagebox.showerror('Сценарий',str(exc),parent=w)
    def delete():
        try:
            data=scenarios();data.pop(name.get().strip().lower(),None);save('scenarios.json',data);refresh()
        except OSError as exc:messagebox.showerror('Сценарий',str(exc),parent=w)
    row=tk.Frame(w);row.pack(pady=8)
    tk.Button(row,text='Сохранить',command=store).pack(side='left')
    tk.Button(row,text='Удалить',command=delete).pack(side='left')
    tk.Button(row,text='Запустить',command=lambda:app.run_action(name.get().strip())).pack(side='left')
    refresh()
