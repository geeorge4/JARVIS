"""Native PCM measurement with a fallback for source-only installs."""
import ctypes
from pathlib import Path

import numpy as np


try:
    _library = ctypes.CDLL(str(Path(__file__).with_name('jarvis_audio.dll')))
    _rms = _library.jarvis_pcm_rms
    _rms.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
    _rms.restype = ctypes.c_float
except (OSError, AttributeError):
    _rms = None


def pcm_rms(samples):
    samples = np.ascontiguousarray(samples, dtype=np.float32)
    if _rms is not None:
        return _rms(samples.ctypes.data, samples.size)
    return float(np.sqrt(np.mean(samples * samples))) if samples.size else 0.0
