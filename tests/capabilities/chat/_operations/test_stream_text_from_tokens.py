from dataclasses import dataclass
from typing import ClassVar

import pytest

from kiapi.capabilities.chat._operations.stream_text_from_tokens import (
    stream_text_from_tokens,
)


@dataclass
class Chunk:
    token: int | None
    text: str
    finish_reason: str | None = None
    generation_tokens: int = 0


def test_stream_text_from_tokens_decodes_bpe_markup_per_token() -> None:
    tokenizer_utils = pytest.importorskip("mlx_vlm.tokenizer_utils")

    class Processor:
        def __init__(self) -> None:
            self.tokenizer = _TinyTokenizer()
            self.detokenizer = tokenizer_utils.BPEStreamingDetokenizer(self.tokenizer)

    token_ids = [0, 1, 2, 3, 4]
    chunks = [Chunk(token=token_id, text="") for token_id in token_ids]
    chunks.append(Chunk(token=4, text="</function>", finish_reason="stop"))

    streamed = list(stream_text_from_tokens(Processor(), chunks))

    assert [chunk.text for chunk in streamed] == [
        "</",
        "function",
        ">",
        "\n",
        "<tool_call>",
        "",
    ]
    assert streamed[-1].generation_tokens == 0


class _TinyTokenizer:
    vocab: ClassVar[dict[str, int]] = {
        "</": 0,
        "function": 1,
        ">": 2,
        "Ċ": 3,
        "<tool_call>": 4,
    }
