"""Handler for LTX-2.5 distilled (text/image/audio → video; via mlx-video)."""

import time
from pathlib import Path
from typing import Any

from kiapi.core.file import FileStore
from kiapi.core.workdir import create_work_dir

from .._settings import LTX2Settings
from .._views.generate_params import GenerateParams

FEATURES = {"text", "image", "audio"}

# Untiled diffusion decoding peaks near 51 GB at 768x512 / 121 frames; 2x2 tiles
# keep it under the transformer's own peak.
DIFFUSION_VAE_SPATIAL_TILES = 2


def warmup(payload: object | None = None) -> None:
    """Prime kernels with a tiny T2V generation (artifact discarded)."""
    from mlx_video.models.ltx_2.generate import (  # type: ignore
        PipelineType,
        generate_video,
    )

    from .._settings import settings_manager

    s = settings_manager.get_settings()
    tmp = create_work_dir("video/ltx2/warmup")
    generate_video(
        model_repo=s.ltx25_model_repo,
        text_encoder_repo=None,  # pyright: ignore
        prompt="warmup",
        pipeline=PipelineType.DISTILLED,
        height=256,
        width=256,
        num_frames=9,
        fps=24,
        seed=0,
        output_path=str(tmp / "warm.mp4"),
        verbose=False,
    )


def run_generate(
    params: GenerateParams,
    settings: LTX2Settings,
    files: FileStore,
    staged: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    """Blocking generation. Returns artifact metadata (the job's ``result``)."""
    from mlx_video.models.ltx_2.generate import PipelineType, generate_video

    tmp = create_work_dir("video/ltx2")
    video_path = tmp / "video.mp4"

    image = staged.get("image")
    end_image = staged.get("end_image")
    audio_file = staged.get("audio")
    wants_audio = audio_file is not None or params.generate_audio
    audio_out = str(tmp / "audio.wav") if wants_audio else None
    pipeline = PipelineType.DFR if params.pipeline == "dfr" else PipelineType.DISTILLED
    tiles = DIFFUSION_VAE_SPATIAL_TILES if params.video_decoder == "diffusion" else 1

    t0 = time.time()
    output = generate_video(
        model_repo=settings.ltx25_model_repo,
        text_encoder_repo=None,  # pyright: ignore
        prompt=params.prompt,
        pipeline=pipeline,
        height=params.height,
        width=params.width,
        num_frames=params.num_frames,
        fps=params.fps,
        seed=params.seed,
        output_path=str(video_path),
        enhance_prompt=params.enhance_prompt,
        prompt_enhancer_repo=settings.prompt_enhancer_repo,
        image=image,
        image_strength=params.image_strength,
        end_image=end_image,
        end_image_strength=params.end_image_strength,
        audio=params.generate_audio,
        audio_file=audio_file,
        output_audio_path=audio_out,
        auto_duration_max_seconds=min(20.0, settings.max_num_frames / params.fps),
        detailing_lora=settings.detailing_lora_repo,
        video_decoder=params.video_decoder,
        diffusion_vae_spatial_tiles=tiles,
        verbose=False,
    )
    total_s = round(time.time() - t0, 2)

    if not video_path.exists():
        raise RuntimeError("generation finished but no video file was produced")

    # Audio (when requested) is muxed into video.mp4 by mlx-video; drop the wav.
    has_audio = audio_out is not None and Path(audio_out).exists()
    if audio_out is not None:
        Path(audio_out).unlink(missing_ok=True)

    video_np = output[0] if isinstance(output, tuple) else output
    gen_params = params.gen_params() | {"num_frames": len(video_np)}
    meta = {
        "mode": mode,
        "prompt": params.prompt,
        "params": gen_params,
        "has_audio": has_audio,
        "timings": {"total_s": total_s},
    }
    rec = files.put_path(
        video_path,
        filename=f"video_{int(time.time())}.mp4",
        content_type="video/mp4",
        meta=meta,
        move=True,
    )
    return {"file_id": rec.file_id, "video_bytes": rec.size, **meta}
