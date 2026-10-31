from kiapi.capabilities.embedding._operations.format_response import format_response
from kiapi.capabilities.embedding._utils.encode_vector import encode_vector


def test_format_follows_openai_shape() -> None:
    result = format_response(
        model_name="m",
        vectors=[[1.0, 0.0], [0.0, 1.0]],
        elapsed=0.1234,
        prompt_tokens=7,
    )

    assert result == {
        "object": "list",
        "data": [
            {"object": "embedding", "index": 0, "embedding": [1.0, 0.0]},
            {"object": "embedding", "index": 1, "embedding": [0.0, 1.0]},
        ],
        "model": "m",
        "usage": {"prompt_tokens": 7, "total_tokens": 7},
        "timings": {"total_s": 0.123},
    }


def test_format_resizes_before_encoding() -> None:
    result = format_response(
        model_name="m",
        vectors=[[0.0, 1.0, 1.0]],
        elapsed=0.0,
        prompt_tokens=1,
        dimensions=2,
        encoding_format="base64",
    )

    assert result["data"][0]["embedding"] == encode_vector([0.0, 1.0])
