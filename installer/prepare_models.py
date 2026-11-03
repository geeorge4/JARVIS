"""Optional data-only downloads. Run manually after installing dependencies."""
from pathlib import Path
import urllib.request
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if __name__ == '__main__':
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
