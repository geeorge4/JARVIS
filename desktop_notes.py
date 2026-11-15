"""Shared storage for desktop notes created by UI and voice commands."""
from datetime import datetime
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
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

    def export_text(self, destination):
        destination = Path(destination)
        if destination.suffix.lower() != '.txt':
            raise ValueError('Для экспорта выбери файл с расширением .txt.')
        notes = self.list()
        if not notes:
            return 0
        blocks = []
        for index, note in enumerate(notes, start=1):
            date = note.get('date')
            heading = f'Заметка {index}'
            if isinstance(date, str) and date.strip():
                heading += f' · {date.replace("T", " ", 1)}'
            blocks.append(f'{heading}\n{note["text"]}')
        temporary = None
        try:
            with NamedTemporaryFile(mode='w', encoding='utf-8', dir=destination.parent,
                                    prefix='.jarvis-notes-', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write('\n\n'.join(blocks) + '\n')
            temporary.replace(destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return len(notes)

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

