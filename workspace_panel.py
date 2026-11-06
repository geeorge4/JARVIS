"""Desktop workspace for pinned commands, shared notes and active timers."""
import tkinter as tk
from tkinter import messagebox, simpledialog

from activation import mode
from desktop_notes import Notes
from extra_commands import norm
import product

BG = '#121212'
PANEL = '#202020'
TEXT = '#eeeeee'
DEFAULT_PINS = [
    ('YouTube', 'открой ютуб'),
    ('Steam', 'открой Steam'),
    ('Калькулятор', 'открой калькулятор'),
    ('Блокнот', 'открой блокнот'),
    ('Загрузки', 'открой загрузки'),
    ('Проверка ПК', 'проверь сбои Windows'),
]


class Workspace:
    def __init__(self, app, parent, notes_path):
        self.app = app
        self.notes = Notes(notes_path)
        self.panes = {}
        self.tabs = {}
        self.current = ''
        self.timer_rows = []
        self.note_rows = []
        self.pins = self.load_pins()
        app.heading(parent, 'Рабочий стол', 'Команды, заметки и таймеры')
        tabs = tk.Frame(parent, bg=BG)
        tabs.pack(fill='x', padx=16, pady=(0, 8))
        for name in ('Быстрые команды', 'Заметки', 'Таймеры'):
            button = app.button(tabs, name, lambda selected=name: self.show(selected))
            button.pack(side='left', fill='x', expand=True, padx=2)
            self.tabs[name] = button
            self.panes[name] = tk.Frame(parent, bg=BG)
        self.build_pins()
        self.build_notes()
        self.build_timers()
        self.show('Быстрые команды')

    @staticmethod
    def load_pins():
        entries = product.load().get('workspace_pins')
        if not isinstance(entries, list):
            return DEFAULT_PINS.copy()
        return [(pair[0], pair[1]) for pair in entries[:12] if isinstance(pair, list)
                and len(pair) == 2 and all(isinstance(value, str) for value in pair)]

    def show(self, name):
        for label, pane in self.panes.items():
            pane.pack_forget()
            self.tabs[label].configure(bg='#344652' if label == name else '#242424')
        self.current = name
        self.panes[name].pack(fill='both', expand=True, padx=16, pady=(0, 8))
        self.refresh()

    def build_pins(self):
        pane = self.panes['Быстрые команды']
        row = tk.Frame(pane, bg=BG)
        row.pack(fill='x', pady=(0, 6))
        self.app.button(row, '+ Закрепить команду', self.add_pin).pack(side='left')
        self.pin_grid = tk.Frame(pane, bg=BG)
        self.pin_grid.pack(fill='x')
        for column in range(3):
            self.pin_grid.columnconfigure(column, weight=1, uniform='pin')
        self.render_pins()

    def render_pins(self):
        for widget in self.pin_grid.winfo_children():
            widget.destroy()
        for index, (label, command) in enumerate(self.pins):
            tile = tk.Frame(self.pin_grid, bg=PANEL)
            tile.grid(row=index // 3, column=index % 3, sticky='nsew', padx=3, pady=3)
            self.app.button(tile, label, lambda value=command: self.app.dispatch(value)).pack(side='left', fill='both', expand=True)
            self.app.button(tile, '×', lambda i=index: self.remove_pin(i)).pack(side='right')

    def save_pins(self, pins):
        try:
            product.save(workspace_pins=pins)
        except OSError as error:
            messagebox.showerror('Быстрые команды', str(error), parent=self.app.root)
            return
        self.pins = pins
        self.render_pins()

    def add_pin(self):
        if len(self.pins) >= 12:
            messagebox.showinfo('Быстрые команды', 'Можно закрепить до 12 команд.', parent=self.app.root)
            return
        label = simpledialog.askstring('Новая кнопка', 'Название кнопки', parent=self.app.root)
        if not label or not label.strip():
            return
        command = simpledialog.askstring('Новая кнопка', 'Что сказать Джарвису при нажатии?', parent=self.app.root)
        if command and command.strip():
            self.save_pins(self.pins + [(label.strip()[:24], command.strip()[:1000])])

    def remove_pin(self, index):
        self.save_pins(self.pins[:index] + self.pins[index + 1:])

    def build_notes(self):
        pane = self.panes['Заметки']
        row = tk.Frame(pane, bg=BG)
        row.pack(fill='x')
        tk.Label(row, text='Поиск', bg=BG, fg=TEXT).pack(side='left', padx=(0, 8))
        self.search = tk.StringVar()
        tk.Entry(row, textvariable=self.search, bg=PANEL, fg=TEXT, insertbackground=TEXT).pack(side='left', fill='x', expand=True)
        self.app.button(row, '+ Новая', lambda: self.edit_note(None)).pack(side='left', padx=4)
        self.note_list = self.listbox(pane)
        self.note_list.bind('<Double-Button-1>', lambda _: self.edit_selected())
        self.note_list.bind('<Return>', lambda _: self.edit_selected())
        actions = tk.Frame(pane, bg=BG)
        actions.pack(fill='x')
        self.app.button(actions, 'Редактировать', self.edit_selected).pack(side='left')
        self.app.button(actions, 'Удалить', self.delete_note).pack(side='left')
        self.note_info = tk.Label(actions, bg=BG, fg='#9ab0be')
        self.note_info.pack(side='right')
        self.search.trace_add('write', lambda *_: self.refresh_notes())

    def listbox(self, pane):
        row = tk.Frame(pane, bg=BG)
        row.pack(fill='both', expand=True, pady=6)
        bar = tk.Scrollbar(row)
        bar.pack(side='right', fill='y')
        result = tk.Listbox(row, bg=PANEL, fg=TEXT, selectbackground='#40586a', exportselection=False,
                            highlightthickness=0, yscrollcommand=bar.set, font=('Segoe UI', 11))
        result.pack(side='left', fill='both', expand=True)
        bar.configure(command=result.yview)
        return result

    def refresh_notes(self):
        selected = self.selected_note()
        try:
            notes = self.notes.list()
            query = norm(self.search.get())
            rows = [(index, note) for index, note in reversed(list(enumerate(notes))) if query in norm(note['text'])]
            self.note_info.configure(text=f'{len(rows)} из {len(notes)}')
        except (OSError, ValueError) as error:
            rows = []
            self.note_info.configure(text=str(error))
        if rows == self.note_rows:
            return
        self.note_rows = rows
        self.note_list.delete(0, 'end')
        for row, item in enumerate(rows):
            _, note = item
            preview = ' '.join(note['text'].split())
            self.note_list.insert('end', preview[:100] + ('…' if len(preview) > 100 else ''))
            if item == selected:
                self.note_list.selection_set(row)

    def selected_note(self):
        selection = self.note_list.curselection()
        return self.note_rows[selection[0]] if selection else None

    def full_mode(self):
        if mode() == 'full':
            return True
        messagebox.showinfo('Рабочий стол', 'Для заметок и таймеров нужен полный режим JARVIS.', parent=self.app.root)
        return False

    def edit_selected(self):
        item = self.selected_note()
        if item is not None:
            self.edit_note(item)

    def edit_note(self, item):
        if not self.full_mode():
            return
        window = tk.Toplevel(self.app.root)
        window.title('Новая заметка' if item is None else 'Редактировать заметку')
        window.transient(self.app.root)
        window.configure(bg=BG)
        editor = tk.Text(window, width=55, height=10, wrap='word', bg=PANEL, fg=TEXT, insertbackground=TEXT)
        editor.pack(fill='both', expand=True, padx=12, pady=12)
        if item is not None:
            editor.insert('1.0', item[1]['text'])
        def save():
            value = editor.get('1.0', 'end-1c').strip()
            if not 1 <= len(value) <= 4000:
                messagebox.showinfo('Заметка', 'Введите от 1 до 4000 символов.', parent=window)
                return
            try:
                if item is None:
                    self.notes.add(value)
                else:
                    self.notes.change(*item, text=value)
            except (OSError, ValueError) as error:
                messagebox.showerror('Заметка', str(error), parent=window)
                return
            window.destroy()
            self.refresh_notes()
        self.app.button(window, 'Сохранить', save).pack(pady=(0, 10))
        window.bind('<Control-Return>', lambda _: save())
        window.bind('<Escape>', lambda _: window.destroy())
        window.grab_set()
        editor.focus_set()

    def delete_note(self):
        item = self.selected_note()
        if item is None or not self.full_mode():
            return
        if not messagebox.askyesno('Заметка', 'Удалить выбранную заметку?', parent=self.app.root):
            return
        try:
            self.notes.change(*item)
        except (OSError, ValueError) as error:
            messagebox.showerror('Заметка', str(error), parent=self.app.root)
        self.refresh_notes()

    def build_timers(self):
        pane = self.panes['Таймеры']
        row = tk.Frame(pane, bg=BG)
        row.pack(fill='x')
        for seconds, label in ((60, '1 мин'), (300, '5 мин'), (900, '15 мин'), (1500, '25 мин')):
            self.app.button(row, label, lambda value=seconds: self.start_timer(value)).pack(side='left', padx=2)
        self.app.button(row, '+ Свой', self.custom_timer).pack(side='left', padx=2)
        self.timer_list = self.listbox(pane)
        controls = tk.Frame(pane, bg=BG)
        controls.pack(fill='x')
        self.app.button(controls, 'Отменить выбранный', self.cancel_timer).pack(side='left')
        self.timer_info = tk.Label(controls, bg=BG, fg='#9ab0be')
        self.timer_info.pack(side='right')

    def extras(self):
        return getattr(self.app.assistant, 'extras', None)

    def custom_timer(self):
        seconds = simpledialog.askinteger('Таймер', 'Длительность в секундах', minvalue=1, maxvalue=86400, parent=self.app.root)
        if seconds is not None:
            self.start_timer(seconds)

    def start_timer(self, seconds):
        if not self.full_mode():
            return
        extras = self.extras()
        if extras is None:
            self.timer_info.configure(text='Джарвис ещё запускается')
            return
        self.app.status.set(extras.handle(f'таймер {seconds} сек'))
        self.refresh_timers()

    def cancel_timer(self):
        selection = self.timer_list.curselection()
        extras = self.extras()
        if selection and extras is not None:
            extras.cancel_timer(self.timer_rows[selection[0]][0])
            self.refresh_timers()

    def refresh_timers(self):
        extras = self.extras()
        rows = extras.timer_snapshot() if extras is not None else []
        self.timer_info.configure(text='Активных таймеров: ' + str(len(rows)))
        if rows == self.timer_rows:
            return
        selection = self.timer_list.curselection()
        selected = self.timer_rows[selection[0]][0] if selection else None
        self.timer_rows = rows
        self.timer_list.delete(0, 'end')
        for row, (identifier, seconds) in enumerate(rows):
            hours, rest = divmod(seconds, 3600)
            minutes, seconds = divmod(rest, 60)
            self.timer_list.insert('end', f'Таймер {identifier}     {hours:02d}:{minutes:02d}:{seconds:02d}')
            if identifier == selected:
                self.timer_list.selection_set(row)

    def refresh(self):
        if self.current == 'Заметки':
            self.refresh_notes()
        elif self.current == 'Таймеры':
            self.refresh_timers()

