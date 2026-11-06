"""Shared storage for desktop notes created by UI and voice commands."""
from datetime import datetime
import json
import threading

_lock = threading.RLock()


class Notes:
    def __init__(self, path):
        self.path = path

    def list(self):
        with _lock:
            try:
                notes = json.loads(self.path.read_text(encoding='utf-8'))
            except FileNotFoundError:
                return []
            if not isinstance(notes, list) or not all(
                    isinstance(note, dict) and isinstance(note.get('text'), str) for note in notes):
                raise ValueError('Файл заметок имеет неизвестный формат.')
            return notes

    def _save(self, notes):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(notes, ensure_ascii=False), encoding='utf-8')
        temporary.replace(self.path)

    def add(self, text):
        with _lock:
            notes = self.list()
            notes.append({'text': text[:4000], 'date': datetime.now().isoformat(timespec='seconds')})
            self._save(notes[-200:])

    def change(self, index, expected, text=None):
        with _lock:
            notes = self.list()
            if index >= len(notes) or notes[index] != expected:
                raise ValueError('Список заметок изменился. Выбери заметку заново.')
            if text is None:
                del notes[index]
            else:
                notes[index] = dict(expected, text=text[:4000])
            self._save(notes)

