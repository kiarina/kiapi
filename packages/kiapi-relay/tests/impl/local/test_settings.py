import pytest
from pydantic import ValidationError

from kiapi_relay.impl.local import LocalRelaySettings


def test_settings_normalize_prefix() -> None:
    settings = LocalRelaySettings(
        prefix="/private/kiapi/",
    )

    assert settings.prefix == "private/kiapi"


def test_settings_reject_empty_prefix() -> None:
    with pytest.raises(ValidationError):
        LocalRelaySettings(prefix="/")
