import pytest
from pydantic import ValidationError

from kiapi_relay.impl.gcp import GCPRelaySettings


def test_settings_normalize_paths() -> None:
    settings = GCPRelaySettings(
        database_url="https://example.firebaseio.com/",
        bucket="relay-bucket",
    )

    assert settings.database_url == "https://example.firebaseio.com"


def test_settings_reject_insecure_database_url() -> None:
    with pytest.raises(ValidationError):
        GCPRelaySettings(
            database_url="http://example.firebaseio.com",
            bucket="relay-bucket",
        )
