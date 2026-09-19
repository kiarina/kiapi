import hashlib
import json
from pathlib import Path


def media_apc_tenant(
    tenant: str,
    images: list[str],
    audio: list[str],
    videos: list[str],
    *,
    fps: float = 1.0,
    use_audio_in_video: bool = False,
) -> str:
    if not (images or audio or videos):
        return tenant
    payload = {
        "media": [
            [kind, [_file_hash(p) for p in paths]]
            for kind, paths in (("image", images), ("audio", audio), ("video", videos))
        ],
        "fps": fps if videos else None,
        "use_audio_in_video": use_audio_in_video if videos else None,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return f"{tenant}:media:{digest}"


def _file_hash(path: str) -> str:
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()
