"""Start mlx-serve for one job, stream one video generation, and stop it."""

import json
import socket
import subprocess
import tarfile
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx

from .._helpers.mlx_serve_paths import mlx_serve_archive, mlx_serve_binary
from .._settings import H3Settings

# mlx-serve waits up to 30 s for open connections before it exits.
STOP_TIMEOUT_S = 60.0


def ensure_mlx_serve_binary(settings: H3Settings) -> Path:
    binary = mlx_serve_binary(settings)
    if not binary.exists():
        with tarfile.open(mlx_serve_archive(settings)) as archive:
            archive.extractall(binary.parent.parent, filter="tar")
    return binary


@contextmanager
def mlx_serve(settings: H3Settings, *, model_dir: str, log_path: Path) -> Iterator[str]:
    """Run mlx-serve on a free loopback port and yield its base URL."""
    binary = ensure_mlx_serve_binary(settings)
    port = _free_port()
    with log_path.open("wb") as log:
        proc = subprocess.Popen(
            [
                str(binary),
                "--model",
                model_dir,
                "--serve",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        base_url = f"http://127.0.0.1:{port}"
        try:
            _wait_ready(proc, base_url, settings.startup_timeout_s, log_path)
            yield base_url
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=STOP_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


def generate_video(
    base_url: str,
    body: dict[str, Any],
    *,
    on_progress: Callable[[str, int, int], None],
) -> dict[str, Any]:
    """POST a streaming video request and return the ``complete`` event."""
    with (
        httpx.Client(timeout=httpx.Timeout(None, connect=10.0)) as client,
        client.stream(
            "POST", f"{base_url}/v1/video/generations", json=body | {"stream": True}
        ) as res,
    ):
        if res.status_code != 200:
            raise RuntimeError(f"mlx-serve {res.status_code}: {res.read().decode()}")
        for line in res.iter_lines():
            if not line.startswith("data: "):
                continue
            event: dict[str, Any] = json.loads(line.removeprefix("data: "))
            kind = event.get("type")
            if kind == "progress":
                on_progress(
                    str(event.get("stage", "")),
                    int(event.get("step", 0)),
                    int(event.get("total", 0)),
                )
            elif kind == "complete":
                return event
            elif kind == "error":
                raise RuntimeError(f"mlx-serve: {event.get('message')}")
    raise RuntimeError("mlx-serve closed the stream without a result")


def _wait_ready(
    proc: subprocess.Popen[bytes], base_url: str, timeout_s: float, log_path: Path
) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            tail = log_path.read_text(errors="replace")[-2000:]
            raise RuntimeError(f"mlx-serve exited with {proc.returncode}: {tail}")
        try:
            if httpx.get(f"{base_url}/health", timeout=2.0).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1.0)
    raise RuntimeError(f"mlx-serve did not become ready in {timeout_s:.0f}s")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
