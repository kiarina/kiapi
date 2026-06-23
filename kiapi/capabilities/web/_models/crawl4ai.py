"""Resident Crawl4AI backend, launched as a foreground Docker subprocess."""

import httpx

from kiapi.core.model import ModelSpec

from .._services.web_backend_process import WebBackendProcess
from .._settings import settings_manager

FEATURES = {"fetch"}


def load(spec: ModelSpec) -> WebBackendProcess:
    settings = settings_manager.get_settings()
    return WebBackendProcess.start(
        name="crawl4ai",
        image=spec.repo,
        container_port=11235,
        log_dir=settings.backend_log_dir,
        ready_timeout_s=settings.backend_ready_timeout_s,
        healthcheck=_healthcheck,
        extra_args=["--shm-size", "1g"],
    )


def release(payload: WebBackendProcess) -> None:
    payload.release()


def _healthcheck(base_url: str) -> None:
    resp = httpx.get(f"{base_url.rstrip('/')}/health", timeout=5.0)
    resp.raise_for_status()
