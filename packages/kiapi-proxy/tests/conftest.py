from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_user_data_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    """Keep the node ID file and single-instance lock out of the real data dir.

    The proxy lifespan resolves a persistent node ID and acquires a per-data-dir
    lock at startup. Point XDG_DATA_HOME at a temporary directory so tests never
    touch (or contend on) the developer's real user data directory.
    """
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))
    yield
