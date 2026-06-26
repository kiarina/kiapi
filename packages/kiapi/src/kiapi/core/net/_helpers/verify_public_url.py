"""SSRF guard for user-supplied URLs.

Several capabilities materialize inputs from a client-provided ``http(s)`` URL
(chat media, embedding image, generic file refs). Without a check, a client could
point the server at ``http://localhost:...``, ``http://169.254.169.254/`` (cloud
metadata), or any internal service — a server-side request forgery. Call
:func:`verify_public_url` before fetching.

The check resolves the host and rejects the URL if *any* resolved address is not
a public unicast address. It is a best-effort mitigation, not airtight: a DNS
name that re-resolves to a private address between this check and the actual
fetch (DNS rebinding) is not covered. The ``KIAPI_NET_ALLOW_PRIVATE_URLS``
setting disables the guard for trusted local development.
"""

import ipaddress
import socket
import urllib.parse

from .._exceptions.unsafe_url_error import UnsafeURLError
from .._settings import settings_manager


def _is_public(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    mapped = getattr(addr, "ipv4_mapped", None)
    if mapped is not None:
        addr = mapped
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def verify_public_url(url: str, *, kind: str = "url") -> None:
    """Raise :class:`UnsafeURLError` unless ``url`` is a fetchable public URL.

    Accepts only ``http``/``https`` whose host resolves entirely to public
    addresses. ``kind`` is used in the error message (e.g. ``"image"``).
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeURLError(
            f"{kind} url must be an http:// or https:// URL, got {parsed.scheme!r}"
        )

    host = parsed.hostname
    if not host:
        raise UnsafeURLError(f"{kind} url has no host")

    if settings_manager.get_settings().allow_private_urls:
        return

    # A bare IP literal still parses as hostname; getaddrinfo handles both.
    try:
        infos = socket.getaddrinfo(host, parsed.port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"cannot resolve {kind} url host {host!r}: {exc}") from exc

    for info in infos:
        ip = info[4][0]
        if not _is_public(ipaddress.ip_address(ip)):
            raise UnsafeURLError(
                f"{kind} url host {host!r} resolves to non-public address {ip}"
            )
