import pytest

from kiapi.api.web.router import _negotiate_format


@pytest.mark.parametrize(
    "accept",
    [
        None,
        "*/*",
        "text/markdown",
        "text/plain",
        "text/html,application/xhtml+xml,*/*",  # a browser's default
        "text/*",
    ],
)
def test_negotiate_defaults_to_markdown(accept: str | None) -> None:
    assert _negotiate_format(accept) == "markdown"


@pytest.mark.parametrize(
    "accept",
    ["application/pdf", "application/pdf, */*", "APPLICATION/PDF"],
)
def test_negotiate_picks_pdf(accept: str) -> None:
    assert _negotiate_format(accept) == "pdf"


@pytest.mark.parametrize("accept", ["application/json", "image/png"])
def test_negotiate_rejects_incompatible(accept: str) -> None:
    assert _negotiate_format(accept) is None
