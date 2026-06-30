from pathlib import Path

from filelock import FileLock, Timeout

_LOCK_FILE = "instance.lock"


class AlreadyRunningError(RuntimeError):
    """Raised when another instance already holds the single-instance lock."""


class SingleInstanceLock:
    """Filesystem lock that prevents a second process from starting.

    The lock is scoped to ``data_dir`` (which maps one-to-one to a node ID), so
    instances that use different data directories may run side by side. The OS
    releases the lock automatically if the holding process dies, so a crashed
    instance never leaves a stale lock behind.
    """

    def __init__(self, data_dir: str | Path, *, name: str = "kiapi") -> None:
        directory = Path(data_dir)
        directory.mkdir(parents=True, exist_ok=True)
        self._name = name
        self._path = directory / _LOCK_FILE
        self._lock = FileLock(str(self._path))

    def acquire(self, *, timeout: float = 10.0) -> None:
        try:
            self._lock.acquire(timeout=timeout)
        except Timeout as exc:
            raise AlreadyRunningError(
                f"another {self._name} instance is already running (lock: {self._path})"
            ) from exc

    def release(self) -> None:
        self._lock.release()
