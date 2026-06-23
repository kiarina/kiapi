"""Unified file store. Artifacts (and uploads) are addressed by ``file_id``.

Files outlive jobs while their files remain on disk: jobs are in-memory and reset
on process restart, while stored files stay self-describing via a sidecar
``<file_id>.json`` holding the original filename, content type, size, and an
optional ``meta`` blob. This
mirrors the per-server Files APIs (ace-step / audiocraft / video) unified into
one store under ``files_root``.
"""

import json
import mimetypes
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from .._schemas.file_record import FileRecord
from .._settings import FileSettings
from .._types.file_id import FileID


class FileStore:
    def __init__(self, settings: FileSettings) -> None:
        self.root = Path(settings.files_root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)

    def _blob_path(self, file_id: FileID, suffix: str) -> Path:
        return self.root / f"{file_id}{suffix}"

    def _sidecar(self, file_id: FileID) -> Path:
        return self.root / f"{file_id}.json"

    # -- write ----------------------------------------------------------------

    def put_bytes(
        self,
        data: bytes,
        *,
        filename: str,
        content_type: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> FileRecord:
        file_id = _generate_file_id()
        suffix = Path(filename).suffix
        path = self._blob_path(file_id, suffix)
        path.write_bytes(data)
        rec = FileRecord(
            file_id=file_id,
            filename=filename,
            content_type=_resolve_content_type(filename, content_type),
            size=len(data),
            created_at=time.time(),
            meta=meta or {},
            path=str(path),
        )
        self._write_sidecar(rec, suffix)
        return rec

    def put_path(
        self,
        src: str | Path,
        *,
        filename: str | None = None,
        content_type: str | None = None,
        meta: dict[str, Any] | None = None,
        move: bool = False,
    ) -> FileRecord:
        src = Path(src)
        file_id = _generate_file_id()
        suffix = src.suffix
        filename = filename or src.name
        path = self._blob_path(file_id, suffix)
        if move:
            shutil.move(str(src), str(path))
        else:
            shutil.copyfile(src, path)
        rec = FileRecord(
            file_id=file_id,
            filename=filename,
            content_type=_resolve_content_type(filename, content_type),
            size=path.stat().st_size,
            created_at=time.time(),
            meta=meta or {},
            path=str(path),
        )
        self._write_sidecar(rec, suffix)
        return rec

    def _write_sidecar(self, rec: FileRecord, suffix: str) -> None:
        payload = rec.model_dump()
        payload["_suffix"] = suffix
        self._sidecar(rec.file_id).write_text(json.dumps(payload, ensure_ascii=False))

    # -- read -----------------------------------------------------------------

    def get(self, file_id: FileID) -> FileRecord | None:
        sidecar = self._sidecar(file_id)
        if not sidecar.exists():
            return None
        d = json.loads(sidecar.read_text())
        suffix = d.get("_suffix", "")
        return FileRecord(
            file_id=d["file_id"],
            filename=d["filename"],
            content_type=d["content_type"],
            size=d["size"],
            created_at=d["created_at"],
            meta=d.get("meta", {}),
            path=str(self._blob_path(file_id, suffix)),
        )

    def list(self) -> list[FileRecord]:
        recs = []
        for sidecar in self.root.glob("*.json"):
            rec = self.get(sidecar.stem)
            if rec is not None:
                recs.append(rec)
        return sorted(recs, key=lambda r: r.created_at, reverse=True)

    def delete(self, file_id: FileID) -> bool:
        rec = self.get(file_id)
        if rec is None:
            return False
        Path(rec.path).unlink(missing_ok=True)
        self._sidecar(file_id).unlink(missing_ok=True)
        return True


def _generate_file_id() -> FileID:
    return f"file_{uuid.uuid4().hex}"


def _resolve_content_type(filename: str, content_type: str | None) -> str:
    return (
        content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    )
