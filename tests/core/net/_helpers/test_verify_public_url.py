import socket
from collections.abc import Callable
from typing import Any

import pytest

from kiapi.core.net import UnsafeURLError, settings_manager, verify_public_url
from kiapi.core.net._helpers import verify_public_url as mod


def _fake_getaddrinfo(ip: str) -> Callable[..., list[tuple[Any, ...]]]:
    def _impl(
        host: str, port: int | None, *args: Any, **kwargs: Any
    ) -> list[tuple[Any, ...]]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port or 80))]

    return _impl


def test_rejects_non_http_scheme() -> None:
    with pytest.raises(UnsafeURLError):
        verify_public_url("ftp://example.com/x", kind="image")


def test_rejects_missing_host() -> None:
    with pytest.raises(UnsafeURLError):
        verify_public_url("http:///x")


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/x",
        "http://localhost/x",
        "http://10.0.0.5/x",
        "http://192.168.1.1/x",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/x",
    ],
)
def test_rejects_non_public_addresses(url: str) -> None:
    with pytest.raises(UnsafeURLError):
        verify_public_url(url, kind="image")


def test_allows_public_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod.socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34"))
    verify_public_url("https://example.com/x", kind="image")


def test_rejects_public_host_resolving_private(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mod.socket, "getaddrinfo", _fake_getaddrinfo("127.0.0.1"))
    with pytest.raises(UnsafeURLError):
        verify_public_url("https://evil.example.com/x")


def test_unresolvable_host(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: Any, **kwargs: Any) -> Any:
        raise socket.gaierror("nope")

    monkeypatch.setattr(mod.socket, "getaddrinfo", _boom)
    with pytest.raises(UnsafeURLError):
        verify_public_url("https://nonexistent.invalid/x")


def test_escape_hatch_allows_private() -> None:
    settings_manager.user_config = {"allow_private_urls": True}
    try:
        # With the guard disabled, a loopback URL passes without a DNS lookup.
        verify_public_url("http://127.0.0.1/x")
    finally:
        settings_manager.reset_user_config()
