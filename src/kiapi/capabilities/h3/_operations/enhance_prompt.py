"""Rewrite a request into MiniMax's structured H3 prompt with a kiapi chat model.

This stands in for MiniMax's hosted H3-Context-IR: the chat model reads the
official prompt guide, sees the reference images and frames of the reference
videos, and writes the sections H3 was trained on.
"""

import base64
import re
import subprocess
from pathlib import Path
from typing import Any

from kiapi.capabilities.chat import ChatRequest, handle_chat
from kiapi.core.app import AppContext
from kiapi.core.job import ProgressReporter
from kiapi.core.model import model_registry

from .._helpers.mlx_serve_paths import prompt_guide
from .._settings import H3Settings
from .._views.generate_params import GenerateParams
from .prepare_references import FPS, has_audio

STRUCTURED_MARKERS = ("subject_definitions:", "integrated_multimodal_description:")
LABEL = re.compile(r"<(Picture|Video|Audio) (\d+)>")
FRAME_POINTS = (0.05, 0.5, 0.95)
PREVIEW_WIDTH = 512


def is_structured(prompt: str) -> bool:
    return any(marker in prompt for marker in STRUCTURED_MARKERS)


def enhance_prompt(
    ctx: AppContext,
    params: GenerateParams,
    staged: dict[str, list[str]],
    settings: H3Settings,
    work_dir: Path,
) -> str:
    if not params.enhance_prompt or is_structured(params.prompt):
        return params.prompt

    ProgressReporter.current().update(0.0, "rewriting prompt")
    has_refs = any(staged.values())
    guide = prompt_guide(settings, "ref-en.txt" if has_refs else "base-en.txt")
    audio_notes = _audio_notes(staged, use_video_audio=params.use_video_audio)
    spec = model_registry.resolve("chat", settings.enhance_model)
    ctx.ensure_model_ready(spec)
    req = ChatRequest(
        model=settings.enhance_model,
        temperature=0.3,
        max_completion_tokens=settings.enhance_max_tokens,
        messages=build_rewrite_messages(
            guide.read_text(),
            prompt=params.prompt,
            images=[
                _image_data_url(Path(p), work_dir, f"preview_image_{i}")
                for i, p in enumerate(staged["images"])
            ],
            video_frames=[
                _video_frame_urls(
                    Path(p), work_dir, f"preview_video_{i}", params.num_frames
                )
                for i, p in enumerate(staged["videos"])
            ],
            audio_notes=audio_notes,
            seconds=params.num_frames / FPS,
            width=params.width,
            height=params.height,
        ),
    )
    completion, _ = handle_chat(ctx, req)
    text = clean_rewrite(completion["choices"][0]["message"]["content"] or "")
    counts = {
        "Picture": len(staged["images"]),
        "Video": len(staged["videos"]),
        "Audio": len(audio_notes),
    }
    if not is_structured(text) or not labels_within(text, counts):
        return params.prompt
    return text


def labels_within(text: str, counts: dict[str, int]) -> bool:
    return all(1 <= int(n) <= counts[kind] for kind, n in LABEL.findall(text))


def build_rewrite_messages(
    guide: str,
    *,
    prompt: str,
    images: list[str],
    video_frames: list[list[str]],
    audio_notes: list[str],
    seconds: float,
    width: int,
    height: int,
) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []
    for i, url in enumerate(images, 1):
        content.append({"type": "text", "text": f"<Picture {i}>:"})
        content.append({"type": "image_url", "image_url": {"url": url}})
    for i, frames in enumerate(video_frames, 1):
        content.append(
            {
                "type": "text",
                "text": f"<Video {i}> (frames sampled in order; not separate pictures):",
            }
        )
        content.extend(
            {"type": "image_url", "image_url": {"url": url}} for url in frames
        )
    for note in audio_notes:
        content.append({"type": "text", "text": note})
    mode = "full-reference six-section" if (images or video_frames) else "text-to-video"
    labels = [f"<Picture {i}>" for i in range(1, len(images) + 1)]
    labels += [f"<Video {i}>" for i in range(1, len(video_frames) + 1)]
    labels += [f"<Audio {i}>" for i in range(1, len(audio_notes) + 1)]
    allowed = ", ".join(labels) if labels else "none"
    content.append(
        {
            "type": "text",
            "text": (
                f"Target video: {seconds:.1f} seconds, {width}x{height}.\n"
                f"User request:\n{prompt}\n\n"
                f"Reference labels that exist: {allowed}. Use no other <Picture N>, "
                "<Video N> or <Audio N> labels; <Subject N> labels are yours to define.\n"
                f"Rewrite this into the {mode} format of the guide. Keep dialogue, "
                "lyrics and on-screen text in their original language. Output only "
                "the prompt, nothing else."
            ),
        }
    )
    return [
        {
            "role": "system",
            "content": (
                "You write prompts for the MiniMax H3 video model. "
                "Follow this guide exactly.\n\n" + guide
            ),
        },
        {"role": "user", "content": content},
    ]


def clean_rewrite(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    fenced = re.fullmatch(r"```[a-z]*\n(.*)\n```", text, flags=re.DOTALL)
    return (fenced.group(1) if fenced else text).strip()


def _audio_notes(staged: dict[str, list[str]], *, use_video_audio: bool) -> list[str]:
    notes: list[str] = []
    if use_video_audio:
        for i, path in enumerate(staged["videos"], 1):
            if has_audio(Path(path)):
                notes.append(
                    f"<Audio {len(notes) + 1}>: the soundtrack of <Video {i}> "
                    f"({_duration(Path(path)):.1f} s)."
                )
    for path in staged["audios"]:
        notes.append(
            f"<Audio {len(notes) + 1}>: a standalone audio clip "
            f"({min(_duration(Path(path)), 15.0):.1f} s). You cannot hear it; take its "
            "role (voice timbre, music, sound) from the user request."
        )
    return notes


def _image_data_url(src: Path, work_dir: Path, name: str) -> str:
    dst = work_dir / f"{name}.jpg"
    _ffmpeg(
        "-i",
        str(src),
        "-frames:v",
        "1",
        "-vf",
        f"scale='min({PREVIEW_WIDTH},iw)':-2",
        str(dst),
    )
    return _data_url(dst)


def _video_frame_urls(
    src: Path, work_dir: Path, name: str, num_frames: int
) -> list[str]:
    span = min(_duration(src), num_frames / FPS)
    urls = []
    for i, point in enumerate(FRAME_POINTS):
        dst = work_dir / f"{name}_{i}.jpg"
        _ffmpeg(
            "-ss", f"{span * point:.3f}", "-i", str(src), "-frames:v", "1",
            "-vf", f"scale='min({PREVIEW_WIDTH},iw)':-2", str(dst),
        )  # fmt: skip
        urls.append(_data_url(dst))
    return urls


def _duration(src: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(src),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def _ffmpeg(*args: str) -> None:
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", *args], check=True, capture_output=True
    )


def _data_url(path: Path) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()
