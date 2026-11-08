"""Live CS2 session card."""
import tkinter as tk
from game_journal import session, LOCK


class SessionPanel:
    def __init__(self, app, parent):
        card = tk.Frame(parent, bg='#191919', highlightbackground='#303030', highlightthickness=1)
        card.pack(fill='x', padx=4, pady=12)
        header = tk.Frame(card, bg='#191919')
        header.pack(fill='x', padx=18, pady=16)
        tk.Label(header, text='JARVIS · ИГРОВАЯ СЕССИЯ', bg='#191919', fg='#aaa',
                 font=('Segoe UI', 11, 'bold')).pack(side='left')
        tk.Label(header, text=' CS2 ', bg='#143422', fg='#37cc78',
                 font=('Segoe UI', 11, 'bold')).pack(side='right')
        grid = tk.Frame(card, bg='#191919')
        grid.pack(fill='x', padx=18)
        self.values = {}
        for i, title in enumerate(('Убийства', 'Смерти', 'K/D', 'Игровое время', 'Средний FPS')):
            column, row = i % 2, (i // 2) * 2
            grid.columnconfigure(column, weight=1, uniform='stat')
            tk.Label(grid, text=title, bg='#191919', fg='#aaa', anchor='w').grid(
                row=row, column=column, sticky='ew', pady=(4, 0))
            value = tk.Label(grid, text='—', bg='#191919',
                             fg='#37cc78' if title in ('Убийства', 'K/D') else '#fff',
                             font=('Segoe UI', 25, 'bold'), anchor='w')
            value.grid(row=row+1, column=column, sticky='ew', pady=(0, 10))
            self.values[title] = value
        self.note = tk.Label(card, bg='#191919', fg='#aaa', justify='left', anchor='w',
                            text='Данные JARVIS могут включать ботов и тренировочные режимы.\n'
                                 'FPS — среднее по замерам подключённого CSV во время игры.')
        self.note.pack(fill='x', padx=18, pady=10)
        controls = tk.Frame(parent, bg='#121212')
        controls.pack(fill='x')
        app.button(controls, 'Новая сессия', lambda: app.dispatch('начать игровую сессию')).pack(side='left')
        app.button(controls, 'Завершить', lambda: app.dispatch('завершить игровую сессию')).pack(side='left', padx=4)
        app.button(controls, 'Подключить FPS', app.choose_fps_csv).pack(side='left')
        self.refresh()

    def refresh(self):
        with LOCK:
            data = dict(session.data)
        kills, deaths = data.get('kills', 0), data.get('deaths', 0)
        minutes = int(data.get('active_seconds', 0) // 60)
        count = data.get('fps_count', 0)
        values = (str(kills), str(deaths), f'{kills/deaths:.2f}'.replace('.', ',') if deaths else '—',
                  f'{minutes//60} ч {minutes%60} мин',
                  str(round(data.get('fps_sum', 0)/count)) if count else 'Нет замеров')
        for label, value in zip(self.values.values(), values):
            label.configure(text=value if data else '—')
