"""Local Dust2 lineups and recall practice."""
import json
from pathlib import Path
import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from uuid import uuid4


class Lineups:
    def __init__(self, app, parent, folder, query=''):
        from PIL import Image, ImageTk

        self.Image, self.ImageTk = Image, ImageTk
        self.folder = folder
        self.index = folder / 'lineups.json'
        self.cards = json.loads(self.index.read_text(encoding='utf-8')) if self.index.exists() else []
        self.window = tk.Toplevel(parent)
        self.window.title('Тренер Dust2')
        self.window.geometry('850x590')
        if parent is not app.root:
            self.window.attributes('-topmost', True)
        self.query = tk.StringVar(self.window, value=query)
        bar = ttk.Frame(self.window, padding=10)
        bar.pack(fill='x')
        search = ttk.Entry(bar, textvariable=self.query)
        search.pack(side='left', fill='x', expand=True)
        for label, action in [('Добавить', self.add), ('Тренировка', self.practice), ('Показать', self.reveal)]:
            ttk.Button(bar, text=label, command=action).pack(side='left', padx=3)
        self.listbox = tk.Listbox(self.window, height=6, exportselection=False)
        self.listbox.pack(fill='x', padx=10)
        self.listbox.bind('<<ListboxSelect>>', self.select)
        self.details = ttk.Label(self.window, wraplength=800, justify='left')
        self.details.pack(fill='x', padx=10, pady=10)
        self.pictures = ttk.Frame(self.window)
        self.pictures.pack(fill='both', expand=True, padx=10)
        self.photos = []
        self.current = None
        self.query.trace_add('write', lambda *_: self.refresh())
        self.refresh()
        search.focus_set()

    def refresh(self):
        terms = self.query.get().casefold().split()
        self.filtered = [card for card in self.cards if all(
            term in ' '.join(card[k] for k in ('title', 'method')).casefold() for term in terms)]
        self.listbox.delete(0, 'end')
        for card in self.filtered:
            self.listbox.insert('end', card['title'])
        self.current = None
        if self.filtered:
            self.listbox.selection_set(0)
            self.select()
        else:
            self.display('Добавь первую раскидку.' if not self.cards else 'Совпадений нет.')

    def select(self, event=None):
        selection = self.listbox.curselection()
        if selection:
            self.current = self.filtered[selection[0]]
            self.reveal()

    def display(self, text):
        self.details.configure(text=text)
        for widget in self.pictures.winfo_children():
            widget.destroy()
        self.photos.clear()

    def reveal(self):
        if self.current is None:
            return
        self.display(self.current['title'] + '\n' + self.current['method'])
        for key, caption in [('aim', 'Прицел'), ('landing', 'Приземление')]:
            path = self.folder / self.current[key]
            panel = ttk.Frame(self.pictures)
            panel.pack(side='left', anchor='n', padx=5)
            ttk.Label(panel, text=caption).pack()
            try:
                with self.Image.open(path) as image:
                    image.thumbnail((390, 290))
                    photo = self.ImageTk.PhotoImage(image, master=self.window)
                self.photos.append(photo)
                ttk.Button(panel, image=photo, command=lambda p=path: self.zoom(p)).pack()
            except OSError:
                ttk.Label(panel, text='Скриншот недоступен').pack()

    def zoom(self, path):
        window = tk.Toplevel(self.window)
        window.title('Скриншот раскидки')
        window.attributes('-topmost', bool(self.window.attributes('-topmost')))
        with self.Image.open(path) as image:
            image.thumbnail((window.winfo_screenwidth()-80, window.winfo_screenheight()-120))
            window.photo = self.ImageTk.PhotoImage(image, master=window)
        ttk.Label(window, image=window.photo).pack()

    def practice(self):
        if self.filtered:
            choices = [card for card in self.filtered if card is not self.current] or self.filtered
            self.current = random.choice(choices)
            self.listbox.selection_clear(0, 'end')
            self.display(self.current['title'] + '\nВспомни прицел и бросок, затем нажми «Показать».')

    def add(self):
        form = tk.Toplevel(self.window)
        form.title('Новая раскидка')
        form.transient(self.window)
        fields = {}
        for key, label in [('title', 'Откуда → куда'), ('method', 'Ориентир и способ броска')]:
            ttk.Label(form, text=label).pack(anchor='w', padx=12, pady=(8, 0))
            fields[key] = ttk.Entry(form, width=65)
            fields[key].pack(padx=12)
        files = {}

        def pick(key, button):
            file = filedialog.askopenfilename(parent=form, filetypes=[('Изображения', '*.png *.jpg *.jpeg *.webp *.bmp')])
            if file:
                files[key] = file
                button.configure(text=Path(file).name)

        for key, caption in [('aim', 'Выбрать скрин прицела'), ('landing', 'Выбрать скрин приземления')]:
            button = ttk.Button(form, text=caption)
            button.configure(command=lambda k=key, b=button: pick(k, b))
            button.pack(fill='x', padx=12, pady=4)

        def save():
            card = {key: field.get().strip() for key, field in fields.items()}
            if not all(card.values()) or len(files) != 2:
                messagebox.showinfo('Тренер Dust2', 'Заполни оба поля и выбери два скриншота.', parent=form)
                return
            created = []
            temporary = self.index.with_name('lineups.tmp')
            try:
                self.folder.mkdir(parents=True, exist_ok=True)
                for key, file in files.items():
                    target = self.folder / (uuid4().hex + '.png')
                    created.append(target)
                    with self.Image.open(file) as image:
                        image.convert('RGB').save(target)
                    card[key] = target.name
                cards = self.cards + [card]
                temporary.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding='utf-8')
                temporary.replace(self.index)
            except (OSError, ValueError) as exc:
                for target in created + [temporary]:
                    target.unlink(missing_ok=True)
                messagebox.showerror('Тренер Dust2', str(exc), parent=form)
                return
            self.cards = cards
            form.destroy()
            self.query.set(card['title'])

        ttk.Button(form, text='Сохранить', command=save).pack(pady=10)
        fields['title'].focus_set()
