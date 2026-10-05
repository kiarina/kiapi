"""Handler for MiniMax H3 Ref2VA (text + references → video with stereo audio; via mlx-serve)."""

import base64
import subprocess
import time
from pathlib import Path
from typing import Any

from huggingface_hub import hf_hub_download, snapshot_download

from kiapi.core.file import FileStore
from kiapi.core.job import ProgressReporter
from kiapi.core.workdir import create_work_dir

from .._operations.prepare_references import prepare_references
from .._operations.run_mlx_serve import generate_video, mlx_serve
from .._settings import H3Settings
from .._views.generate_params import GenerateParams

# Loading, encoding and decoding around the denoising loop.
SETUP_FRACTION = 0.05
DECODE_FRACTION = 0.05


def run_generate(
    params: GenerateParams,
    settings: H3Settings,
    files: FileStore,
    staged: dict[str, list[str]],
    *,
    request_prompt: str,
) -> dict[str, Any]:
    """Blocking generation. Returns artifact metadata (the job's ``result``)."""
    reporter = ProgressReporter.current()
    tmp = create_work_dir("video/h3")
    model_dir = snapshot_download(settings.model_repo, local_files_only=True)

    body: dict[str, Any] = {
        "prompt": params.prompt,
        "width": params.width,
        "height": params.height,
        "num_frames": params.num_frames,
        "steps": params.steps,
        "seed": params.seed,
        "fast": params.fast,
    }
    if params.turbo:
        body["lora_paths"] = [
            hf_hub_download(
                settings.turbo_lora_repo,
                settings.turbo_lora_file,
                local_files_only=True,
            )
        ]
        body["lora_scales"] = [1.0]
    body |= prepare_references(
        images=staged["images"],
        videos=staged["videos"],
        audios=staged["audios"],
        use_video_audio=params.use_video_audio,
        width=params.width,
        height=params.height,
        num_frames=params.num_frames,
        work_dir=tmp,
    )

    def on_progress(stage: str, step: int, total: int) -> None:
        if total > 0:
            span = 1.0 - SETUP_FRACTION - DECODE_FRACTION
            reporter.update(
                SETUP_FRACTION + span * step / total, f"{stage} {step}/{total}"
            )

    t0 = time.time()
    reporter.update(0.01, "starting mlx-serve")
    with mlx_serve(
        settings, model_dir=model_dir, log_path=tmp / "mlx-serve.log"
    ) as url:
        reporter.update(SETUP_FRACTION / 2, "encoding prompt and references")
        result = generate_video(url, body, on_progress=on_progress)
    reporter.update(1.0 - DECODE_FRACTION, "writing mp4")
    video_path = tmp / "video.mp4"
    has_audio = _write_mp4(result, tmp, video_path)
    total_s = round(time.time() - t0, 2)

    gen_params = params.gen_params() | {
        "prompt": request_prompt,
        "enhanced_prompt": params.prompt if params.prompt != request_prompt else None,
        "num_frames": int(result["frames"]),
    }
    meta = {
        "prompt": request_prompt,
        "params": gen_params,
        "references": {kind: len(paths) for kind, paths in staged.items()},
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


def _write_mp4(result: dict[str, Any], tmp: Path, video_path: Path) -> bool:
    rgb = tmp / "frames.rgb"
    rgb.write_bytes(base64.b64decode(result["data"]))
    cmd = [
        "ffmpeg",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{result['width']}x{result['height']}",
        "-r",
        str(result.get("fps", 24)),
        "-i",
        str(rgb),
    ]
    has_audio = bool(result.get("audio_data"))
    if has_audio:
        pcm = tmp / "audio.pcm"
        pcm.write_bytes(base64.b64decode(result["audio_data"]))
        cmd += [
            "-f",
            "s16le",
            "-ar",
            str(result["audio_sample_rate"]),
            "-ac",
            str(result["audio_channels"]),
            "-i",
            str(pcm),
            "-c:a",
            "aac",
        ]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest", str(video_path)]
    subprocess.run(cmd, check=True, capture_output=True)
    rgb.unlink()
    (tmp / "audio.pcm").unlink(missing_ok=True)
    return has_audio
