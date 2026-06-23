"""Shared helper: parse OpenAI-style multimodal ``messages`` into the Qwen
chat-template shape. Model handlers call this with the set of modalities they
support (``allow=``); anything outside that set is rejected with 400.

Recognised content parts (lenient — aliases accepted):

  text   : {"type": "text", "text": "..."}
  image  : {"type": "image_url",  "image_url": {"url": "data:image/...;base64,..." | "http..." }}
           aliases: {"type": "image", "image": <url|data|path>}, {"type": "input_image", ...}
  audio  : {"type": "input_audio", "input_audio": {"data": "<base64>", "format": "wav"}}
           aliases: {"type": "audio", "audio": <url|data|path>}, {"type": "audio_url", ...}
  video  : {"type": "video_url",  "video_url": {"url": "data:video/...;base64,..." | "http..." }}
           aliases: {"type": "video", "video": <url|data|path>}, {"type": "input_video", ...}

Each media source (data URL, http(s) URL, or bare base64) is materialized to a
file under ``tmp_dir``. Server-side local paths are intentionally not accepted,
so a chat message cannot read arbitrary files off the host. The function returns:

  - ``template_messages``: same conversation, but every media part rewritten to
    the Qwen-native form ({"type": "image"/"audio"/"video", <key>: <path>}) so the
    processor's chat_template inserts placeholders in document order.
  - ``images`` / ``audios`` / ``videos``: ordered lists of file paths, collected in
    the SAME walk order, to hand to ``generate(image=, audio=, video=)``.
"""

import base64
import binascii
import json
import re
import subprocess
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from kiapi.core.net import UnsafeURLError, verify_public_url

_DATA_URL = re.compile(r"^data:(?P<mime>[\w./+-]+)?;base64,(?P<data>.*)$", re.DOTALL)

_EXT_BY_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".m4a",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}
_DEFAULT_EXT = {"image": ".png", "audio": ".wav", "video": ".mp4"}


class MediaError(ValueError):
    """Bad/undecodable media in a message; mapped to HTTP 400 by the API layer."""


class CapabilityError(MediaError):
    """A modality the selected model does not support; mapped to HTTP 400."""


def parse_messages(
    messages: list[dict[str, Any]],
    tmp_dir: Path,
    *,
    allow: set[str] | None = None,
    use_audio_in_video: bool = True,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str]]:
    """Parse messages into (template_messages, images, audios, videos).

    ``allow`` is the set of modalities the selected model supports
    (e.g. ``{"text", "image"}``). A part outside it raises :class:`CapabilityError`.
    ``None`` allows everything (used by tests).
    """
    template_messages: list[dict[str, Any]] = []
    images: list[str] = []
    audios: list[str] = []
    videos: list[str] = []

    def _check(kind: str) -> None:
        if allow is not None and kind not in allow:
            raise CapabilityError(
                f"{kind} input is not supported by the selected model"
            )

    for raw_msg in messages:
        msg = _normalize_tool_calls_for_template(raw_msg)
        role = msg.get("role", "user")
        content = msg.get("content")

        if content is None or isinstance(content, str):
            # Pass plain text / tool fields (tool_calls, tool_call_id, name) through.
            template_messages.append(dict(msg))
            continue

        if not isinstance(content, list):
            raise MediaError(f"message.content must be a string or list (role={role})")

        new_content: list[dict[str, Any]] = []
        for part in content:
            if not isinstance(part, dict):
                raise MediaError("each content part must be an object")
            kind, source = _extract_part(part)

            if kind == "text":
                new_content.append({"type": "text", "text": source or ""})
                continue

            _check(kind)

            fmt = None
            if isinstance(source, tuple):  # (data, format) from input_audio/input_video
                source, fmt = source
            path = _materialize(source, kind, tmp_dir, fmt=fmt)

            if kind == "image":
                images.append(path)
                new_content.append({"type": "image", "image": path})
            elif kind == "audio":
                audios.append(path)
                new_content.append({"type": "audio", "audio": path})
            else:  # video
                videos.append(path)
                new_content.append({"type": "video", "video": path})
                # A video that carries sound: demux its audio track and feed it as
                # an audio input too (placeholder right after the video), so the
                # model hears the clip, not just sees it.
                if use_audio_in_video and (allow is None or "audio" in allow):
                    apath = _extract_audio(path, tmp_dir)
                    if apath is not None:
                        audios.append(apath)
                        new_content.append({"type": "audio", "audio": apath})

        out = dict(msg)
        out["content"] = new_content
        template_messages.append(out)

    return template_messages, images, audios, videos


def _template_tool_arguments(arguments: Any) -> dict[str, Any]:
    """Convert OpenAI's JSON-string tool args to the mapping Qwen templates expect."""
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            return {"_raw": arguments}
        if isinstance(parsed, dict):
            return parsed
        return {"value": parsed}
    if arguments is None:
        return {}
    return {"value": arguments}


