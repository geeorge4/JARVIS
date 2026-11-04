"""Install selected local models for the JARVIS installation."""
from pathlib import Path
import os
import socket
import subprocess
import time
import urllib.request
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
def prepare_voice():
    from huggingface_hub import snapshot_download
    folder = ROOT / 'speech-models'
    folder.mkdir(exist_ok=True)
    for name in ('ru_RU-denis-medium.onnx', 'ru_RU-denis-medium.onnx.json', 'MODEL_CARD'):
        path = folder / name
        if not path.exists():
            temporary = path.with_suffix(path.suffix + '.part')
            urllib.request.urlretrieve('https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/denis/medium/' + name, temporary)
            temporary.replace(path)
    snapshot_download('Systran/faster-whisper-base', local_dir=folder / 'whisper-base', allow_patterns=['config.json', 'model.bin', 'tokenizer.json', 'vocabulary.*'])
    import product
    if 'voice_engine' not in product.load():
        product.save(voice_engine='piper')
    print('Piper and Whisper models ready. Existing settings preserved.')


def prepare_qwen():
    from jarvis import MODEL, ollama_executable

    executable = str(ollama_executable())
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        address = f'127.0.0.1:{listener.getsockname()[1]}'
    env = dict(os.environ, OLLAMA_HOST=address, OLLAMA_MODELS=str(ROOT / 'models'), OLLAMA_NO_CLOUD='1')
    with subprocess.Popen([executable, 'serve'], env=env, creationflags=subprocess.CREATE_NO_WINDOW) as server:
        try:
            for _ in range(90):
                if server.poll() is not None:
                    raise RuntimeError('Ollama stopped before it could start.')
                try:
                    with urllib.request.urlopen(f'http://{address}/api/version', timeout=1):
                        break
                except OSError:
                    time.sleep(1)
            else:
                raise RuntimeError('Ollama did not start in time.')
            subprocess.run([executable, 'pull', MODEL], env=env, check=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        finally:
            if server.poll() is None:
                server.terminate()


if __name__ == '__main__':
    if '--qwen' in sys.argv:
        prepare_qwen()
    else:
        prepare_voice()

