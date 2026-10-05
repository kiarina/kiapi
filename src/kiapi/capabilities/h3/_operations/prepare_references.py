"""Convert staged reference files into mlx-serve's Ref2VA request fields."""

import base64
import subprocess
from pathlib import Path
from typing import Any

FPS = 24
# H3 accepts reference audio clips of 2 to 15 seconds.
MAX_AUDIO_S = 15


def prepare_references(
    *,
    images: list[str],
    videos: list[str],
    audios: list[str],
    use_video_audio: bool,
    width: int,
    height: int,
    num_frames: int,
    work_dir: Path,
) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    if images:
        fields["ref_images"] = [
            _b64(_as_image(Path(path), work_dir / f"image_{i}.png"))
            for i, path in enumerate(images)
        ]
    if videos:
        fields["ref_videos"] = [
            _video_entry(
                Path(path),
                work_dir / f"video_{i}",
                width=width,
                height=height,
                num_frames=num_frames,
                with_audio=use_video_audio,
            )
            for i, path in enumerate(videos)
        ]
    if audios:
        fields["ref_audios"] = [
            _b64(_as_wav(Path(path), work_dir / f"audio_{i}.wav"))
            for i, path in enumerate(audios)
        ]
    return fields


def _video_entry(
    src: Path,
    out_dir: Path,
    *,
    width: int,
    height: int,
    num_frames: int,
    with_audio: bool,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    _ffmpeg(
        "-i",
        str(src),
        "-vf",
        f"fps={FPS},scale={width}:{height}:force_original_aspect_ratio=decrease",
        "-frames:v",
        str(num_frames),
        "-q:v",
        "2",
        str(out_dir / "%04d.jpg"),
    )
    frames = sorted(out_dir.glob("*.jpg"))
    if not frames:
        raise ValueError(f"no frames could be decoded from reference video {src.name}")
    entry: dict[str, Any] = {"frames": [_b64(frame) for frame in frames]}
    if with_audio and has_audio(src):
        seconds = len(frames) / FPS
        wav = out_dir / "audio.wav"
        _ffmpeg("-i", str(src), "-vn", "-t", f"{seconds:.3f}", str(wav))
        entry["audio"] = _b64(wav)
    return entry


def _as_image(src: Path, dst: Path) -> Path:
    if src.suffix.lower() in (".png", ".jpg", ".jpeg"):
        return src
    _ffmpeg("-i", str(src), "-frames:v", "1", str(dst))
    return dst


def _as_wav(src: Path, dst: Path) -> Path:
    _ffmpeg("-i", str(src), "-vn", "-t", str(MAX_AUDIO_S), str(dst))
    return dst


def has_audio(src: Path) -> bool:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            str(src),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(out.stdout.strip())


def _ffmpeg(*args: str) -> None:
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", *args],
        check=True,
        capture_output=True,
    )


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()
