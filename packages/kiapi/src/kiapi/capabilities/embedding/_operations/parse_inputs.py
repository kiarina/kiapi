"""Turn an embedding request's modality inputs into usable values.

The request carries one field per modality (``text``, ``image``, ...). Model
handlers call :func:`parse_inputs` with the set of modalities they support
(``allow=``); anything outside that set — or an empty request — is rejected with
:class:`~kiapi.capabilities.CapabilityError` (mapped to HTTP 400 by the API layer).

  - ``text``  is passed through as-is.
  - ``image`` accepts a data URL, an http(s) URL, or bare base64, and is
    materialized to a file under ``tmp_dir`` (the loader reads paths).

Returns a dict keyed by modality, e.g. ``{"text": "...", "image": "/tmp/..png"}``.
"""

import base64
import binascii
import re
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from kiapi.capabilities import CapabilityError
from kiapi.core.net import UnsafeURLError, verify_public_url

_DATA_URL = re.compile(r"^data:(?P<mime>[\w./+-]+)?;base64,(?P<data>.*)$", re.DOTALL)

_EXT_BY_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
_DEFAULT_EXT = {"image": ".png"}


def _write_bytes(data: bytes, tmp_dir: Path, kind: str, ext: str) -> str:
    path = tmp_dir / f"{kind}_{uuid.uuid4().hex}{ext}"
    path.write_bytes(data)
    return str(path)


def _materialize(source: str, kind: str, tmp_dir: Path) -> str:
    """Turn a data URL / http(s) URL / bare base64 into a file path."""
    if not isinstance(source, str) or not source:
        raise CapabilityError(f"{kind}: empty or non-string source")

    m = _DATA_URL.match(source)
    if m:
        mime = m.group("mime") or ""
        ext = _EXT_BY_MIME.get(mime, _DEFAULT_EXT[kind])
        try:
            return _write_bytes(base64.b64decode(m.group("data")), tmp_dir, kind, ext)
        except (binascii.Error, ValueError) as exc:
            raise CapabilityError(f"{kind}: invalid base64 data URL ({exc})")  # noqa: B904

    if source.startswith(("http://", "https://")):
        try:
            verify_public_url(source, kind=kind)
        except UnsafeURLError as exc:
            raise CapabilityError(f"{kind}: {exc}")  # noqa: B904
        try:
            with urllib.request.urlopen(source, timeout=30) as resp:
                data = resp.read()
        except Exception as exc:
            raise CapabilityError(f"{kind}: failed to fetch {source!r} ({exc})")  # noqa: B904
        ext = Path(source.split("?")[0]).suffix or _DEFAULT_EXT[kind]
        return _write_bytes(data, tmp_dir, kind, ext)

    # Bare base64 (no data: prefix) — the common case for {"image": "<b64>"}.
    try:
        data = base64.b64decode(source, validate=True)
    except (binascii.Error, ValueError):
        raise CapabilityError(f"{kind}: source is not a data URL, URL, or base64")  # noqa: B904
    return _write_bytes(data, tmp_dir, kind, _DEFAULT_EXT[kind])


def parse_inputs(
    inputs: dict[str, Any],
    tmp_dir: Path,
    *,
    allow: set[str] | None = None,
) -> dict[str, Any]:
    """Validate + materialize request inputs into a per-modality dict.

    ``allow`` is the set of modalities the selected model supports (e.g.
    ``{"text", "image"}``). An input outside it raises :class:`CapabilityError`.
    ``None`` allows everything (used by tests).
    """
    if not inputs:
        raise CapabilityError(
            "request has no input (provide at least one of: text, image)"
        )

    out: dict[str, Any] = {}
    for kind, source in inputs.items():
        if allow is not None and kind not in allow:
            raise CapabilityError(
                f"{kind} input is not supported by the selected model"
            )
        if kind == "text":
            out["text"] = source or ""
        elif kind == "image":
            out["image"] = _materialize(source, "image", tmp_dir)
        else:  # pragma: no cover — schema only exposes known modalities
            raise CapabilityError(f"unsupported input modality: {kind!r}")
    return out
