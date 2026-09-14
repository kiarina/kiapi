"""Load an audio file as a mono float32 array at the target sampling rate.

Replaces ``mlx_vlm.utils.load_audio`` for the Qwen3-Omni audio path. That helper
has a bug: ``read_audio`` returns audio channel-last ``(samples, channels)``, but
``load_audio`` then resamples with ``resample_audio(..., axis=-1)`` (the *channel*
axis) while downmixing with ``mean(axis=1)`` (also the channel axis). The two are
inconsistent, so a stereo clip whose rate differs from the target (e.g. a 48 kHz
stereo wav) is never actually resampled on the time axis — its 48 kHz samples are
handed to the model as if they were 16 kHz, and Omni can't recognize the speech.
Mono clips happen to work because their only axis is the time axis.

Here we downmix to mono *first* (so the array is 1-D) and only then resample, so
``resample_audio``'s default ``axis=-1`` is the time axis and the rate conversion
is correct. Drop this once mlx-vlm fixes ``load_audio``.
"""

import numpy as np


def load_audio_mono(path: str, sr: int) -> np.ndarray:
    """Read ``path`` and return a mono float32 array resampled to ``sr`` Hz."""
    from mlx_audio.audio_io import read as read_audio  # type: ignore
    from mlx_audio.utils import resample_audio  # type: ignore

    audio, orig_sr = read_audio(path, dtype="float32")
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim > 1:  # (samples, channels) → mono, before any resample
        audio = audio.mean(axis=1)
    if orig_sr != sr:
        audio = resample_audio(audio, orig_sr, sr)  # 1-D, so axis=-1 is time
    return np.asarray(audio, dtype=np.float32)
