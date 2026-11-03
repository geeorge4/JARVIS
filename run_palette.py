"""Окно запуска: локальный поиск и необязательный подбор через Ollama."""
import json
import queue
import threading
import tkinter as tk
import urllib.request
from app_launcher import Launcher, ALIASES
import workflows

def local_matches(text, names):
    query = Launcher.target(text) or ALIASES.get(text.lower().strip(), text.lower().strip())
    exact = [n for n in names if n == query]
    partial = [n for n in names if query and query in n and n not in exact]
    if exact or partial: return (exact + sorted(partial))[:8]
    import difflib
    return difflib.get_close_matches(query, names, n=8, cutoff=.4) if query else names[:8]

def ai_matches(text, names):
    from jarvis import Jarvis
    Jarvis.__new__(Jarvis).start_server()
    payload = {'model':'qwen3:4b-instruct','stream':False,'format':'json',
        'keep_alive':'30m','options':{'num_ctx':4096,'num_predict':180},
        'messages':[{'role':'system','content':
        'Выбери до 5 приложений из списка под задачу пользователя. '
        'Не выполняй команды. Верни JSON {"apps":["точное название"]}. Список: '+json.dumps(names,ensure_ascii=False)},
        {'role':'user','content':text[:1000]}]}
    req = urllib.request.Request('http://127.0.0.1:11435/api/chat',
        data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=90) as response: data=json.load(response)
    result=json.loads(data['message']['content']).get('apps',[])
    if not isinstance(result,list): return []
    return list(dict.fromkeys(n for n in result if isinstance(n,str) and n in names))[:5]

class RunPalette:
    def __init__(self, app):
        self.app=app;self.results=queue.Queue();self.tasks=queue.Queue();self.serial=0;self.options=[];self.names=[];self.saved=workflows.load('launcher-history.json',{'favorites':[],'recent':[]});self.closed=False;self.pending=None
        self.window=tk.Toplevel(app.root);self.window.title('JARVIS · Выполнить')
        self.window.geometry('600x370');self.window.configure(bg='#181818');self.window.attributes('-topmost',True)
        self.window.protocol('WM_DELETE_WINDOW',self.close);self.window.bind('<Escape>',lambda e:self.close())
        tk.Label(self.window,text='Что открыть или сделать?',bg='#181818',fg='white',font=('Segoe UI',17,'bold')).pack(pady=(18,10))
        self.entry=tk.Entry(self.window,bg='#292929',fg='white',insertbackground='white',relief='flat',font=('Segoe UI',14));self.entry.pack(fill='x',padx=20,ipady=8)
        self.entry.bind('<KeyRelease>',self.changed);self.entry.bind('<Return>',lambda e:self.execute());self.entry.bind('<Down>',self.select_first)
        self.list=tk.Listbox(self.window,bg='#202020',fg='#ddd',selectbackground='#40586a',relief='flat',font=('Segoe UI',12),height=7);self.list.pack(fill='both',expand=True,padx=20,pady=10)
        self.list.bind('<Double-Button-1>',lambda e:self.execute());self.list.bind('<Return>',lambda e:self.execute())
        self.status=tk.StringVar(value='Загружаю список приложений…');tk.Label(self.window,textvariable=self.status,bg='#181818',fg='#999',wraplength=560).pack()
        row=tk.Frame(self.window,bg='#181818');row.pack(pady=10)
        tk.Button(row,text='Предложить через ИИ',command=self.suggest).pack(side='left',padx=6)
        tk.Button(row,text='★ В избранное / убрать',command=self.favorite).pack(side='left',padx=6)
        tk.Button(row,text='Выполнить',command=self.execute).pack(side='left',padx=6)
        threading.Thread(target=self.worker,daemon=True).start();self.poll();self.window.lift();self.entry.focus_force()

    def worker(self):
        try:
            launcher=Launcher();launcher.refresh();names=sorted(launcher.apps)
            self.results.put(('index',0,names))
        except Exception as exc:self.results.put(('error',0,str(exc)));return
        while True:
            job=self.tasks.get()
            if job is None:return
            version,text=job
            try:self.results.put(('ai',version,ai_matches(text,names)))
            except Exception:self.results.put(('error',version,'ИИ не ответил. Локальный поиск доступен.'))

    def changed(self,event=None):
        if event and event.keysym in ('Up','Down','Return','Escape'):return
        self.serial+=1
        if self.pending:self.window.after_cancel(self.pending)
        self.pending=self.window.after(200,self.search)

    def search(self):
        self.pending=None
        if self.entry.get().strip():names=local_matches(self.entry.get(),self.names)
        else:names=list(dict.fromkeys(n for n in self.saved.get('favorites',[])+self.saved.get('recent',[]) + self.names if n in self.names))[:16]
        self.display(names)
        self.status.set('Enter — выполнить выбранное. ИИ подбирает приложения по описанию задачи.')

    def display(self,names):
        self.options=names;self.list.delete(0,'end')
        for name in names:self.list.insert('end',('★ ' if name in self.saved.get('favorites',[]) else '')+name)
        if names:self.list.selection_set(0)

    def favorite(self):
        selection=self.list.curselection()
        if not selection:return
        name=self.options[selection[0]];favorites=self.saved.setdefault('favorites',[])
        if name in favorites:favorites.remove(name)
        else:favorites.append(name)
        try:workflows.save('launcher-history.json',self.saved);self.display(self.options)
        except OSError:self.status.set('Не удалось сохранить избранное.')

    def suggest(self):
        if not self.names or not self.entry.get().strip():return
        self.serial+=1;self.tasks.put((self.serial,self.entry.get().strip()));self.status.set('ИИ подбирает варианты…')

    def select_first(self,event):
        if self.options:self.list.focus_set();self.list.selection_set(0)
        return 'break'

    def execute(self):
        if self.app.busy:self.status.set('Джарвис занят. Дождись завершения команды.');return
        selection=self.list.curselection()
        if not selection:self.status.set('Выбери найденное приложение. Для описания задачи нажми «Предложить через ИИ».');return
        name=self.options[selection[0]]
        from activation import mode
        if mode()!='full':self.status.set('Для запуска приложений нужен ключ.');return
        self.saved['recent']=([name]+[n for n in self.saved.get('recent',[]) if n!=name])[:10]
        try:workflows.save('launcher-history.json',self.saved)
        except OSError:pass
        self.app.run_action('открой '+name);self.close()

    def poll(self):
        if self.closed:return
        try:
            while True:
                kind,version,data=self.results.get_nowait()
                if kind=='index':self.names=data;self.search()
                elif version==self.serial:
                    if kind=='ai':self.display(data);self.status.set('Варианты ИИ. Выбери приложение и нажми Enter.' if data else 'Подходящих приложений не найдено.')
                    else:self.status.set(data)
        except queue.Empty:pass
        self.window.after(100,self.poll)

    def show(self):
        self.window.deiconify();self.window.lift();self.entry.focus_force()

    def close(self):
        self.closed=True;self.tasks.put(None)
        if self.pending:self.window.after_cancel(self.pending)
        self.window.destroy();self.app.palette=None