def _normalize_tool_calls_for_template(msg: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of msg with tool-call history shaped for HF chat templates."""
    out = dict(msg)
    calls = out.get("tool_calls")
    if not isinstance(calls, list):
        return out

    if out.get("content") is None:
        out["content"] = ""

    normalized = []
    for call in calls:
        if not isinstance(call, dict):
            normalized.append(call)
            continue
        ncall = dict(call)
        fn = ncall.get("function")
        if isinstance(fn, dict):
            nfn = dict(fn)
            if "arguments" in nfn:
                nfn["arguments"] = _template_tool_arguments(nfn["arguments"])
            ncall["function"] = nfn
        elif "arguments" in ncall:
            ncall["arguments"] = _template_tool_arguments(ncall["arguments"])
        normalized.append(ncall)

    out["tool_calls"] = normalized
    return out


def _write_bytes(data: bytes, tmp_dir: Path, kind: str, ext: str) -> str:
    path = tmp_dir / f"{kind}_{uuid.uuid4().hex}{ext}"
    path.write_bytes(data)
    return str(path)


def _materialize(
    source: str, kind: str, tmp_dir: Path, *, fmt: str | None = None
) -> str:
    """Turn a data URL / http(s) URL / bare base64 into a local file path."""
    if not isinstance(source, str) or not source:
        raise MediaError(f"{kind}: empty or non-string source")

    m = _DATA_URL.match(source)
    if m:
        mime = m.group("mime") or ""
        ext = _EXT_BY_MIME.get(mime, _DEFAULT_EXT[kind])
        try:
            return _write_bytes(base64.b64decode(m.group("data")), tmp_dir, kind, ext)
        except (binascii.Error, ValueError) as exc:
            raise MediaError(f"{kind}: invalid base64 data URL ({exc})")  # noqa: B904

    if source.startswith(("http://", "https://")):
        try:
            verify_public_url(source, kind=kind)
        except UnsafeURLError as exc:
            raise MediaError(f"{kind}: {exc}")  # noqa: B904
        try:
            with urllib.request.urlopen(source, timeout=30) as resp:
                data = resp.read()
        except Exception as exc:
            raise MediaError(f"{kind}: failed to fetch {source!r} ({exc})")  # noqa: B904
        ext = Path(source.split("?")[0]).suffix or _DEFAULT_EXT[kind]
        return _write_bytes(data, tmp_dir, kind, ext)

    # Bare base64 (e.g. input_audio.data without a data: prefix). Server-side
    # local paths are intentionally NOT accepted: a chat message must not be able
    # to read arbitrary files off the host.
    try:
        data = base64.b64decode(source, validate=True)
    except (binascii.Error, ValueError):
        raise MediaError(f"{kind}: source is not a data URL, URL, or base64")  # noqa: B904
    ext = (
        _EXT_BY_MIME.get(f"{kind}/{fmt}", _DEFAULT_EXT[kind])
        if fmt
        else _DEFAULT_EXT[kind]
    )
    return _write_bytes(data, tmp_dir, kind, ext)


def _extract_part(part: dict[str, Any]) -> tuple[str, Any]:
    """Return (kind, source) for one content part. kind ∈ text|image|audio|video."""
    t = part.get("type")

    if t == "text":
        return "text", part.get("text", "")

    if (
        t in ("image_url", "image", "input_image")
        or "image_url" in part
        or "image" in part
    ):
        if "image_url" in part:
            iu = part["image_url"]
            return "image", iu.get("url") if isinstance(iu, dict) else iu
        return "image", part.get("image") or part.get("input_image")

    if (
        t in ("input_audio", "audio", "audio_url")
        or "input_audio" in part
        or "audio_url" in part
    ):
        if "input_audio" in part:
            ia = part["input_audio"]
            if isinstance(ia, dict):
                return "audio", (ia.get("data"), ia.get("format"))
            return "audio", ia
        if "audio_url" in part:
            au = part["audio_url"]
            return "audio", au.get("url") if isinstance(au, dict) else au
        return "audio", part.get("audio")

    if (
        t in ("video_url", "video", "input_video")
        or "video_url" in part
        or "video" in part
    ):
        if "video_url" in part:
            vu = part["video_url"]
            return "video", vu.get("url") if isinstance(vu, dict) else vu
        if "input_video" in part:
            iv = part["input_video"]
            if isinstance(iv, dict):
                return "video", (iv.get("data"), iv.get("format"))
            return "video", iv
        return "video", part.get("video")

    raise MediaError(f"unsupported content part type: {t!r}")


def _extract_audio(video_path: str, tmp_dir: Path) -> str | None:
    """Demux a video's audio track to mono 16 kHz wav. None if it has no audio."""
    wav = tmp_dir / f"audio_{uuid.uuid4().hex}.wav"
    try:
        # If the video has no audio stream, ffmpeg will fail/exit with an error,
        # and either not create the file or leave it empty.
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                video_path,
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                str(wav),
            ],
            capture_output=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if wav.exists() and wav.stat().st_size > 0:
        return str(wav)

    if wav.exists():
        wav.unlink(missing_ok=True)
    return None
