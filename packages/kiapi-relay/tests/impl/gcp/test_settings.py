import pytest
from pydantic import ValidationError

from kiapi_relay.impl.gcp import GCPRelaySettings


def test_settings_normalize_paths() -> None:
    settings = GCPRelaySettings(
        node_id="worker-1",
        database_url="https://example.firebaseio.com/",
        bucket="relay-bucket",
        prefix="/private/kiapi/",
    )

    assert settings.database_url == "https://example.firebaseio.com"
    assert settings.prefix == "private/kiapi"


def test_settings_reject_insecure_database_url() -> None:
    with pytest.raises(ValidationError):
        GCPRelaySettings(
            node_id="worker-1",
            database_url="http://example.firebaseio.com",
            bucket="relay-bucket",
        )
