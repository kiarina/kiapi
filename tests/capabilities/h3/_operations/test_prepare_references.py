import base64
import shutil
import subprocess
from pathlib import Path

import pytest

from kiapi.capabilities.h3._operations.prepare_references import prepare_references

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


def test_prepare_references_orders_fields_and_cuts_videos(tmp_path: Path) -> None:
    image = tmp_path / "a.png"
    _ffmpeg("-f", "lavfi", "-i", "color=red:s=64x48", "-frames:v", "1", str(image))
    video = tmp_path / "v.mp4"
    _ffmpeg(
        "-f", "lavfi", "-i", "testsrc=s=128x96:r=24:d=2",
        "-f", "lavfi", "-i", "sine=d=2",
        "-shortest", str(video),
    )  # fmt: skip
    audio = tmp_path / "s.mp3"
    _ffmpeg("-f", "lavfi", "-i", "sine=d=2", str(audio))

    fields = prepare_references(
        images=[str(image)],
        videos=[str(video)],
        audios=[str(audio)],
        use_video_audio=True,
        width=64,
        height=64,
        num_frames=22,
        work_dir=tmp_path / "work",
    )

    assert base64.b64decode(fields["ref_images"][0]) == image.read_bytes()
    clip = fields["ref_videos"][0]
    assert len(clip["frames"]) == 22
    assert base64.b64decode(clip["audio"])[:4] == b"RIFF"
    assert base64.b64decode(fields["ref_audios"][0])[:4] == b"RIFF"


def test_prepare_references_skips_video_audio_unless_requested(
    tmp_path: Path,
) -> None:
    video = tmp_path / "v.mp4"
    _ffmpeg("-f", "lavfi", "-i", "testsrc=s=64x64:r=24:d=1", str(video))

    fields = prepare_references(
        images=[],
        videos=[str(video)],
        audios=[],
        use_video_audio=False,
        width=64,
        height=64,
        num_frames=56,
        work_dir=tmp_path / "work",
    )

    assert set(fields) == {"ref_videos"}
    assert "audio" not in fields["ref_videos"][0]
    assert len(fields["ref_videos"][0]["frames"]) == 24
