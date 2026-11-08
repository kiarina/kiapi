import threading
import urllib.request
from collections.abc import Iterator
from email.message import Message
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO

import pytest

from kiapi.core.net import UnsafeURLError, open_public_url, settings_manager
from kiapi.core.net._helpers.open_public_url import _PublicRedirectHandler


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/target")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
def server_url() -> Iterator[str]:
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def test_rejects_private_url(server_url: str) -> None:
    with pytest.raises(UnsafeURLError):
        open_public_url(f"{server_url}/target", kind="image", timeout=5)


def test_redirect_to_private_address_is_rejected() -> None:
    handler = _PublicRedirectHandler("image")
    req = urllib.request.Request("https://example.com/x")
    with pytest.raises(UnsafeURLError):
        handler.redirect_request(
            req, BytesIO(), 302, "Found", Message(), "http://169.254.169.254/"
        )


def test_escape_hatch_follows_redirects(server_url: str) -> None:
    settings_manager.user_config = {"allow_private_urls": True}
    try:
        with open_public_url(f"{server_url}/redirect", timeout=5) as response:
            assert response.read() == b"ok"
    finally:
        settings_manager.reset_user_config()
