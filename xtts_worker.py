"""Изолированный XTTS-процесс: JSON-lines, без доступа к командам компьютера."""
import contextlib
import json
from pathlib import Path
import sys

sys.stdin.reconfigure(encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')

model_dir=Path(sys.argv[1]);reference=Path(sys.argv[2])
with contextlib.redirect_stdout(sys.stderr):
    import torch
    import soundfile as sf
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts
    torch.set_num_threads(4)
    config=XttsConfig();config.load_json(str(model_dir/'config.json'))
    model=Xtts(config)
    model.load_checkpoint(config,checkpoint_dir=str(model_dir),eval=True,use_deepspeed=False)
    model.cpu()
    conditioning,speaker=model.get_conditioning_latents(audio_path=str(reference),gpt_cond_len=6,
        gpt_cond_chunk_len=config.gpt_cond_chunk_len,max_ref_length=config.max_ref_len,
        sound_norm_refs=config.sound_norm_refs)
for line in sys.stdin:
    try:
        request=json.loads(line)
        with contextlib.redirect_stdout(sys.stderr),torch.inference_mode():
            result=model.inference(request['text'],request.get('language','ru'),conditioning,speaker,
                                   speed=request.get('speed',1.0),
                                   repetition_penalty=config.repetition_penalty,
                                   temperature=config.temperature,top_k=config.top_k,top_p=config.top_p,
                                   enable_text_splitting=len(request['text'])>200)
            sf.write(request['output'],result['wav'],24000)
        print(json.dumps({'ok':True}),flush=True)
    except Exception as exc:print(json.dumps({'ok':False,'error':str(exc)}),flush=True)
