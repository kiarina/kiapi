import shutil
import subprocess
from pathlib import Path

import pytest

from kiapi.capabilities.h3._operations.enhance_prompt import (
    _audio_notes,
    build_rewrite_messages,
    clean_rewrite,
    is_structured,
    labels_within,
)


def test_is_structured_detects_both_guide_formats() -> None:
    assert is_structured("subject_definitions:\n<Subject 1> is ...")
    assert is_structured("integrated_multimodal_description: [Shot 1] ...")
    assert not is_structured("a cat waves at the camera")


def test_clean_rewrite_strips_fences_and_thinking() -> None:
    raw = "<think>plan</think>\n```text\nsummary:\nx\n```"

    assert clean_rewrite(raw) == "summary:\nx"


def test_build_rewrite_messages_labels_references_in_order() -> None:
    messages = build_rewrite_messages(
        "GUIDE",
        prompt="<Picture 2> meets <Picture 1>",
        images=["data:image/jpeg;base64,a", "data:image/jpeg;base64,b"],
        video_frames=[["data:image/jpeg;base64,c"]],
        audio_notes=["<Audio 1>: a standalone audio clip (3.0 s)."],
        seconds=5.2,
        width=960,
        height=544,
    )

    assert messages[0]["role"] == "system"
    assert messages[0]["content"].endswith("GUIDE")
    texts = [part["text"] for part in messages[1]["content"] if part["type"] == "text"]
    assert texts[:4] == [
        "<Picture 1>:",
        "<Picture 2>:",
        "<Video 1> (frames sampled in order; not separate pictures):",
        "<Audio 1>: a standalone audio clip (3.0 s).",
    ]
    assert "5.2 seconds, 960x544" in texts[-1]
    assert "full-reference six-section" in texts[-1]


def test_build_rewrite_messages_uses_text_format_without_references() -> None:
    messages = build_rewrite_messages(
        "GUIDE",
        prompt="a fox in snow",
        images=[],
        video_frames=[],
        audio_notes=[],
        seconds=5.2,
        width=960,
        height=544,
    )

    assert "text-to-video format" in messages[1]["content"][-1]["text"]


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_audio_notes_number_soundtracks_before_standalone_audio(tmp_path: Path) -> None:
    def ffmpeg(*args: str) -> None:
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)

    silent = tmp_path / "silent.mp4"
    ffmpeg("-f", "lavfi", "-i", "testsrc=s=64x64:r=24:d=2", str(silent))
    voiced = tmp_path / "voiced.mp4"
    ffmpeg(
        "-f", "lavfi", "-i", "testsrc=s=64x64:r=24:d=2",
        "-f", "lavfi", "-i", "sine=d=2", "-shortest", str(voiced),
    )  # fmt: skip
    clip = tmp_path / "clip.wav"
    ffmpeg("-f", "lavfi", "-i", "sine=d=3", str(clip))

    notes = _audio_notes(
        {"images": [], "videos": [str(silent), str(voiced)], "audios": [str(clip)]},
        use_video_audio=True,
    )

    assert notes[0].startswith("<Audio 1>: the soundtrack of <Video 2>")
    assert notes[1].startswith("<Audio 2>: a standalone audio clip (3.0 s)")


def test_labels_within_rejects_labels_without_a_reference() -> None:
    counts = {"Picture": 0, "Video": 1, "Audio": 1}

    assert labels_within("<Subject 1> from <Video 1> with <Audio 1>", counts)
    assert not labels_within("<Picture 1> is the last frame of <Video 1>", counts)
    assert not labels_within("<Audio 2>", counts)


def test_build_rewrite_messages_lists_the_existing_labels() -> None:
    messages = build_rewrite_messages(
        "GUIDE",
        prompt="continue <Video 1>",
        images=[],
        video_frames=[["data:image/jpeg;base64,c"]],
        audio_notes=["<Audio 1>: the soundtrack of <Video 1> (3.0 s)."],
        seconds=5.2,
        width=960,
        height=544,
    )

    assert (
        "Reference labels that exist: <Video 1>, <Audio 1>."
        in (messages[1]["content"][-1]["text"])
    )
