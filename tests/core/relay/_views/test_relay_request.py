import pytest
from pydantic import ValidationError

from kiapi.core.relay import (
    RelayMultipartBody,
    RelayMultipartFile,
    RelayRequest,
    RelaySettings,
)


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


def test_relay_request_accepts_multipart_body() -> None:
    request = RelayRequest(
        method="POST",
        path="/v1/files",
        multipart=RelayMultipartBody(
            files=[
                RelayMultipartFile(
                    filename="hello.txt",
                    content_base64="aGVsbG8=",
                )
            ]
        ),
    )

    assert request.multipart is not None
    assert request.multipart.files[0].content() == b"hello"


def test_relay_request_rejects_mixed_json_and_multipart_body() -> None:
    with pytest.raises(ValidationError):
        RelayRequest(
            method="POST",
            path="/v1/files",
            body={"ok": True},
            multipart=RelayMultipartBody(
                files=[
                    RelayMultipartFile(
                        filename="hello.txt",
                        content_base64="aGVsbG8=",
                    )
                ]
            ),
        )


def test_relay_settings_include_local_preset() -> None:
    assert RelaySettings().presets["local"] == "kiapi.relay.local:create_local_relay"
