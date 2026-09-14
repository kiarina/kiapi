"""Resident SearXNG backend, launched as a foreground Docker subprocess."""

import httpx

from kiapi.core.model import ModelSpec

from .._operations.resolve_searxng_config_dir import resolve_searxng_config_dir
from .._services.web_backend_process import WebBackendProcess
from .._settings import settings_manager

FEATURES = {"search"}


def load(spec: ModelSpec) -> WebBackendProcess:
    settings = settings_manager.get_settings()
    searxng_dir = resolve_searxng_config_dir()
    return WebBackendProcess.start(
        name="searxng",
        image=spec.repo,
        container_port=8080,
        log_dir=settings.backend_log_dir,
        ready_timeout_s=settings.backend_ready_timeout_s,
        healthcheck=_healthcheck,
        extra_args=[
            "-v",
            f"{searxng_dir}:/etc/searxng:rw",
            "-e",
            "SEARXNG_BASE_URL=http://localhost/",
        ],
    )


def release(payload: WebBackendProcess) -> None:
    payload.release()


def _healthcheck(base_url: str) -> None:
    resp = httpx.get(
        f"{base_url.rstrip('/')}/search",
        params={"q": "kiapi", "format": "json"},
        timeout=5.0,
    )
    resp.raise_for_status()
    resp.json()
