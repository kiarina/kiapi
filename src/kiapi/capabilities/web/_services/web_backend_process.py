"""Foreground subprocess wrapper for web backend containers.

The web capability treats SearXNG and Crawl4AI like resident subprocess models:
``load`` starts a foreground ``docker run --rm`` process on a free localhost port,
and ``release`` terminates that process. Docker is only an implementation detail
of this payload.
"""

import socket
import subprocess
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO, Self

import httpx


class WebBackendProcess:
    def __init__(
        self,
        *,
        name: str,
        proc: subprocess.Popen,
        base_url: str,
        port: int,
        log_file: BinaryIO,
        log_path: Path,
    ) -> None:
        self.name = name
        self.proc = proc
        self.base_url = base_url
        self.port = port
        self.log_file = log_file
        self.log_path = log_path
        self.started_at = time.time()

    def release(self) -> None:
        proc = self.proc
        if proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=15)
            except Exception:
                proc.kill()
                proc.wait(timeout=5)
        try:
            self.log_file.close()
        except Exception:
            pass

    @classmethod
    def start(
        cls,
        *,
        name: str,
        image: str,
        container_port: int,
        log_dir: str,
        ready_timeout_s: float,
        healthcheck: Callable[[str], None],
        extra_args: list[str] | None = None,
        attempts: int = 3,
    ) -> Self:
        last_error: Exception | None = None
        for _ in range(attempts):
            port = _pick_free_port()
            log_path = _log_path(log_dir, name, port)
            log_file = log_path.open("ab")
            container_name = f"kiapi-web-{name}-{uuid.uuid4().hex[:12]}"
            cmd = [
                "docker",
                "run",
                "--rm",
                "--name",
                container_name,
                "-p",
                f"127.0.0.1:{port}:{container_port}",
                *(extra_args or []),
                image,
            ]
            proc = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            backend = cls(
                name=name,
                proc=proc,
                base_url=f"http://127.0.0.1:{port}",
                port=port,
                log_file=log_file,
                log_path=log_path,
            )
            try:
                _wait_ready(backend, ready_timeout_s, healthcheck)
                return backend
            except Exception as exc:
                last_error = exc
                backend.release()

        assert last_error is not None
        raise last_error


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _log_path(log_dir: str, name: str, port: int) -> Path:
    path = Path(log_dir).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path / f"kiapi-web-{name}-{port}.log"


def _wait_ready(
    backend: WebBackendProcess,
    timeout_s: float,
    healthcheck: Callable[[str], None],
) -> None:
    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if backend.proc.poll() is not None:
            raise RuntimeError(
                f"{backend.name} backend exited early "
                f"(code {backend.proc.returncode}); log: {backend.log_path}"
            )
        try:
            healthcheck(backend.base_url)
            return
        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            last_error = exc
            time.sleep(0.5)

    detail = f": {last_error}" if last_error else ""
    raise RuntimeError(
        f"{backend.name} backend did not become ready within {timeout_s}s{detail}; "
        f"log: {backend.log_path}"
    )
