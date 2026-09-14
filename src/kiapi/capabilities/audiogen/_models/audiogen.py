"""Handler for AudioGen (text → sound effect; ``facebook/audiogen-medium``).

Owns the load + generate flow, ported from mlx-audiocraft-server's
generation.run_generation. Generates a 16 kHz mono WAV, stores it in the global
file store, and returns the artifact metadata (the job's ``result``).
"""

import time
from types import SimpleNamespace
from typing import Any

from kiapi.core.file import FileStore
from kiapi.core.model import ModelSpec
from kiapi.core.workdir import create_work_dir

from .._helpers.attach_audiogen_progress import attach_audiogen_progress
from .._views.generate_params import GenerateParams

FEATURES = {"text"}


def load(spec: ModelSpec) -> SimpleNamespace:
    from mlx_audiocraft import AudioGen  # type: ignore

    model = AudioGen.get_pretrained(spec.repo)
    return SimpleNamespace(model=model)


def warmup(payload: SimpleNamespace) -> None:
    """Prime weights + MLX kernels with a tiny generation (artifact discarded)."""
    model = payload.model
    model.set_generation_params(duration=1.0)
    model.generate(["click"])


def run(
    payload: SimpleNamespace,
    params: GenerateParams,
    files: FileStore,
) -> dict[str, Any]:
    """Blocking generation on the resident model. Returns artifact metadata."""
    import mlx.core as mx
    import numpy as np
    import soundfile as sf  # type: ignore

    model = payload.model

    mx.random.seed(params.seed)

    model.set_generation_params(
        duration=params.duration,
        top_k=params.top_k,
        top_p=params.top_p,
        temperature=params.temperature,
        cfg_coef=params.cfg_coef,
    )

    attach_audiogen_progress(model)

    t0 = time.time()
    wavs = model.generate([params.prompt], progress=True)  # [B, C, T] mlx array
    total_s = round(time.time() - t0, 2)

    # [B, C, T] -> [T, C] (soundfile wants samples-major); squeeze mono to 1-D.
    arr = np.array(wavs[0])  # [C, T]
    arr = arr.T  # [T, C]
    if arr.shape[1] == 1:
        arr = arr[:, 0]

    sample_rate = int(model.sample_rate)
    tmp_dir = create_work_dir("audio/audiogen")
    tmp_wav = tmp_dir / "se.wav"
    sf.write(str(tmp_wav), arr, sample_rate)
    if not tmp_wav.exists():
        raise RuntimeError("generation finished but no audio file was produced")

    duration_s = round(arr.shape[0] / sample_rate, 3)
    meta = {
        "model": params.model,
        "prompt": params.prompt,
        "params": params.model_dump(),
        "duration_s": duration_s,
        "sample_rate": sample_rate,
        "timings": {"total_s": total_s},
    }
    rec = files.put_path(
        tmp_wav,
        filename=f"se_{int(time.time())}.wav",
        content_type="audio/wav",
        meta=meta,
        move=True,
    )

    return {
        "file_id": rec.file_id,
        "audio_bytes": rec.size,
        **meta,
    }
