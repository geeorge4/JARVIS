"""Поиск через индекс AppOpener; запуск AppID без shell-команд."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ALIASES = {'телеграм': 'telegram', 'телеграмм': 'telegram', 'дискорд': 'discord',
           'стим': 'steam', 'стима': 'steam', 'хром': 'google chrome',
           'гугл хром': 'google chrome', 'вс код': 'visual studio code',
           'роблокс': 'roblox', 'ноушен': 'notion', 'спотифай': 'spotify'}

class Launcher:
    def __init__(self):
        self.apps = None

    def refresh(self, update=False):
        deps = Path(os.environ['LOCALAPPDATA']) / 'JARVISASSISTENT' / 'app-deps'
        if str(deps) not in sys.path: sys.path.insert(0, str(deps))
        import AppOpener
        if update:
            # AppOpener кеширует существование Data при первом импорте.
            AppOpener.check.check_data = (Path(AppOpener.__file__).parent / 'Data').is_dir()
            AppOpener.check.create_file(print_text=False)
            AppOpener.check.app_names()
        path = Path(AppOpener.__file__).parent / 'Data' / 'data.json'
        self.apps = {k.strip().lower(): v for k,v in json.loads(path.read_text()).items()
                     if k.strip() and isinstance(v,str)}
        return len(self.apps)

    @staticmethod
    def target(text):
        text = text.lower().replace('ё','е').strip(' .,!?')
        match = re.search(r'(?:откро[йи]|открыть|открывай|запусти(?:ть)?|включи(?:ть)?|open|launch|start)\s+(.+)', text)
        if not match: return None
        name = re.sub(r'\b(?:пожалуйста|мне|приложение|программу|сейчас)\b', '', match.group(1))
        name = re.sub(r'\s+',' ',name).strip(' .,!?')
        return ALIASES.get(name,name)

    def find(self, name):
        if self.apps is None: self.refresh()
        name = ALIASES.get(name.lower(),name.lower())
        if name in self.apps: return name, []
        matches = [n for n in self.apps if name and name in n]
        if len(matches)==1: return matches[0], []
        if matches: return None, sorted(matches)[:6]
        import difflib
        return None, difflib.get_close_matches(name,list(self.apps),n=4,cutoff=.55)

    def open(self, name):
        selected, suggestions = self.find(name)
        if not selected:
            return ('Нашёл несколько вариантов: ' if suggestions else 'Приложение не найдено: ') + (', '.join(suggestions) if suggestions else name) + '. Уточни название.'
        subprocess.Popen(['explorer.exe', 'shell:AppsFolder\\' + self.apps[selected]])
        return 'Отправил команду открыть ' + selected + '.'
