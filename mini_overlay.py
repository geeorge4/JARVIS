import tkinter as tk

class MiniOverlay:
    def __init__(self,app):
        self.app=app
        self.window=tk.Toplevel(app.root);self.window.title('JARVIS Overlay')
        self.window.geometry(f'420x240+{max(0,app.root.winfo_screenwidth()-450)}+60')
        self.window.overrideredirect(True);self.window.attributes('-topmost',True)
        self.window.attributes('-alpha',.95);self.window.configure(bg='#15212a',highlightbackground='#52748b',highlightthickness=1)
        bar=tk.Frame(self.window,bg='#203340');bar.pack(fill='x')
        title=tk.Label(bar,text='JARVIS  ·  Ctrl+Shift+O',bg='#203340',fg='#b8d3e6');title.pack(side='left',padx=10,pady=7)
        tk.Button(bar,text='×',command=self.hide,bg='#203340',fg='white',bd=0).pack(side='right')
        def down(e):self.drag=(e.x_root-self.window.winfo_x(),e.y_root-self.window.winfo_y())
        def move(e):self.window.geometry(f'+{e.x_root-self.drag[0]}+{e.y_root-self.drag[1]}')
        for widget in (bar,title):widget.bind('<Button-1>',down);widget.bind('<B1-Motion>',move)
        self.answer=tk.Text(self.window,bg='#15212a',fg='#d3e3ef',relief='flat',wrap='word',height=5,font=('Segoe UI',11),state='disabled')
        self.answer.pack(fill='both',expand=True,padx=10,pady=7)
        row=tk.Frame(self.window,bg='#15212a');row.pack(fill='x',padx=10,pady=(0,10))
        self.entry=tk.Entry(row,bg='#243a49',fg='white',insertbackground='white',relief='flat',font=('Segoe UI',11));self.entry.pack(side='left',fill='x',expand=True,ipady=7)
        self.entry.bind('<Return>',lambda e:self.send())
        tk.Button(row,text='➤',command=self.send,bg='#29485c',fg='white',bd=0).pack(side='left',padx=4)
        tk.Button(row,text='Микр.',command=self.mic,bg='#29485c',fg='white',bd=0).pack(side='left')
        tk.Button(row,text='Dust2',command=self.lineups,bg='#29485c',fg='white',bd=0).pack(side='left',padx=4)
        self.window.bind('<Escape>',lambda e:self.hide())
        self.set_answer(app.last_answer or 'Введи команду. Esc — скрыть оверлей.');self.entry.focus_force()

    def set_answer(self,text):
        self.answer.configure(state='normal');self.answer.delete('1.0','end');__import__('chat_format').insert(self.answer,text);self.answer.configure(state='disabled')

    def lineups(self):
        self.app.open_lineups(self.entry.get().strip(), self.window)

    def send(self):
        if self.app.busy:self.set_answer('Джарвис занят — дождись ответа.');return
        text=self.entry.get().strip()
        if not text:return
        self.entry.delete(0,'end');self.set_answer('Выполняю: '+text)
        self.app.busy=True;self.app.status.set('Выполняю: '+text);self.app.jobs.put((False,text))

    def mic(self):
        if self.app.busy:self.set_answer('Джарвис занят — дождись ответа.');return
        self.set_answer('Слушаю 6 секунд…');self.app.busy=True;self.app.status.set('Слушаю…');self.app.jobs.put((True,''))

    def hide(self):self.window.withdraw()

    def toggle(self):
        if self.window.state()=='withdrawn':self.window.deiconify();self.window.lift();self.entry.focus_force()
        else:self.hide()
