import pytest
from pydantic import ValidationError

from kiapi.capabilities.web._views.fetch_request import FetchRequest


def test_fetch_request_accepts_http_and_https() -> None:
    assert FetchRequest(url="http://a.test").format == "markdown"
    assert FetchRequest(url="https://a.test", format="pdf").format == "pdf"


@pytest.mark.parametrize(
    "url", ["ftp://a.test/f", "file:///etc/passwd", "a.test", "javascript:alert(1)"]
)
def test_fetch_request_rejects_non_http_scheme(url: str) -> None:
    with pytest.raises(ValidationError):
        FetchRequest(url=url)


def test_fetch_request_rejects_unknown_format() -> None:
    with pytest.raises(ValidationError):
        FetchRequest(url="https://a.test", format="html")  # type: ignore[arg-type]


def test_fetch_request_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        FetchRequest(url="https://a.test", mode="async")  # type: ignore[call-arg]
