import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from desktop_notes import Notes


class NotesExportTests(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.store = Notes(self.root / 'notes.json')

    def test_export_preserves_russian_text_line_breaks_and_original_notes(self):
        notes = [{'text': 'Список\n• молоко', 'date': '2026-11-15T11:00:00'},
                 {'text': 'Старая заметка без даты'}]
        self.store.path.write_text(json.dumps(notes, ensure_ascii=False), encoding='utf-8')
        target = self.root / 'заметки.txt'
        self.assertEqual(self.store.export_text(target), 2)
        self.assertEqual(target.read_text(encoding='utf-8'),
                         'Заметка 1 · 2026-11-15 11:00:00\nСписок\n• молоко\n\n'
                         'Заметка 2\nСтарая заметка без даты\n')
        self.assertEqual(self.store.list(), notes)

    def test_empty_export_leaves_existing_file_alone(self):
        target = self.root / 'заметки.txt'
        target.write_text('Старый экспорт', encoding='utf-8')
        self.assertEqual(self.store.export_text(target), 0)
        self.assertEqual(target.read_text(encoding='utf-8'), 'Старый экспорт')

    def test_export_cannot_replace_notes_database(self):
        self.store.add('Молоко')
        with self.assertRaises(ValueError):
            self.store.export_text(self.store.path)
        self.assertEqual(self.store.list()[0]['text'], 'Молоко')
