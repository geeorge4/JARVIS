import tkinter as tk
from tkinter import messagebox, filedialog
import math,threading,queue,time,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent / 'tray-deps'))
from jarvis import Jarvis
from collections import deque
import product
import workflows
from extra_commands import CATALOG
import windows_shell
DATA=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'JARVISASSISTENT'/'phrases.json'
PREFS=DATA.with_name('settings.json')
ACTIONS=['что за гимн','история гимнов','повтори гимн','отчет сессии','покажи игровой журнал','завершить игровую сессию','проверь сбои Windows','анализ синего экрана','прочитай экран','объясни ошибку на экране','открой ютуб','открой Steam','открой браузер','открой калькулятор','открой блокнот','открой проводник','открой настройки','открой загрузки','открой документы']
class App:
 def __init__(self):
  self.events=queue.Queue();self.jobs=queue.Queue();self.busy=False;self.angle=0;self.hidden=False;self.tray=None;self.assistant=None;self.wake_enabled=True;self.closing=False;self.voice_output=True;self.current='Орб';self.hotkey=None;self.run_hotkey=None;self.palette=None;self.overlay=None;self.overlay_hotkey=None;self.background_recording=False;self.last_answer='';self.draft_timer=None;self.ace_server=None;self.services=None;self.guard_paused=False;self.combat_until=0;self.kill_comments=deque()
  try:self.phrases=json.loads(DATA.read_text(encoding='utf-8'))
  except (OSError,ValueError):self.phrases={}
  if not isinstance(self.phrases,dict):self.phrases={}
  prefs=product.load();self.wake_enabled=prefs.get('wake_enabled',True);self.voice_output=prefs.get('voice_output',True);self.game_mode=prefs.get('game_mode',False)
  windows_shell.identity()
  self.root=tk.Tk();self.root.title('JARVIS');self.root.geometry(f'{min(920,self.root.winfo_screenwidth()-40)}x{min(720,self.root.winfo_screenheight()-100)}+20+20');self.root.configure(bg='#121212');self.root.overrideredirect(True)
  bar=tk.Frame(self.root,bg='#272727',height=32);bar.pack(fill='x');bar.pack_propagate(False)
  title=tk.Label(bar,text='JARVIS',bg='#272727',fg='#ddd');title.pack(side='left',padx=14)
  def down(e):self.drag=(e.x_root-self.root.winfo_x(),e.y_root-self.root.winfo_y())
  def move(e):self.root.geometry(f'+{e.x_root-self.drag[0]}+{e.y_root-self.drag[1]}')
  for w in (bar,title):w.bind('<Button-1>',down);w.bind('<B1-Motion>',move)
  self.button(bar,'✕',self.hide).pack(side='right');self.button(bar,'—',self.minimize).pack(side='right')
  shell=tk.Frame(self.root,bg='#121212');shell.pack(fill='both',expand=True)
  self.sidebar=tk.Frame(shell,bg='#151515',width=200);self.sidebar.pack(side='left',fill='y');self.sidebar.pack_propagate(False)
  tk.Label(self.sidebar,text='J A R V I S',font=('Segoe UI',16,'bold'),bg='#151515',fg='#eee').pack(pady=25)
  self.nav={};self.pages={}
  right=tk.Frame(shell,bg='#121212');right.pack(side='left',fill='both',expand=True)
  self.content=tk.Frame(right,bg='#121212');self.content.pack(fill='both',expand=True)
  for name in ['Орб','Нейрочат','Команды','Конструктор','Настройки']:
   b=self.button(self.sidebar,name,lambda n=name:self.page(n));b.pack(fill='x',padx=10,pady=5,ipady=9);self.nav[name]=b
   self.pages[name]=tk.Frame(self.content,bg='#121212')
  self.canvas=tk.Canvas(self.pages['Орб'],bg='#121212',highlightthickness=0);self.canvas.pack(fill='both',expand=True)
  from orb_view import Orb
  self.orb=Orb(self.canvas)
  chat=self.pages['Нейрочат'];self.heading(chat,'JARVIS','Спроси что угодно')
  tools=tk.Frame(chat,bg='#121212');tools.pack(pady=3)
  self.button(tools,'Копировать ответ',self.copy_answer).pack(side='left',padx=4)
  self.button(tools,'Сохранить переписку',self.export_chat).pack(side='left',padx=4)
  hints=tk.Frame(chat,bg='#121212');hints.pack(pady=8)
  for i,text in enumerate(['Объясни простыми словами','Помоги с текстом','Составь план на день','Разбери ошибку в коде']):
   self.button(hints,text,lambda t=text:self.prompt(t)).grid(row=i//2,column=i%2,padx=5,pady=5,ipady=7)
  self.chat_search=tk.Frame(chat,bg='#121212')
  self.search_entry=tk.Entry(self.chat_search,bg='#252525',fg='white',insertbackground='white',font=('Segoe UI',11));self.search_entry.pack(side='left',fill='x',expand=True,padx=5)
  self.search_count=tk.StringVar(value='');tk.Label(self.chat_search,textvariable=self.search_count,bg='#121212',fg='#aaa').pack(side='left')
  self.button(self.chat_search,'↓',self.next_match).pack(side='left');self.button(self.chat_search,'×',self.close_search).pack(side='left')
  self.search_matches=[];self.search_index=-1
  self.search_entry.bind('<KeyRelease>',lambda e:self.find_chat() if e.keysym!='Return' else None);self.search_entry.bind('<Return>',lambda e:self.next_match())
  self.answer=tk.Text(chat,bg='#121212',fg='#dedede',wrap='word',relief='flat',font=('Segoe UI',12),state='disabled',padx=15,pady=10);self.answer.pack(fill='both',expand=True,padx=10,pady=10)
  self.answer.tag_configure('found',background='#544d26',foreground='white');self.answer.tag_configure('current_match',background='#3a6580',foreground='white')
  self.answer.bind('<Control-a>',self.select_chat);self.answer.bind('<Control-A>',self.select_chat)
  self.answer.bind('<Control-c>',self.copy_selection);self.answer.bind('<Control-C>',self.copy_selection)
  self.chat_menu=tk.Menu(self.root,tearoff=False)
  self.chat_menu.add_command(label='Копировать выделенное',command=self.copy_selection)
  self.chat_menu.add_command(label='Выделить всё',command=self.select_chat)
  self.chat_menu.add_command(label='Копировать последний ответ',command=self.copy_answer)
  self.answer.bind('<Button-3>',lambda e:self.chat_menu.tk_popup(e.x_root,e.y_root))
  self.heading(self.pages['Команды'],'Команды','Нажми, чтобы выполнить.')
  self.commands_license=tk.StringVar()
  tk.Label(self.pages['Команды'],textvariable=self.commands_license,bg='#121212',fg='#9acba3').pack(pady=5)
  self.update_license_status()
  self.command_search=tk.Entry(self.pages['Команды'],bg='#252525',fg='white',insertbackground='white',font=('Segoe UI',12));self.command_search.pack(fill='x',padx=25,pady=8)
  self.command_list=tk.Listbox(self.pages['Команды'],bg='#202020',fg='#ddd',selectbackground='#40586a',relief='flat',font=('Segoe UI',12));self.command_list.pack(fill='both',expand=True,padx=25,pady=8)
  self.command_search.bind('<KeyRelease>',lambda e:self.filter_commands())
  self.command_list.bind('<Double-Button-1>',lambda e:self.choose_command());self.command_list.bind('<Return>',lambda e:self.choose_command())
  self.button(self.pages['Команды'],'Выбрать команду',self.choose_command).pack(pady=5)
  self.filter_commands()
  build=self.pages['Конструктор'];self.heading(build,'Конструктор','Своя фраза → существующая команда')
  self.phrase=tk.Entry(build,bg='#252525',fg='white',insertbackground='white',font=('Segoe UI',12));self.phrase.pack(fill='x',padx=30,pady=10)
  self.action=tk.StringVar(value=ACTIONS[0]);tk.OptionMenu(build,self.action,*ACTIONS).pack(fill='x',padx=30)
  self.button(build,'Сохранить фразу',self.save_phrase).pack(pady=12)
  self.phrase_list=tk.Listbox(build,bg='#202020',fg='#ddd',relief='flat',font=('Segoe UI',11));self.phrase_list.pack(fill='both',expand=True,padx=30,pady=10)
  self.button(build,'Удалить выбранную',self.delete_phrase).pack(pady=10);self.refresh_phrases()
  self.button(self.pages['Конструктор'],'Сценарии: создать / изменить',lambda:workflows.editor(self)).pack(pady=6,before=self.phrase_list)
  settings=self.scrollable_settings();self.heading(settings,'Настройки','Локальный ИИ · faster-whisper · Piper')
  from personality import STYLES
  tk.Label(settings,text='Характер Джарвиса',bg='#121212',fg='#ddd').pack(pady=(10,4))
  self.personality_var=tk.StringVar(value=prefs.get('personality','Адаптивный'))
  tk.OptionMenu(settings,self.personality_var,*STYLES,command=self.save_personality).pack(pady=5)
  self.wake_var=tk.BooleanVar(value=self.wake_enabled);self.sound_var=tk.BooleanVar(value=self.voice_output)
  tk.Checkbutton(settings,text='Активация словом Джарвис',variable=self.wake_var,command=self.sync_settings,bg='#121212',fg='#ddd',selectcolor='#333').pack(anchor='w',padx=30,pady=10)
  tk.Checkbutton(settings,text='Озвучивать ответы',variable=self.sound_var,command=self.sync_settings,bg='#121212',fg='#ddd',selectcolor='#333').pack(anchor='w',padx=30,pady=10)
  tk.Label(settings,text='Движок голоса',bg='#121212',fg='#ddd').pack(pady=5)
  self.voice_engine=tk.StringVar(value=prefs.get('voice_engine','xtts'))
  tk.OptionMenu(settings,self.voice_engine,'xtts','piper').pack()
  tk.Label(settings,text='Громкость голоса (%)',bg='#121212',fg='#ddd').pack(pady=(8,0))
  self.speech_volume=tk.Scale(settings,from_=0,to=100,orient='horizontal',resolution=5,bg='#121212',fg='#ddd',highlightthickness=0,length=300)
  self.speech_volume.set(prefs.get('speech_volume',.9)*100);self.speech_volume.pack()
  tk.Label(settings,text='Скорость голоса (×)',bg='#121212',fg='#ddd').pack()
  self.speech_speed=tk.Scale(settings,from_=.7,to=1.5,orient='horizontal',resolution=.05,bg='#121212',fg='#ddd',highlightthickness=0,length=300)
  self.speech_speed.set(prefs.get('speech_speed',1.0));self.speech_speed.pack()
  voice_buttons=tk.Frame(settings,bg='#121212');voice_buttons.pack(pady=5)
  self.button(voice_buttons,'Сохранить голос',self.save_voice).pack(side='left',padx=4)
  self.button(voice_buttons,'Проверить голос',self.test_voice).pack(side='left',padx=4)
  self.menu_music_var=tk.BooleanVar(value=prefs.get('cs2_menu_music',(Path(__file__).parent/'round-drops'/'menu.wav').is_file()))
  tk.Checkbutton(settings,text='CS2: музыка в меню (30%)',variable=self.menu_music_var,command=self.save_menu_music,bg='#121212',fg='#ddd',selectcolor='#333').pack(anchor='w',padx=30,pady=8)
  self.kill_sound_var=tk.BooleanVar(value=prefs.get('cs2_kill_sound',(Path(__file__).parent/'round-drops'/'kill.wav').is_file()))
  tk.Checkbutton(settings,text='CS2: звук за каждый килл',variable=self.kill_sound_var,command=lambda:product.save(cs2_kill_sound=self.kill_sound_var.get()),bg='#121212',fg='#ddd',selectcolor='#333').pack(anchor='w',padx=30,pady=8)
  self.drops_var=tk.BooleanVar(value=prefs.get('cs2_round_drops',any((Path(__file__).parent/'round-drops').glob('drop-*.wav'))))
  tk.Checkbutton(settings,text='CS2: гимны за победу в раунде и матче',variable=self.drops_var,command=self.save_drops_setting,bg='#121212',fg='#ddd',selectcolor='#333').pack(anchor='w',padx=30,pady=8)
  self.button(settings,'Проверить гимн',self.test_drop).pack(pady=4)
  self.button(settings,'Проверить связь CS2',self.check_cs2).pack(pady=4)
  self.button(settings,'Остановить музыку',lambda:__import__('round_drops').stop()).pack(pady=4)
  self.ace_var=tk.BooleanVar(value=prefs.get('cs2_ace',True))
  tk.Checkbutton(settings,text='CS2: фраза за эйс (в том числе в игровом режиме)',variable=self.ace_var,command=self.save_ace_setting,bg='#121212',fg='#ddd',selectcolor='#333').pack(anchor='w',padx=30,pady=8)
  self.commentator_var=tk.BooleanVar(value=prefs.get('cs2_commentator',True))
  tk.Checkbutton(settings,text='CS2: каждый килл + редкие комментарии раунда',variable=self.commentator_var,command=self.save_commentator_setting,bg='#121212',fg='#ddd',selectcolor='#333').pack(anchor='w',padx=30,pady=8)
  self.light_var=tk.BooleanVar(value=prefs.get('gaming_lightweight',True))
  tk.Checkbutton(settings,text='Экономить FPS: в игре только готовые фразы XTTS',variable=self.light_var,command=self.save_light_setting,bg='#121212',fg='#ddd',selectcolor='#333').pack(anchor='w',padx=30,pady=6)
  self.wt_var=tk.BooleanVar(value=prefs.get('wt_mode',True));self.dynamic_var=tk.BooleanVar(value=prefs.get('dynamic_voice',True));self.guard_var=tk.BooleanVar(value=prefs.get('performance_guard',True))
  for label,var in [('War Thunder: реакции на локальные HUD-события',self.wt_var),('Динамический голос и приглушение',self.dynamic_var),('Performance Guardian: контроль ресурсов',self.guard_var)]:
   tk.Checkbutton(settings,text=label,variable=var,command=self.save_gaming_settings,bg='#121212',fg='#ddd',selectcolor='#333').pack(anchor='w',padx=30,pady=6)
  self.wt_status=tk.StringVar(value='War Thunder: ожидаю запуск игры');tk.Label(settings,textvariable=self.wt_status,bg='#121212',fg='#aaa').pack(pady=5)
  self.metrics_text=tk.StringVar(value='Датчики: загрузка…');tk.Label(settings,textvariable=self.metrics_text,bg='#121212',fg='#aaa',wraplength=600,justify='left').pack(pady=8)
  self.button(settings,'Подключить FPS: CSV PresentMon',self.choose_fps_csv).pack(pady=4)
  self.hotkey_value='Ctrl+J'
  try:self.hotkey_value=json.loads(PREFS.read_text(encoding='utf-8')).get('hotkey','Ctrl+J')
  except (OSError,ValueError,AttributeError):pass
  tk.Label(settings,text='Открыть поверх окон — сочетание клавиш',bg='#121212',fg='#ddd').pack(pady=(15,5))
  self.hotkey_entry=tk.Entry(settings,bg='#252525',fg='white',insertbackground='white',font=('Segoe UI',12));self.hotkey_entry.insert(0,self.hotkey_value);self.hotkey_entry.pack(pady=5)
  self.button(settings,'Сохранить сочетание',self.save_hotkey).pack(pady=5)
  from activation import mode
  self.license_label=tk.Label(settings,text='Активирован' if mode()=='full' else 'Без ключа',bg='#121212',fg='#aaa');self.license_label.pack(pady=15)
  self.button(settings,'Ввести ключ',self.enter_key).pack(pady=5);self.button(settings,'Сбросить ключ',self.reset_key).pack(pady=5)
  self.button(settings,'Очистить историю чата',self.clear_chat).pack(pady=5)
  self.button(settings,'Забыть пользователя и переписку',self.forget_user).pack(pady=5);self.button(settings,'Выйти из приложения',self.quit).pack(pady=5)
  self.game_button=self.button(right,'',lambda:self.set_game_mode(not self.game_mode));self.game_button.pack(side='bottom',fill='x',padx=18,before=self.content);self.update_game_button()
  self.wake_button=self.button(right,'',self.toggle_wake);self.wake_button.pack(side='bottom',fill='x',padx=18,pady=3,before=self.content);self.update_wake_button()
  self.status=tk.StringVar(value='Запускаюсь…');tk.Label(right,textvariable=self.status,bg='#121212',fg='#8b9aa5',wraplength=650).pack(pady=8)
  row=tk.Frame(right,bg='#222',padx=14,pady=14);row.pack(side='bottom',fill='x',padx=18,pady=(0,18),before=self.content)
  self.entry=tk.Entry(row,bg='#222',fg='white',insertbackground='white',relief='flat',font=('Segoe UI',13));self.entry.pack(fill='x',ipady=10);self.entry.bind('<Return>',lambda e:self.submit())
  self.entry.insert(0,str(prefs.get('draft',''))[:8000]);self.entry.bind('<KeyRelease>',self.schedule_draft)
  tk.Label(row,text='Спроси что угодно · локально',bg='#222',fg='#888').pack(side='left')
  self.button(row,'Говорить',lambda:self.submit(True)).pack(side='right');self.button(row,'Отправить',self.submit).pack(side='right',padx=8);self.button(row,'Стоп',self.stop_speech).pack(side='right')
  self.page('Нейрочат');self.setup_tray();self.setup_hotkey();self.setup_run_hotkey();self.setup_overlay_hotkey();self.setup_cs2();self.setup_gaming_services();self.root.protocol('WM_DELETE_WINDOW',self.hide);self.root.bind('<Escape>',lambda e:self.hide())
  self.root.bind('<Control-f>',lambda e:self.open_search())
  self.root.bind('<Control-F>',lambda e:self.open_search())
  self.root.bind('<Control-l>',lambda e:self.focus_input())
  self.root.bind('<Control-L>',lambda e:self.focus_input())
  self.root.bind('<Map>',self.on_map)
  self.root.bind('<MouseWheel>',self.settings_wheel)
  self.root.after(100,self.apply_taskbar)
  threading.Thread(target=self.worker,daemon=True).start();self.tick();self.root.after(300,lambda:None if self.game_mode else product.whats_new(self.root));self.root.mainloop()
 def open_search(self):
  self.page('Нейрочат');self.chat_search.pack(fill='x',padx=10,pady=3,before=self.answer);self.search_entry.focus_set();self.find_chat();return 'break'
 def close_search(self):
  self.chat_search.pack_forget();self.answer.tag_remove('found','1.0','end');self.answer.tag_remove('current_match','1.0','end');self.entry.focus_set()
 def find_chat(self):
  query=self.search_entry.get();self.search_matches=[];self.search_index=-1
  self.answer.tag_remove('found','1.0','end');self.answer.tag_remove('current_match','1.0','end')
  if not query:self.search_count.set('');return
  index='1.0';count=tk.IntVar()
  while len(self.search_matches)<500:
   hit=self.answer.search(query,index,stopindex='end',nocase=True,count=count)
   if not hit or count.get()<=0:break
   end=self.answer.index(f'{hit}+{count.get()}c');self.search_matches.append((hit,end));self.answer.tag_add('found',hit,end);index=end
  self.search_count.set(str(len(self.search_matches))+('+' if len(self.search_matches)==500 else ''))
  if self.search_matches:self.next_match()
 def next_match(self):
  if not self.search_matches:return
  self.search_index=(self.search_index+1)%len(self.search_matches);start,end=self.search_matches[self.search_index]
  self.answer.tag_remove('current_match','1.0','end');self.answer.tag_add('current_match',start,end);self.answer.see(start);self.search_count.set(f'{self.search_index+1}/{len(self.search_matches)}')
 def select_chat(self,event=None):
  self.answer.tag_add('sel','1.0','end-1c');return 'break'
 def copy_selection(self,event=None):
  try:text=self.answer.get('sel.first','sel.last')
  except tk.TclError:return 'break'
  self.root.clipboard_clear();self.root.clipboard_append(text);self.status.set('Выделенный текст скопирован.');return 'break'
 def scrollable_settings(self):
  page=self.pages['Настройки']
  self.settings_canvas=tk.Canvas(page,bg='#121212',highlightthickness=0)
  scrollbar=tk.Scrollbar(page,orient='vertical',command=self.settings_canvas.yview)
  scrollbar.pack(side='right',fill='y');self.settings_canvas.pack(side='left',fill='both',expand=True)
  self.settings_canvas.configure(yscrollcommand=scrollbar.set)
  inside=tk.Frame(self.settings_canvas,bg='#121212')
  item=self.settings_canvas.create_window(0,0,window=inside,anchor='nw')
  inside.bind('<Configure>',lambda e:self.settings_canvas.configure(scrollregion=self.settings_canvas.bbox('all')))
  self.settings_canvas.bind('<Configure>',lambda e:self.settings_canvas.itemconfigure(item,width=e.width))
  return inside
 def settings_wheel(self,event):
  if self.current=='Настройки':self.settings_canvas.yview_scroll(-int(event.delta/120),'units');return 'break'
 def schedule_draft(self,event=None):
  if self.draft_timer:self.root.after_cancel(self.draft_timer)
  self.draft_timer=self.root.after(900,self.save_draft)
 def save_draft(self):
  self.draft_timer=None
  try:product.save(draft=self.entry.get()[:8000])
  except OSError as exc:self.status.set('Черновик не сохранён: '+str(exc))
 def export_chat(self):
  text=self.answer.get('1.0','end').strip()
  if not text:self.status.set('Переписка пока пуста.');return
  path=filedialog.asksaveasfilename(parent=self.root,title='Сохранить переписку',defaultextension='.txt',initialfile='JARVIS-chat.txt',filetypes=[('Текст','*.txt')])
  if not path:return
  try:Path(path).write_text(text+'\n',encoding='utf-8');self.status.set('Переписка сохранена.')
  except OSError as exc:messagebox.showerror('Экспорт',str(exc),parent=self.root)
 def filter_commands(self):
  all_commands=list(dict.fromkeys(ACTIONS+CATALOG+['я играю','я работаю','включи игровой режим','выключи игровой режим','обнови список приложений','очистить историю','помощь']))
  query=self.command_search.get().lower().strip();self.filtered_commands=[c for c in all_commands if query in c.lower()]
  self.command_list.delete(0,'end')
  for command in self.filtered_commands:self.command_list.insert('end',command)
 def choose_command(self):
  selection=self.command_list.curselection()
  if not selection:return
  text=self.filtered_commands[selection[0]];self.entry.delete(0,'end');self.entry.insert(0,text);self.entry.focus_set();self.status.set('Команда подставлена — нажми Enter для выполнения.')
 def update_game_button(self):
  self.game_button.configure(text='Игровой режим: ВКЛ' if self.game_mode else 'Игровой режим: ВЫКЛ')
 def set_game_mode(self,enabled):
  self.game_mode=bool(enabled);self.update_game_button()
  if enabled and self.assistant and self.assistant.speech:self.assistant.speech.interrupt();self.assistant.speech.stop_wake()
  try:product.save(game_mode=self.game_mode)
  except OSError as exc:self.status.set('Не удалось сохранить игровой режим: '+str(exc))
  if enabled:self.hide()
 def apply_taskbar(self):
  if self.closing:return
  try:windows_shell.taskbar(self.root)
  except Exception as exc:self.status.set('Панель задач: '+str(exc))
 def on_map(self,event):
  if event.widget==self.root and self.root.state()=='normal':
   self.hidden=False;self.root.overrideredirect(True);self.root.after(50,self.apply_taskbar)
 def minimize(self):
  self.root.attributes('-topmost',False);self.root.overrideredirect(False);self.root.iconify()
 def focus_input(self):
  self.page('Нейрочат');self.entry.focus_set();return 'break'
 def copy_answer(self):
  if not self.last_answer:self.status.set('Пока нет ответа для копирования.');return
  self.root.clipboard_clear();self.root.clipboard_append(self.last_answer);self.status.set('Ответ скопирован.')
 def stop_speech(self):
  if self.assistant and self.assistant.speech:self.assistant.speech.interrupt()
  self.status.set('Озвучка остановлена. Вычисление ответа, если идёт, продолжается.')
 def save_light_setting(self):
  try:product.save(gaming_lightweight=self.light_var.get())
  except OSError as exc:self.status.set(str(exc))
 def setup_gaming_services(self):
  from gaming_services import Services
  self.services=Services(self.events)
 def save_gaming_settings(self):
  try:product.save(wt_mode=self.wt_var.get(),dynamic_voice=self.dynamic_var.get(),performance_guard=self.guard_var.get())
  except OSError as exc:self.status.set(str(exc))
  if not self.guard_var.get():self.guard_paused=False
 def choose_fps_csv(self):
  path=filedialog.askopenfilename(parent=self.root,title='Текущий CSV захвата PresentMon',filetypes=[('CSV','*.csv')])
  if path:
   try:product.save(fps_csv=path);self.status.set('CSV FPS подключён. Данные должны обновляться внешним захватом.')
   except OSError as exc:self.status.set(str(exc))
 def cs2_state(self,data):
  self.events.put(('cs2_menu',__import__('menu_music').in_menu(data)))
  try:__import__('game_journal').session.update(data)
  except (OSError,ValueError,TypeError):pass
  player=data.get('player',{});provider=data.get('provider',{});state=player.get('state',{})
  health=state.get('health',100);flash=state.get('flashed',0)
  critical=(player.get('steamid')==provider.get('steamid') and data.get('round',{}).get('phase')=='live' and isinstance(health,(int,float)) and health>0 and
            (health<=30 or (isinstance(flash,(int,float)) and flash>0) or data.get('bomb',{}).get('state')=='planted'))
  self.events.put(('combat',bool(critical)))
 def save_personality(self, value):
  try:product.save(personality=value)
  except OSError as exc:messagebox.showerror('Характер',str(exc),parent=self.root)

 def save_voice(self):
  try:
   product.save(voice_engine=self.voice_engine.get(),speech_volume=float(self.speech_volume.get())/100,speech_speed=float(self.speech_speed.get()))
   self.status.set('Громкость и скорость голоса сохранены.');return True
  except OSError as exc:self.status.set('Не удалось сохранить голос: '+str(exc));return False
 def test_voice(self):
  if not self.save_voice():return
  if self.assistant and self.assistant.speech:self.assistant.speech.speak('Привет, Гоша. Проверка громкости и скорости голоса.')
  else:self.status.set('Голос ещё загружается. Попробуй через несколько секунд.')
 def setup_cs2(self):
  try:
   from cs2_ace import AceServer
   self.ace_server=AceServer(lambda text:self.events.put(('ace',text)),comment_callback=lambda text:self.events.put(('commentary',text)),state_callback=self.cs2_state,win_callback=lambda:self.events.put(('round_win','')),match_callback=lambda:self.events.put(('match_win','')),kill_callback=lambda:self.events.put(('kill_sound','')))
  except OSError as exc:self.status.set('CS2: приём событий недоступен: '+str(exc))
 def save_menu_music(self):
  try:product.save(cs2_menu_music=self.menu_music_var.get())
  except OSError as exc:self.status.set(str(exc))
  if not self.menu_music_var.get() and getattr(self,'menu_audio',None):self.menu_audio.update(False)

 def test_drop(self):
  try:
   clip=__import__('round_drops').play()
   self.status.set('Проверка гимна: '+clip)
  except (OSError,RuntimeError) as exc:messagebox.showerror('Музыка CS2',str(exc),parent=self.root)
 def check_cs2(self):
  server=self.ace_server
  if not server:message='Приёмник CS2 не запущен. Возможно, открыта ещё одна копия JARVIS.'
  elif not server.last_received:message='Данные CS2 ещё не приходили. Перезапусти CS2 после запуска JARVIS и зайди в матч.'
  else:
   age=int(time.monotonic()-server.last_received)
   message='Последний пакет: '+str(age)+' сек. назад. '+str(server.last_summary)
  messagebox.showinfo('Связь CS2',message,parent=self.root)

 def save_drops_setting(self):
  try:
   product.save(cs2_round_drops=self.drops_var.get())
   if not self.drops_var.get():__import__('round_drops').stop()
  except OSError as exc:messagebox.showerror('CS2',str(exc),parent=self.root)

 def save_commentator_setting(self):
  try:product.save(cs2_commentator=self.commentator_var.get())
  except OSError as exc:self.status.set('Не удалось сохранить комментатора: '+str(exc))
 def save_ace_setting(self):
  try:product.save(cs2_ace=self.ace_var.get())
  except OSError as exc:self.status.set('Не удалось сохранить настройку CS2: '+str(exc))
 def setup_overlay_hotkey(self):
  try:
   from hotkey import Hotkey
   self.overlay_hotkey=Hotkey(lambda:self.events.put(('overlay','')))
   self.overlay_hotkey.set('Ctrl+Shift+O')
  except Exception as exc:self.status.set('Оверлей доступен из трея: '+str(exc))
 def toggle_overlay(self):
  if self.overlay is None:
   from mini_overlay import MiniOverlay
   self.overlay=MiniOverlay(self)
  else:self.overlay.toggle()
 def setup_run_hotkey(self):
  try:
   from hotkey import Hotkey
   self.run_hotkey=Hotkey(lambda:self.events.put(('run_palette','')))
   self.run_hotkey.set('Ctrl+Shift+R')
  except Exception as exc:messagebox.showwarning('Окно Выполнить',str(exc),parent=self.root)
 def open_palette(self):
  if self.palette is not None and not self.palette.closed:self.palette.show();return
  from run_palette import RunPalette
  self.palette=RunPalette(self)
 def setup_hotkey(self):
  try:
   from hotkey import Hotkey
   self.hotkey=Hotkey(lambda:self.events.put(('hotkey','')))
   self.hotkey.set(self.hotkey_value)
  except Exception as exc:messagebox.showwarning('Горячая клавиша',str(exc),parent=self.root)
 def save_hotkey(self):
  value=self.hotkey_entry.get().strip()
  previous=self.hotkey_value
  try:
   if self.hotkey is None:raise RuntimeError('Перезапусти приложение, чтобы включить горячие клавиши.')
   self.hotkey.set(value)
   try:
    product.save(hotkey=value)
   except OSError:
    self.hotkey.set(previous);raise
   self.hotkey_value=value;self.status.set('Сочетание сохранено: '+value)
  except Exception as exc:messagebox.showerror('Горячая клавиша',str(exc),parent=self.root)
 def show_overlay(self):
  self.show();self.root.attributes('-topmost',True);self.root.lift()
  try:
   import ctypes
   from ctypes import wintypes
   user32=ctypes.windll.user32
   user32.GetParent.argtypes=[wintypes.HWND];user32.GetParent.restype=wintypes.HWND
   user32.SetForegroundWindow.argtypes=[wintypes.HWND]
   handle=user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
   user32.SetForegroundWindow(handle)
  except Exception:pass
  self.entry.focus_force()
 def button(self,parent,text,command):
  return tk.Button(parent,text=text,command=command,bg='#242424',fg='#ddd',activebackground='#353535',activeforeground='white',relief='flat',bd=0,font=('Segoe UI',11),padx=12,pady=5)
 def heading(self,parent,title,sub):
  tk.Label(parent,text=title,font=('Segoe UI',24,'bold'),bg='#121212',fg='#ddd').pack(pady=(25,6))
  tk.Label(parent,text=sub,bg='#121212',fg='#929292',wraplength=630).pack(pady=5)
 def update_license_status(self):
  from activation import mode
  full=mode()=='full'
  self.commands_license.set('Продукт активирован — все команды доступны.' if full else 'Без ключа: доступны YouTube и вопросы.')
  if hasattr(self,'license_label'):self.license_label.configure(text='Активирован' if full else 'Без ключа')
 def page(self,name):
  self.current=name
  if hasattr(self,"commands_license"):self.update_license_status()
  for n,p in self.pages.items():
   p.pack_forget();self.nav[n].configure(bg='#292929' if n==name else '#151515')
  self.pages[name].pack(fill='both',expand=True)
  if name=='Орб' and hasattr(self,'orb'):self.root.after_idle(self.orb.draw)
  if hasattr(self,'entry'):self.entry.focus_set()
 def prompt(self,text):self.entry.delete(0,'end');self.entry.insert(0,text+': ');self.entry.focus_set()
 def run_action(self,text):self.entry.delete(0,'end');self.entry.insert(0,text);self.submit()
 def transcript(self,text):
  self.answer.configure(state='normal');__import__('chat_format').insert(self.answer,text+'\n\n');self.answer.see('end');self.answer.configure(state='disabled')
  if self.search_entry.get():self.find_chat()
 def update_wake_button(self):
  self.wake_button.configure(text='Фоновый микрофон: ВКЛ — выключить' if self.wake_enabled else 'Фоновый микрофон: ВЫКЛ — включить',fg='#9acba3' if self.wake_enabled else '#bbb')
 def sync_settings(self):
  self.wake_enabled=self.wake_var.get();self.voice_output=self.sound_var.get()
  if hasattr(self,"wake_button"):self.update_wake_button()
  if self.assistant and self.assistant.speech:
   self.assistant.speech.set_wake(self.wake_enabled)
   if not self.wake_enabled and self.background_recording:self.assistant.speech.interrupt()
  try:product.save(wake_enabled=self.wake_enabled,voice_output=self.voice_output)
  except OSError as exc:messagebox.showerror('Настройки',str(exc),parent=self.root)
  if not self.voice_output and self.assistant and self.assistant.speech:self.assistant.speech.interrupt()
 def clear_chat(self):
  self.answer.configure(state='normal');self.answer.delete('1.0','end');self.answer.configure(state='disabled');self.jobs.put((False,'__clear_history__'));self.find_chat()
 def forget_user(self):
  if messagebox.askyesno('Очистка памяти','Удалить имя, сохранённые сведения и переписку?',parent=self.root):
   self.jobs.put((False,'__forget_user__'))
   self.answer.configure(state='normal');self.answer.delete('1.0','end');self.answer.configure(state='disabled')
 def enter_key(self):
  import subprocess
  subprocess.Popen([sys.executable,__file__,'--activate']);self.quit()
 def reset_key(self):
  from activation import reset
  try:reset();self.update_license_status()
  except OSError as e:messagebox.showerror('Ошибка',str(e),parent=self.root)
 def persist_phrases(self):
  try:
   DATA.parent.mkdir(parents=True,exist_ok=True);tmp=DATA.with_suffix('.tmp');tmp.write_text(json.dumps(self.phrases,ensure_ascii=False),encoding='utf-8');tmp.replace(DATA);self.refresh_phrases()
  except OSError as e:messagebox.showerror('Ошибка',str(e),parent=self.root)
 def save_phrase(self):
  phrase=self.phrase.get().strip().lower()
  if phrase:self.phrases[phrase]=self.action.get();self.persist_phrases()
 def delete_phrase(self):
  selection=self.phrase_list.curselection()
  if selection:self.phrases.pop(list(self.phrases)[selection[0]],None);self.persist_phrases()
 def refresh_phrases(self):
  self.phrase_list.delete(0,'end')
  for key,value in self.phrases.items():self.phrase_list.insert('end',key+' → '+str(value))
 def setup_tray(self):
  try:
   import pystray
   from PIL import Image,ImageDraw
   image=Image.new('RGB',(64,64),'#0b141c');draw=ImageDraw.Draw(image)
   draw.ellipse((10,10,54,54),outline='#80b5d3',width=3)
   draw.text((26,23),'J',fill='white')
   self.tray=pystray.Icon('JARVIS',image,'JARVIS',pystray.Menu(
    pystray.MenuItem('Открыть',lambda icon,item:self.events.put(('show','')),default=True),
    pystray.MenuItem('Мини-оверлей · Ctrl+Shift+O',lambda icon,item:self.events.put(('overlay',''))),
    pystray.MenuItem('Игровой режим: вкл/выкл',lambda icon,item:self.events.put(('game',not self.game_mode))),
    pystray.MenuItem('Выполнить · Ctrl+Shift+R',lambda icon,item:self.events.put(('run_palette',''))),
    pystray.MenuItem('Микрофон',lambda icon,item:self.events.put(('mic',''))),
    pystray.MenuItem('Слово Джарвис: вкл/выкл',lambda icon,item:self.events.put(('wake',''))),
    pystray.MenuItem('Выйти',lambda icon,item:self.events.put(('close','')))))
   threading.Thread(target=self.tray.run,daemon=True).start()
  except Exception as exc:
   self.tray=None
   self.status.set('Трей недоступен: '+str(exc))
 def hide(self):
  self.root.attributes('-topmost',False)
  if self.tray is not None and self.tray.visible:
   self.hidden=True;self.root.withdraw()
  else:self.root.overrideredirect(False);self.root.iconify()
 def show(self):
  self.hidden=False;self.root.deiconify();self.root.overrideredirect(True);self.root.lift();self.entry.focus_set()
 def toggle_wake(self):
  self.wake_enabled=not self.wake_enabled
  self.wake_var.set(self.wake_enabled)
  self.sync_settings()
  self.status.set('Жду слово Джарвис' if self.wake_enabled else 'Ожидание слова отключено')
 def quit(self):
  if self.draft_timer:self.root.after_cancel(self.draft_timer)
  self.save_draft()
  self.closing=True
  if self.services:self.services.close()
  if getattr(self,'menu_audio',None):self.menu_audio.close()
  if getattr(self,'kill_audio',None):self.kill_audio.close()
  __import__('round_drops').stop()
  if self.ace_server:self.ace_server.close()
  try:__import__('game_journal').session.save()
  except OSError:pass
  if self.hotkey:self.hotkey.close()
  if self.run_hotkey:self.run_hotkey.close()
  if self.overlay_hotkey:self.overlay_hotkey.close()
  if self.palette:self.palette.close()
  if self.assistant and hasattr(self.assistant,"extras"):self.assistant.extras.close()
  if self.assistant and self.assistant.speech:self.assistant.speech.close()
  if self.tray:self.tray.stop()
  self.root.destroy()
 def submit(self,mic=False):
  if self.busy:return
  text=self.entry.get().strip()
  if not mic and not text:return
  self.entry.delete(0,'end');self.save_draft();self.busy=True;self.status.set('Слушаю…' if mic else 'Выполняю…');self.jobs.put((mic,text))
 def worker(self):
  import pythoncom
  pythoncom.CoInitialize()
  j=Jarvis();self.assistant=j;original=j.say
  if self.closing:
   if j.speech:j.speech.close()
   return
  if j.speech:j.speech.on_error=lambda message:self.events.put(('voice_error',message))
  j.notify=lambda text:self.events.put(('reminder',text))
  if j.speech:j.speech.set_wake(self.wake_enabled)
  def say(text):
   self.events.put(('answer',text))
   if self.voice_output and not self.game_mode:original(text)
  j.say=say
  for item in j.history:self.events.put(('restore',('Ты: ' if item['role']=='user' else 'Джарвис: ')+item['content']))
  self.events.put(('ready','Готов. Скажи Джарвис или введи команду.'))
  while not self.closing:
   try:
    mic,text=self.jobs.get(timeout=.2)
   except queue.Empty:
    if self.closing:return
    if self.guard_paused or self.game_mode or not self.wake_enabled or not j.speech or j.speech.speaking.is_set():
     if j.speech:j.speech.stop_wake()
     continue
    try:
     text=j.speech.wake_phrase()
     if text is None:continue
     self.events.put(('listening','Слушаю команду…'))
     if not text:
      import winsound
      winsound.Beep(800,100)
      self.background_recording=True
      try:text=j.listen()
      finally:self.background_recording=False
     if not self.wake_enabled:
      self.events.put(('ready','Фоновый микрофон выключен'));continue
     if not text:
      self.events.put(('ready','Не расслышал. Скажи Джарвис ещё раз.'));continue
     mic=False
    except Exception as exc:
     if j.speech:j.speech.stop_wake()
     self.events.put(('ready','Ошибка микрофона, повтор через 2 секунды: '+str(exc)))
     time.sleep(2)
     continue
   try:
    if j.speech:j.speech.stop_wake()
    if text=='__forget_user__':j.forget_user();continue
    if text=='__clear_history__':j.clear_history();continue
    if mic:
     j.enable_microphone()
     if not j.voice:raise RuntimeError('Микрофон недоступен')
     text=j.listen()
     if not text:raise RuntimeError('Не расслышал. Попробуй ещё раз.')
    self.events.put(('status','Выполняю: '+text))
    self.events.put(('heard',text))
    # Сервер запускается только при необходимости; команды работают без модели.
    # Локальные действия не запускают языковую модель.
    phrase=text.strip().lower().strip(' .!?')
    if phrase.startswith('джарвис'):phrase=phrase[len('джарвис'):].strip(' ,')
    if phrase in ('игровой режим вкл','игровой режим выкл','включи игровой режим','выключи игровой режим'):
     self.game_mode=phrase in ('игровой режим вкл','включи игровой режим');self.events.put(('game',self.game_mode));continue
    scenario=workflows.scenarios().get(phrase)
    if scenario is not None:
     from activation import mode
     if mode()!='full':j.say('Для сценариев нужен ключ.');continue
     scenario=workflows.validate('\n'.join(scenario))
     for action in scenario:
      if action.startswith('игровой режим '):
       self.game_mode=action.endswith('вкл');self.events.put(('game',self.game_mode))
      else:
       result=j.desktop_action(action)
       j.say(result or 'Не удалось выполнить: '+action)
     continue
    custom=self.phrases.get(text.strip().lower())
    if custom in ACTIONS:text=custom
    j.eco_mode=self.guard_paused
    if j.command(text) is False:self.events.put(('close',''))
   except Exception as e:self.events.put(('answer','Ошибка: '+str(e)))
   finally:self.events.put(('ready','Готов'))
 def tick(self):
  try:
   while True:
    kind,text=self.events.get_nowait()
    if kind=='voice_error':self.status.set(text);self.transcript(text);continue
    if kind=='combat':
     was_critical=time.monotonic()<self.combat_until
     self.combat_until=time.monotonic()+5 if text else 0
     if self.assistant and self.assistant.speech:
      self.assistant.speech.duck_until=self.combat_until
      if text and not was_critical and self.dynamic_var.get():self.assistant.speech.interrupt()
     continue
    if kind=='wt_status':self.wt_status.set(text);continue
    if kind=='guard_off':self.guard_paused=False;self.metrics_text.set('Контроль ресурсов выключен.');continue
    if kind=='metrics_error':self.metrics_text.set(text);continue
    if kind=='metrics':
     metrics,paused=text;changed=paused!=self.guard_paused;self.guard_paused=paused
     fmt=lambda value,suffix:('—' if value is None else str(round(value))+suffix)
     self.metrics_text.set('CPU '+fmt(metrics.get('cpu'),'%')+' · RAM '+fmt(metrics.get('ram'),'%')+' · GPU '+fmt(metrics.get('gpu'),'%')+'\nGPU '+fmt(metrics.get('gpu_temp'),'°C')+' · CPU '+fmt(metrics.get('cpu_temp'),'°C')+' · FPS '+fmt(metrics.get('fps'),'')+('\nЩадящий режим: фон на паузе, чат доступен с короткими ответами.' if paused else ''))
     if changed and paused:
      if self.assistant and self.assistant.speech:self.assistant.speech.interrupt();self.assistant.speech.stop_wake()
      self.transcript('Guardian: высокая нагрузка/температура. Фоновые распознавание и анимация на паузе. Чат работает в экономном режиме. Уменьши графику или ограничь FPS.')
     continue
    if kind=='wt_comment':
     phrase,style=text
     if self.wt_var.get():
      self.transcript('War Thunder: '+phrase)
      if style in ('crash','destroyed'):
       from game_toast import GameToast
       GameToast(self.root,phrase)
       if style=='crash':
        try:__import__('round_drops').play()
        except (OSError,RuntimeError) as exc:self.transcript('Гимн аварии: '+str(exc))
       continue

      if self.voice_output and not self.busy and not self.guard_paused and self.assistant and self.assistant.speech and not self.assistant.speech.speaking.is_set():self.assistant.speech.speak(phrase,style=style)
     continue
    if kind=='cs2_menu':
     if not getattr(self,'menu_audio',None):
      from menu_music import MenuMusic
      self.menu_audio=MenuMusic(lambda error:self.events.put(('voice_error',error)))
     self.menu_audio.update(bool(text) and self.menu_music_var.get())
     continue
    if kind=='kill_sound':
     if self.kill_sound_var.get():
      if not getattr(self,'kill_audio',None):
       from kill_sound import KillSound
       self.kill_audio=KillSound(lambda error:self.events.put(('voice_error',error)))
      self.kill_audio.play()
     continue
    if kind=='match_win':
     if self.drops_var.get():
      try:
       __import__('round_drops').play_match()
       self.transcript('CS2 · Победа в матче!')
      except (OSError,RuntimeError) as exc:self.transcript('Гимн матча: '+str(exc))
     continue
    if kind=='round_win':
     if self.drops_var.get():
      try:
       from round_drops import play
       clip=play()
       if clip:self.transcript('CS2 · Победа! '+clip)
      except (OSError,RuntimeError) as exc:self.transcript('Не удалось включить дроп: '+str(exc))
     continue
    if kind=='commentary':
     if isinstance(text,dict) and text.get('type')=='kill':
      if self.commentator_var.get():
       self.transcript('CS2: '+text['text'])
       if self.voice_output:self.kill_comments.append(text['text'])
      continue
     if self.commentator_var.get():
      self.transcript('CS2: '+text)
      if self.voice_output and not self.busy and not self.guard_paused and time.monotonic()>self.combat_until and self.assistant and self.assistant.speech and not self.assistant.speech.speaking.is_set():self.assistant.speech.speak(text,style='warning' if 'попытка' in text or 'отдали' in text else 'victory')
     continue
    if kind=='ace':
     if self.ace_var.get():
      self.kill_comments.clear()
      self.transcript('CS2 · Эйс! '+text)
      if self.voice_output:__import__('round_drops').after_ace(lambda error:self.events.put(('voice_error',error)))
     continue
    if kind=='overlay':self.toggle_overlay();continue
    if kind in ('answer','reminder') and self.overlay is not None:self.overlay.set_answer(text)
    if kind=='reminder':
     self.last_answer=text;self.transcript('Напоминание: '+text);self.status.set(text)
     if not self.game_mode and self.voice_output and self.assistant and self.assistant.speech:self.assistant.speech.speak(text)
     continue
    if kind=='game':self.set_game_mode(text);continue
    if kind=='close':self.quit();return
    if kind=='wake':self.toggle_wake();continue
    if kind=='listening':
     if self.wake_enabled and not self.game_mode:self.show_overlay();self.busy=True;self.status.set(text)
     continue
    if kind=='run_palette':self.open_palette();continue
    if kind=='hotkey':self.show_overlay();continue
    if kind=='show':self.show();continue
    if kind=='mic':self.show();self.submit(True);continue
    if kind=='restore':
     self.transcript(text)
     if text.startswith('Джарвис: '):self.last_answer=text[len('Джарвис: '):]
     continue
    if kind=='heard':self.transcript('Ты: '+text);continue
    if kind=='answer':self.last_answer=text;self.transcript('Джарвис: '+text);self.status.set(text[:100])
    else:self.status.set(text)
    if kind=='ready':self.busy=False
  except queue.Empty:pass
  if self.kill_comments and self.assistant and self.assistant.speech:
   if not self.voice_output or not self.commentator_var.get():self.kill_comments.clear()
   elif not self.assistant.speech.speaking.is_set():
    self.assistant.speech.speak(self.kill_comments.popleft(),style='victory')
  if not self.guard_paused and not self.hidden and not self.game_mode and self.current=='Орб' and self.root.state()!='iconic':
   speech=self.assistant.speech if self.assistant else None
   state='speaking' if speech and speech.speaking.is_set() else 'listening' if self.background_recording or (self.busy and 'Слуш' in self.status.get()) else 'thinking' if self.busy else 'idle'
   self.orb.draw(state)
  self.root.after(500 if self.hidden else 80,self.tick)
if __name__=='__main__':
 from activation import activate
 import sys
 if activate(force='--activate' in sys.argv) and product.welcome():App()
