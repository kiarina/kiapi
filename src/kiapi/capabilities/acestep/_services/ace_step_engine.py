"""kiapi-side proxy for the ace-step worker subprocess.

An :class:`AceStepEngine` owns one long-lived subprocess (launched from the
ace-step venv) holding the LLM + one preset's DiT resident. It is the ``payload``
the memory manager keeps for an ace-step spec; ``release()`` (called on eviction /
TTL / shutdown) terminates the subprocess and frees its memory.

Only ever used from the single worker thread (single-flight), so the simple
request/response over pipes needs no concurrency beyond a guard lock.
"""

import json
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path

from .._exceptions.ace_step_engine_error import AceStepEngineError

SENTINEL = "@@KIAPI@@"
_WORKER = str(Path(__file__).parents[1] / "worker_subprocess.py")


class AceStepEngine:
    def __init__(self, proc: subprocess.Popen) -> None:
        self.proc = proc
        self._lock = threading.Lock()
        self._counter = 0

    # -- lifecycle ------------------------------------------------------------

    @classmethod
    def spawn(
        cls,
        *,
        python_path: str,
        preset_name: str,
        project_root: str,
        checkpoint_dir: str,
        llm_model: str,
        ready_timeout_s: float,
    ) -> "AceStepEngine":
        proc = subprocess.Popen(
            [
                python_path,
                _WORKER,
                "--preset-name",
                preset_name,
                "--project-root",
                project_root,
                "--checkpoint-dir",
                checkpoint_dir,
                "--llm-model",
                llm_model,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,  # inherit: ace-step logs stream to kiapi's stderr
            text=True,
            bufsize=1,
        )
        engine = cls(proc)
        engine._await_event("ready", timeout_s=ready_timeout_s)
        return engine

    def release(self) -> None:
        proc = self.proc
        if proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
        for stream in (proc.stdin, proc.stdout):
            try:
                if stream is not None:
                    stream.close()
            except Exception:
                pass

    # -- protocol -------------------------------------------------------------

    def _read_proto(self, timeout_s: float | None = None) -> dict:
        """Read the next ``@@KIAPI@@`` protocol line, skipping any other noise."""
        deadline = (time.monotonic() + timeout_s) if timeout_s else None
        assert self.proc.stdout is not None
        for line in self.proc.stdout:  # blocks; ace-step noise on fd1 is skipped
            line = line.rstrip("\n")
            if line.startswith(SENTINEL):
                return json.loads(line[len(SENTINEL) :])  # type: ignore
            if deadline is not None and time.monotonic() > deadline:
                break
        if self.proc.poll() is not None:
            raise AceStepEngineError(
                f"ace-step worker exited (code {self.proc.returncode}) before replying"
            )
        raise AceStepEngineError("ace-step worker produced no protocol output")

    def _await_event(self, event: str, *, timeout_s: float) -> dict:
        msg = self._read_proto(timeout_s=timeout_s)
        if msg.get("event") == "error":
            raise AceStepEngineError(msg.get("error", "worker init error"))
        if msg.get("event") != event:
            raise AceStepEngineError(f"expected event {event!r}, got {msg!r}")
        return msg

    def generate(
        self,
        task: str,
        params: dict,
        save_dir: str,
        *,
        timeout_s: float,
        on_progress: Callable[[float, str | None], None] | None = None,
    ) -> str:
        with self._lock:
            self._counter += 1
            rid = str(self._counter)
            req = {"id": rid, "task": task, "params": params, "save_dir": save_dir}
            if self.proc.stdin is None or self.proc.poll() is not None:
                raise AceStepEngineError("ace-step worker is not running")
            self.proc.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()

            deadline = time.monotonic() + timeout_s
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AceStepEngineError("ace-step worker timed out")
                msg = self._read_proto(timeout_s=remaining)

                if msg.get("event") == "progress":
                    # Forward only our own progress; ignore any stray/stale line.
                    if on_progress is not None and msg.get("id") == rid:
                        on_progress(float(msg.get("fraction", 0.0)), msg.get("label"))
                    continue

                if msg.get("id") != rid:
                    raise AceStepEngineError(f"reply id mismatch: {msg!r}")
                if not msg.get("ok"):
                    raise AceStepEngineError(msg.get("error", "generation failed"))
                return msg["path"]  # type: ignore
