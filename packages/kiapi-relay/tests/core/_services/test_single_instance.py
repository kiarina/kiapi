from pathlib import Path

import pytest

from kiapi_relay import AlreadyRunningError, SingleInstanceLock


def test_second_acquire_raises(tmp_path: Path) -> None:
    first = SingleInstanceLock(tmp_path, name="kiapi")
    first.acquire()
    try:
        second = SingleInstanceLock(tmp_path, name="kiapi")
        with pytest.raises(AlreadyRunningError):
            second.acquire(timeout=0.1)
    finally:
        first.release()


def test_acquire_after_release(tmp_path: Path) -> None:
    lock = SingleInstanceLock(tmp_path, name="kiapi")
    lock.acquire()
    lock.release()

    again = SingleInstanceLock(tmp_path, name="kiapi")
    again.acquire(timeout=0.1)
    again.release()


def test_different_data_dirs_do_not_conflict(tmp_path: Path) -> None:
    a = SingleInstanceLock(tmp_path / "a", name="kiapi")
    b = SingleInstanceLock(tmp_path / "b", name="kiapi")

    a.acquire()
    b.acquire(timeout=0.1)
    a.release()
    b.release()
