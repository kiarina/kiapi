import time
from collections.abc import Generator
from typing import Any

import mlx.core as mx

from ._clone_prompt import ClonePrompt
from ._embed import _embed
from ._prepared_reference import PreparedReference
from ._text_source import TextSource


def generate_prepared(
    model: Any,
    prompt: ClonePrompt,
    source: TextSource,
    session: PreparedReference,
    *,
    emit_frames: int = 4,
    max_frames: int = 1000,
    temperature: float = 0.9,
    trace: dict[str, Any] | None = None,
    require_text_consumed: bool = True,
) -> Generator[Any, None, None]:
    trace = trace if trace is not None else {}
    trace.update(codes=[], waits=[], commits=[], prepared_rows=session.prepared_rows)
    start = time.perf_counter()

    def stamp() -> float:
        return time.perf_counter() - start

    observed = 0

    def poll() -> tuple[list[int], bool, int]:
        nonlocal observed
        ids, closed, version = source.poll()
        if len(ids) != observed:
            trace["commits"].append(
                {"t": stamp(), "tokens": len(ids), "text_chars": len(source.text)}
            )
            observed = len(ids)
        return (ids, closed, version)

    while True:
        ids, closed, version = poll()
        if ids and (closed or len(ids) >= session.required_tokens):
            break
        if closed:
            raise ValueError("No target text")
        source.wait(version)
    needed = session.required_tokens
    text = _embed(model, ids[:needed])
    if len(ids) < needed:
        assert closed
        text = mx.concatenate([text, prompt.eos], axis=1)
        if text.shape[1] < needed:
            text = mx.concatenate(
                [
                    text,
                    mx.broadcast_to(
                        prompt.pad, (1, needed - text.shape[1], text.shape[-1])
                    ),
                ],
                axis=1,
            )
    inputs = text + session.bridge
    cache = session.cache
    for row in range(needed - 1):
        logits, hidden = model.talker(inputs[:, row : row + 1], cache=cache)
        mx.eval(logits, hidden)
    inputs = inputs[:, -1:]
    cursor = needed
    code_cache = model.talker.code_predictor.make_cache()
    decoder = model.speech_tokenizer.decoder
    trace["prefill"] = {
        "t": stamp(),
        "target_tokens": len(ids),
        "required_prefix_tokens": session.required_tokens,
        "cached_rows": session.prepared_rows,
    }
    generated = []
    first_ids: list[int] = []
    emitted = 0
    eos = model.config.talker_config.codec_eos_token_id
    suppress = model._suppress_codec_tokens(eos)
    try:
        for _step in range(max_frames):
            logits, hidden = model.talker(inputs, cache=cache)
            ids, closed, _ = poll()
            token = model._sample_token(
                logits,
                temperature=temperature,
                top_k=50,
                top_p=1.0,
                repetition_penalty=1.05,
                repetition_context_size=max(1, len(first_ids)),
                generated_tokens=first_ids or None,
                suppress_tokens=suppress
                + (
                    []
                    if closed and (not require_text_consumed or cursor > len(ids))
                    else [eos]
                ),
            )
            mx.eval(token)
            if int(token[0, 0]) == eos:
                trace["stop"] = "eos"
                trace["target_tokens"] = len(ids)
                trace["consumed_target_tokens"] = min(cursor, len(ids))
                trace["eos_row_fed"] = cursor > len(ids)
                break
            parts, codes = model._predict_code_tokens(
                token,
                hidden,
                temperature=temperature,
                top_k=50,
                top_p=1.0,
                code_cache=code_cache,
            )
            mx.eval(codes)
            first_ids.append(int(token[0, 0]))
            generated.append(codes)
            trace["codes"].append(codes[0].tolist())
            if len(generated) - emitted >= emit_frames:
                block = mx.transpose(mx.stack(generated[emitted:], axis=1), (0, 2, 1))
                pcm = decoder.streaming_step(block).squeeze(1)[0]
                mx.eval(pcm)
                emitted = len(generated)
                yield pcm
            while True:
                ids, closed, version = poll()
                if cursor < len(ids):
                    next_text = _embed(model, [ids[cursor]])
                    break
                if closed:
                    next_text = prompt.eos if cursor == len(ids) else prompt.pad
                    break
                before = stamp()
                source.wait(version)
                trace["waits"].append({"start": before, "end": stamp()})
            inputs = next_text + model._codec_embeds_for_tokens(parts)
            mx.eval(inputs)
            cursor += 1
        else:
            trace["stop"] = "frame_cap"
            raise RuntimeError("max_frames reached before EOS")
        if len(generated) > emitted:
            block = mx.transpose(mx.stack(generated[emitted:], axis=1), (0, 2, 1))
            pcm = decoder.streaming_step(block).squeeze(1)[0]
            mx.eval(pcm)
            yield pcm
    finally:
        decoder.reset_streaming_state()
