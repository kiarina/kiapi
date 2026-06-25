import pytest
from pydantic import ValidationError

from kiapi.core.relay import RelayRequest


def test_relay_request_accepts_local_absolute_path() -> None:
    request = RelayRequest(method="POST", path="/v1/embedding")

    assert request.path == "/v1/embedding"


@pytest.mark.parametrize(
    "path",
    ["v1/embedding", "//example.com/v1/embedding", "https://example.com/v1"],
)
def test_relay_request_rejects_non_local_path(path: str) -> None:
    with pytest.raises(ValidationError):
        RelayRequest(method="POST", path=path)
