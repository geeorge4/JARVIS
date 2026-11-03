import json
import os
import re
from pathlib import Path

PATH = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'JARVISASSISTENT' / 'memory.json'

class Memory:
    def __init__(self, path=None):
        self.path = path or PATH
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            data = {}
        if not isinstance(data, dict): data = {}
        self.name = str(data.get('name', ''))[:80]
        self.notes = [x[:500] for x in data.get('notes', []) if isinstance(x, str)][-20:]
        self.history = [x for x in data.get('history', []) if isinstance(x, dict) and
                        x.get('role') in ('user', 'assistant') and isinstance(x.get('content'), str)][-12:]

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps({'name': self.name, 'notes': self.notes,
                                   'history': self.history[-12:]}, ensure_ascii=False), encoding='utf-8')
        temp.replace(self.path)

    def remember(self, text):
        match = re.search(r'\bменя зовут\s+([^,.!?\n]{1,80})', text, re.I)
        if match: self.name = match.group(1).strip()
        note = re.match(r'^запомни\s*[:,]?\s*(.+)', text, re.I | re.S)
        if note:
            value = note.group(1).strip()[:500]
            if value not in self.notes: self.notes = (self.notes + [value])[-20:]
        if match or note: self.save()

    def context(self):
        return ('Имя пользователя: ' + self.name + '\n' if self.name else '') + '\n'.join(self.notes)

    def clear(self):
        self.name = ''; self.notes = []; self.history = []; self.save()
