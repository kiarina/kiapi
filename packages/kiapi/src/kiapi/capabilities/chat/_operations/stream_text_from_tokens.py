from collections.abc import Iterable, Iterator
from copy import copy


def stream_text_from_tokens(processor, chunks: Iterable) -> Iterator:  # type: ignore
    """Yield chunks whose text is decoded from token ids when mlx-vlm supports it."""
    try:
        from mlx_vlm.tokenizer_utils import (  # type: ignore
            _ServerTokenStreamer,
            make_streaming_detokenizer,
        )
    except Exception:
        yield from chunks
        return

    tokenizer = processor.tokenizer if hasattr(processor, "tokenizer") else processor
    streamer = _ServerTokenStreamer(tokenizer, make_streaming_detokenizer(processor))

    for chunk in chunks:
        token = getattr(chunk, "token", None)
        finish_reason = getattr(chunk, "finish_reason", None)

        if token is None:
            text = str(getattr(chunk, "text", "") or "")
        elif finish_reason is None:
            text = streamer.advance(token, None)
        else:
            text = streamer.finalize()

        out = copy(chunk)
        out.text = text
        yield out
