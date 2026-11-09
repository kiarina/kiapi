"""Resident Crawl4AI backend, launched as a foreground Docker subprocess.

Crawl4AI images from 2026-10 on bind only the container's loopback unless
``CRAWL4AI_API_TOKEN`` is set, and then require ``Authorization: Bearer`` on
every route except ``/health``. kiapi generates a fresh token per start, so it
never needs to be configured or stored.
"""

import secrets

import httpx

from kiapi.core.model import ModelSpec

from .._services.web_backend_process import WebBackendProcess
from .._settings import settings_manager

FEATURES = {"fetch"}


def load(spec: ModelSpec) -> WebBackendProcess:
    settings = settings_manager.get_settings()
    token = secrets.token_urlsafe(32)
    return WebBackendProcess.start(
        name="crawl4ai",
        image=spec.repo,
        container_port=11235,
        log_dir=settings.backend_log_dir,
        ready_timeout_s=settings.backend_ready_timeout_s,
        healthcheck=_healthcheck,
        extra_args=["--shm-size", "1g"],
        env={"CRAWL4AI_API_TOKEN": token},
        api_token=token,
    )


def release(payload: WebBackendProcess) -> None:
    payload.release()


def _healthcheck(base_url: str) -> None:
    resp = httpx.get(f"{base_url.rstrip('/')}/health", timeout=5.0)
    resp.raise_for_status()
