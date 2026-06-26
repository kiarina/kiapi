from pathlib import Path
from typing import Any

from pytest import MonkeyPatch

from kiapi.capabilities.web._services import web_backend_process as subject


class DummyProc:
    def __init__(self, cmd: list[str], **kwargs: Any) -> None:
        self.cmd = cmd
        self.kwargs = kwargs
        self.returncode: int | None = None
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = 0

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode or 0


def test_start_backend_runs_foreground_docker_with_dynamic_port(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    procs: list[DummyProc] = []

    def fake_popen(cmd: list[str], **kwargs: Any) -> DummyProc:
        proc = DummyProc(cmd, **kwargs)
        procs.append(proc)
        return proc

    monkeypatch.setattr(subject, "_pick_free_port", lambda: 45678)
    monkeypatch.setattr(subject.subprocess, "Popen", fake_popen)

    backend = subject.WebBackendProcess.start(
        name="search",
        image="searxng/searxng:latest",
        container_port=8080,
        log_dir=str(tmp_path),
        ready_timeout_s=1.0,
        healthcheck=lambda base_url: None,
        extra_args=["-v", "/host:/container:rw"],
    )

    assert backend.base_url == "http://127.0.0.1:45678"
    assert procs[0].cmd[:6] == [
        "docker",
        "run",
        "--rm",
        "--name",
        procs[0].cmd[4],
        "-p",
    ]
    assert procs[0].cmd[6] == "127.0.0.1:45678:8080"
    assert procs[0].cmd[-1] == "searxng/searxng:latest"
    assert procs[0].kwargs["stderr"] == subject.subprocess.STDOUT
    assert procs[0].kwargs["start_new_session"] is True

    backend.release()
    assert procs[0].terminated is True
