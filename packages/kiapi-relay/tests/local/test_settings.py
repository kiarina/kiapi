import pytest
from pydantic import ValidationError

from kiapi_relay.local import LocalRelaySettings


def test_settings_normalize_prefix() -> None:
    settings = LocalRelaySettings(
        node_id="worker-1",
        prefix="/private/kiapi/",
    )

    assert settings.prefix == "private/kiapi"


def test_settings_reject_invalid_node_id() -> None:
    with pytest.raises(ValidationError):
        LocalRelaySettings(node_id="worker/1")
