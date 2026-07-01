from collections.abc import Iterator
from pathlib import Path

import pytest
from kiarina.utils.app import configure, reset


@pytest.fixture(autouse=True)
def configure_app() -> None:
    # Match runtime: the CLI entry sets the application identity before any
    # user-directory lookup. Reset first so this is safe to run for every test
    # (`configure` raises if the identity is already set).
    reset()
    configure("kiapi-proxy", "kiarina")


@pytest.fixture(autouse=True)
def isolate_user_dirs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    """Keep the node ID file and single-instance lock out of the real user dirs.

    The proxy lifespan resolves a persistent node ID under the data dir and
    acquires the single-instance lock under the cache dir at startup. Point both
    XDG base directories at a temporary location so tests never touch (or
    contend on) the developer's real user directories.
    """
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg-cache"))
    yield
