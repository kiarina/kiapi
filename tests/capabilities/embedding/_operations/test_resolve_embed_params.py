from typing import Any

import pytest

from kiapi.capabilities import CapabilityError
from kiapi.capabilities.embedding._operations.resolve_embed_params import (
    MAX_INPUTS,
    resolve_embed_params,
)
from kiapi.capabilities.embedding._settings import EmbeddingSettings
from kiapi.capabilities.embedding._views.embed_request import EmbedRequest


def _resolve(**body: Any):  # type: ignore[no-untyped-def]
    return resolve_embed_params(
        EmbeddingSettings(),
        EmbedRequest(**body),
        variant="qwen3-embedding-8b",
        dimension_range=(32, 4096),
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("hello", [{"text": "hello"}]),
        (["a", "b"], [{"text": "a"}, {"text": "b"}]),
        ({"text": "a", "image": "b"}, [{"text": "a", "image": "b"}]),
        (["a", {"image": "b"}], [{"text": "a"}, {"image": "b"}]),
    ],
)
def test_input_forms_become_items(value: Any, expected: list[dict[str, str]]) -> None:
    assert _resolve(input=value).inputs == expected


def test_openai_options_are_passed() -> None:
    params = _resolve(input="a", dimensions=256, encoding_format="base64", user="u")

    assert params.dimensions == 256
    assert params.encoding_format == "base64"


@pytest.mark.parametrize("dimensions", [31, 4097])
def test_rejects_unsupported_dimensions(dimensions: int) -> None:
    with pytest.raises(CapabilityError, match="supports dimensions"):
        _resolve(input="a", dimensions=dimensions)


def test_rejects_empty_list() -> None:
    with pytest.raises(CapabilityError, match="no input"):
        _resolve(input=[])


def test_rejects_too_many_items() -> None:
    with pytest.raises(CapabilityError, match="more than"):
        _resolve(input=["a"] * (MAX_INPUTS + 1))
