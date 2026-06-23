"""Networking guards shared across capabilities.

Currently a single SSRF guard for user-supplied URLs; see
:func:`verify_public_url`.
"""

from ._exceptions.unsafe_url_error import UnsafeURLError
from ._helpers.verify_public_url import verify_public_url
from ._settings import NetSettings, settings_manager

__all__ = [
    "NetSettings",
    "UnsafeURLError",
    "settings_manager",
    "verify_public_url",
]
