from pathlib import Path

import pytest

from kiapi.core.file import FileSettings, FileStore


@pytest.fixture
def file_store(tmp_path: Path) -> FileStore:
    settings = FileSettings(files_root=str(tmp_path))
    return FileStore(settings)


def test_put_bytes_returns_record_and_writes_blob(file_store: FileStore) -> None:
    rec = file_store.put_bytes(b"hello", filename="greeting.txt")

    assert rec.file_id.startswith("file_")
    assert rec.filename == "greeting.txt"
    assert rec.content_type == "text/plain"
    assert rec.size == 5
    assert rec.meta == {}

    blob = Path(rec.path)
    assert blob.exists()
    assert blob.read_bytes() == b"hello"
    assert blob.suffix == ".txt"


def test_put_bytes_explicit_content_type_and_meta(file_store: FileStore) -> None:
    rec = file_store.put_bytes(
        b"\x89PNG",
        filename="img.bin",
        content_type="image/png",
        meta={"source": "test"},
    )

    assert rec.content_type == "image/png"
    assert rec.meta == {"source": "test"}


def test_put_bytes_unknown_extension_falls_back_to_octet_stream(
    file_store: FileStore,
) -> None:
    rec = file_store.put_bytes(b"data", filename="blob.unknownext")

    assert rec.content_type == "application/octet-stream"


def test_put_path_copies_by_default(file_store: FileStore, tmp_path: Path) -> None:
    src = tmp_path / "src.txt"
    src.write_bytes(b"payload")

    rec = file_store.put_path(src)

    assert rec.filename == "src.txt"
    assert rec.size == len(b"payload")
    assert Path(rec.path).read_bytes() == b"payload"
    # copy leaves the source in place
    assert src.exists()


def test_put_path_move_removes_source(file_store: FileStore, tmp_path: Path) -> None:
    src = tmp_path / "moveme.dat"
    src.write_bytes(b"abc")

    rec = file_store.put_path(src, move=True)

    assert Path(rec.path).read_bytes() == b"abc"
    assert not src.exists()


def test_put_path_filename_override(file_store: FileStore, tmp_path: Path) -> None:
    src = tmp_path / "ugly_name.txt"
    src.write_bytes(b"x")

    rec = file_store.put_path(src, filename="nice.txt")

    assert rec.filename == "nice.txt"


def test_get_returns_none_for_unknown_id(file_store: FileStore) -> None:
    assert file_store.get("file_does_not_exist") is None


def test_get_roundtrips_metadata(file_store: FileStore) -> None:
    rec = file_store.put_bytes(b"hi", filename="a.txt", meta={"k": "v"})

    got = file_store.get(rec.file_id)

    assert got is not None
    assert got.file_id == rec.file_id
    assert got.filename == "a.txt"
    assert got.content_type == "text/plain"
    assert got.size == 2
    assert got.meta == {"k": "v"}
    assert Path(got.path).read_bytes() == b"hi"


def test_get_survives_new_store_instance(tmp_path: Path) -> None:
    settings = FileSettings(files_root=str(tmp_path))
    rec = FileStore(settings).put_bytes(b"persisted", filename="p.txt")

    # a fresh instance reads the same on-disk sidecar
    got = FileStore(settings).get(rec.file_id)

    assert got is not None
    assert Path(got.path).read_bytes() == b"persisted"


def test_list_is_sorted_newest_first(file_store: FileStore) -> None:
    first = file_store.put_bytes(b"1", filename="first.txt")
    second = file_store.put_bytes(b"2", filename="second.txt")
    third = file_store.put_bytes(b"3", filename="third.txt")

    recs = file_store.list()

    assert [r.file_id for r in recs] == [
        third.file_id,
        second.file_id,
        first.file_id,
    ]


def test_list_empty(file_store: FileStore) -> None:
    assert file_store.list() == []


def test_delete_removes_blob_and_sidecar(file_store: FileStore) -> None:
    rec = file_store.put_bytes(b"bye", filename="d.txt")

    assert file_store.delete(rec.file_id) is True
    assert file_store.get(rec.file_id) is None
    assert not Path(rec.path).exists()


def test_delete_unknown_returns_false(file_store: FileStore) -> None:
    assert file_store.delete("file_missing") is False
