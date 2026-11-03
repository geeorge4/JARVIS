# Third-party components and personal assets

The MIT license in this repository covers original JARVIS source code only.
It does not relicense Python, libraries, neural models, voices, songs or game assets.

Dependencies are installed separately. Consult their upstream licenses:

- [Python](https://docs.python.org/3/license.html): PSF license and included third-party notices.
- [Ollama](https://github.com/ollama/ollama): MIT; individual models have their own licenses.
- [Qwen3](https://huggingface.co/Qwen): consult the exact model card.
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper): MIT; CTranslate2, FFmpeg/PyAV and model licenses also apply.
- [Piper](https://github.com/OHF-Voice/piper1-gpl): GPL-3.0; individual voices have separate model cards.
- [Piper Denis model card](https://huggingface.co/rhasspy/piper-voices/blob/main/ru/ru_RU/denis/medium/MODEL_CARD).
- [Coqui TTS](https://github.com/idiap/coqui-ai-TTS): consult upstream; XTTS model weights use a separate model license.
- NumPy, sounddevice/PortAudio, Pillow, pystray, pywin32, psutil and AppOpener retain their upstream licenses.

The public package intentionally excludes songs, recorded voice references,
XTTS-generated personal samples, downloaded runtimes, model weights and personal data.
Users may add their own permitted audio files locally; installing an update does
not remove them. No game client, game code or Valve/Gaijin assets are distributed.

JARVIS is an independent project, not affiliated with Valve, Gaijin, Roblox,
Marvel, Microsoft or the authors of any optional models or music.
