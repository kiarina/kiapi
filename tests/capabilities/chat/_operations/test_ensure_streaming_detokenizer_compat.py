import pytest

from kiapi.capabilities.chat._operations.ensure_streaming_detokenizer_compat import (
    ensure_streaming_detokenizer_compat,
)


def test_bpe_streaming_detokenizer_tolerates_invalid_utf8_flush():  # type: ignore
    tokenizer_utils = pytest.importorskip("mlx_vlm.tokenizer_utils")

    ensure_streaming_detokenizer_compat()

    detokenizer = object.__new__(tokenizer_utils.BPEStreamingDetokenizer)
    detokenizer.trim_space = False
    detokenizer.tokenmap = ["¥", "Ġnext"]
    detokenizer._byte_decoder = {
        "¥": 165,
        "Ġ": 32,
        "n": 110,
        "e": 101,
        "x": 120,
        "t": 116,
    }
    detokenizer.reset()

    detokenizer.add_token(0)
    detokenizer.add_token(1)

    assert detokenizer.text == "�"
    assert detokenizer._unflushed == "Ġnext"
