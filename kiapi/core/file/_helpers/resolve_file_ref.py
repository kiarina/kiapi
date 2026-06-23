import base64
import binascii
import mimetypes
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from kiapi.core.net import UnsafeURLError, verify_public_url

from .._schemas.file_data_url_ref import FileDataURLRef
from .._schemas.file_id_ref import FileIDRef
from .._schemas.file_record import FileRecord
from .._schemas.file_url_ref import FileURLRef
from .._services.file_store import FileStore
from .._types.file_ref import FileRef
from .._views.resolved_file_ref import ResolvedFileRef


def resolve_file_ref(
    file_store: FileStore,
    ref: FileRef,
    *,
    kind: str,
) -> ResolvedFileRef:
    if isinstance(ref, FileIDRef):
        rec = file_store.get(ref.file_id)
        if rec is None:
            raise FileNotFoundError(f"unknown {kind} file_id {ref.file_id!r}")
        return ResolvedFileRef(rec)

    if isinstance(ref, FileURLRef):
        return ResolvedFileRef(_store_url(file_store, ref, kind=kind))

    if isinstance(ref, FileDataURLRef):
        return ResolvedFileRef(_store_data_url(file_store, ref, kind=kind))


def _store_url(file_store: FileStore, ref: FileURLRef, *, kind: str) -> FileRecord:
    parsed = urllib.parse.urlparse(ref.url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"{kind} url must be an absolute http:// or https:// URL")

    try:
        verify_public_url(ref.url, kind=kind)
    except UnsafeURLError as exc:
        raise ValueError(str(exc)) from exc

    try:
        with urllib.request.urlopen(ref.url, timeout=30) as response:
            data = response.read()
            content_type = response.headers.get_content_type()
    except urllib.error.URLError as exc:
        raise ValueError(f"failed to fetch {kind} url {ref.url!r}: {exc}") from exc

    filename = (
        Path(parsed.path).name or f"{kind}{_suffix_for_content_type(content_type)}"
    )
    return file_store.put_bytes(
        data,
        filename=filename,
        content_type=content_type,
        meta={"source": "url", "url": ref.url, "kind": kind},
    )


def _store_data_url(
    file_store: FileStore, ref: FileDataURLRef, *, kind: str
) -> FileRecord:
    header, sep, raw = ref.data_url.partition(",")
    if sep != "," or not header.startswith("data:"):
        raise ValueError(f"{kind} data_url must be a data URL")

    media_type = header[5:].split(";", 1)[0] or "application/octet-stream"
    is_base64 = ";base64" in header
    try:
        data = base64.b64decode(raw, validate=True) if is_base64 else raw.encode()
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"invalid {kind} data_url payload: {exc}") from exc

    return file_store.put_bytes(
        data,
        filename=f"{kind}{_suffix_for_content_type(media_type)}",
        content_type=media_type,
        meta={"source": "data_url", "kind": kind},
    )


def _suffix_for_content_type(content_type: str | None) -> str:
    return mimetypes.guess_extension(content_type or "") or ".bin"
