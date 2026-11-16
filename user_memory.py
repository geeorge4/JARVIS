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
        self.notes = [x[:500] for x in data.get('notes', []) if isinstance(x, str)]
        self.history = [x for x in data.get('history', []) if isinstance(x, dict) and
                        x.get('role') in ('user', 'assistant') and isinstance(x.get('content'), str)]

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps({'name': self.name, 'notes': self.notes,
                                   'history': self.history}, ensure_ascii=False), encoding='utf-8')
        temp.replace(self.path)

    def remember(self, text):
        match = re.search(r'\bменя зовут\s+([^,.!?\n]{1,80})', text, re.I)
        if match: self.name = match.group(1).strip()
        note = re.match(r'^запомни\s*[:,]?\s*(.+)', text, re.I | re.S)
        if note:
            value = note.group(1).strip()[:500]
            if value not in self.notes: self.notes.append(value)
        if match or note: self.save()

    @staticmethod
    def keywords(text):
        stop = {'что', 'как', 'это', 'когда', 'который', 'почему', 'помнишь',
                'расскажи', 'напомни', 'раньше', 'про', 'мне', 'мой', 'моя', 'моё'}
        return {token for token in re.findall(r'\w+', text.casefold().replace('ё', 'е'))
                if len(token) > 2 and token not in stop}

    def context(self, prompt='', recent=12, budget=1800):
        terms = self.keywords(prompt)
        candidates = []
        for note in self.notes:
            candidates.append((len(terms & self.keywords(note)), note))
        # Search old exchanges while keeping the latest turns in the normal chat context.
        archived = self.history[:-recent] if recent else self.history
        for index, item in enumerate(archived):
            if item['role'] != 'user':
                continue
            score = len(terms & self.keywords(item['content']))
            if score:
                excerpt = 'Пользователь: ' + item['content'][:300]
                following = archived[index+1:index+2]
                if following and following[0]['role'] == 'assistant':
                    excerpt += '\nДжарвис: ' + following[0]['content'][:300]
                candidates.append((score, excerpt))
        lines = ['Имя пользователя: ' + self.name] if self.name else []
        for _, excerpt in sorted(reversed(candidates), key=lambda pair: pair[0], reverse=True):
            remaining = budget - sum(len(line)+1 for line in lines)
            if remaining < 80:
                break
            lines.append(excerpt[:remaining])
        return '\n'.join(lines)

    def clear(self):
        self.name = ''; self.notes = []; self.history = []; self.save()
