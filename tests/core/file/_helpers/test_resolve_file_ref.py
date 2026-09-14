import base64
from pathlib import Path

import pytest

from kiapi.core.file import (
    FileDataURLRef,
    FileIDRef,
    FileSettings,
    FileStore,
    resolve_file_ref,
)


@pytest.fixture
def file_store(tmp_path: Path) -> FileStore:
    settings = FileSettings(files_root=str(tmp_path))
    return FileStore(settings)


def test_resolve_file_id_ref_returns_existing_record(file_store) -> None:  # type: ignore
    rec = file_store.put_bytes(b"hello", filename="hello.txt")

    resolved = resolve_file_ref(
        file_store, FileIDRef(file_id=rec.file_id), kind="source"
    )

    assert resolved.file_id == rec.file_id
    assert resolved.path == rec.path


def test_resolve_file_id_ref_rejects_missing(file_store) -> None:  # type: ignore
    with pytest.raises(FileNotFoundError):
        resolve_file_ref(file_store, FileIDRef(file_id="file_missing"), kind="source")


def test_resolve_data_url_ref_stores_file(file_store) -> None:  # type: ignore
    payload = base64.b64encode(b"hello").decode()
    ref = FileDataURLRef(data_url=f"data:text/plain;base64,{payload}")

    resolved = resolve_file_ref(file_store, ref, kind="source")

    rec = file_store.get(resolved.file_id)
    assert rec is not None
    assert rec.content_type == "text/plain"
    assert rec.size == 5
