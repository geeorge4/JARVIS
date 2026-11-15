import io
import json
import unittest
from unittest.mock import patch

from jarvis import FALLBACK_MODEL, MODEL, PRIVATE_OLLAMA, SYSTEM_OLLAMA, Jarvis


class OllamaSelectionTests(unittest.TestCase):
    def test_empty_private_store_reuses_system_model(self):
        assistant = Jarvis.__new__(Jarvis)
        with patch.object(assistant, '_installed_models', side_effect=[set(), {FALLBACK_MODEL}]):
            with patch('jarvis.LOCAL_HTTP.open', return_value=io.BytesIO(b'{}')) as send:
                with assistant._open_chat({'stream': False}):
                    pass
                request = send.call_args.args[0]
                self.assertEqual(request.full_url, SYSTEM_OLLAMA + '/api/chat')
                self.assertEqual(json.loads(request.data)['model'], FALLBACK_MODEL)

    def test_existing_private_instruct_model_stays_preferred(self):
        assistant = Jarvis.__new__(Jarvis)
        with patch.object(assistant, '_installed_models', return_value={MODEL}) as list_models:
            self.assertEqual(assistant._choose_chat_target(), (PRIVATE_OLLAMA, MODEL))
            list_models.assert_called_once_with(PRIVATE_OLLAMA)
