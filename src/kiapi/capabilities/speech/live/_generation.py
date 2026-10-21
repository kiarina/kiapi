import time
from collections.abc import Generator
from typing import Any

import mlx.core as mx

from ._clone_prompt import ClonePrompt
from ._embed import _embed
from ._text_source import TextSource


def generate_live(
    model: Any,
    prompt: ClonePrompt,
    source: TextSource,
    *,
    emit_frames: int = 4,
    max_frames: int = 1000,
    temperature: float = 0.9,
    trace: dict[str, Any] | None = None,
) -> Generator[Any, None, None]:
    """Yield float32 PCM arrays while preserving a single talker/code/decoder state.

    ICL needs enough initial target tokens to cover reference-code prefill.
    If closed earlier, complete the original prompt with EOS/pad exactly as in
    full-input causal ICL. It never invents pad conditioning while input is open.
    """
    trace = trace if trace is not None else {}
    trace.update(codes=[], prefill=None, waits=[], commits=[])
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
        if ids and (closed or len(ids) >= prompt.required_prefix_tokens):
            break
        if closed:
            raise ValueError("No target text")
        source.wait(version)
    codec_length = prompt.codec_embeds.shape[1]
    text = _embed(model, prompt.ref_text_ids + ids)
    if closed:
        text = mx.concatenate([text, prompt.eos], axis=1)
    if text.shape[1] < codec_length:
        text = mx.concatenate(
            [
                text,
                mx.broadcast_to(
                    prompt.pad, (1, codec_length - text.shape[1], text.shape[-1])
                ),
            ],
            axis=1,
        )
    inputs = mx.concatenate(
        [prompt.prefix, text[:, :codec_length] + prompt.codec_embeds], axis=1
    )
    cursor = codec_length
    cache = model.talker.make_cache()
    code_cache = model.talker.code_predictor.make_cache()
    decoder = model.speech_tokenizer.decoder
    decoder.reset_streaming_state()
    mx.eval(decoder.streaming_step(prompt.ref_codes))
    trace["prefill"] = {
        "t": stamp(),
        "target_tokens": len(ids),
        "required_prefix_tokens": prompt.required_prefix_tokens,
    }
    generated = []
    first_ids: list[int] = []
    emitted = 0
    config = model.config.talker_config
    eos = config.codec_eos_token_id
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
                suppress_tokens=suppress + ([] if closed else [eos]),
            )
            mx.eval(token)
            if int(token[0, 0]) == eos:
                trace["stop"] = "eos"
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
                absolute = prompt.ref_text_ids + ids
                if cursor < len(absolute):
                    next_text = _embed(model, [absolute[cursor]])
                    break
                if closed:
                    next_text = prompt.eos if cursor == len(absolute) else prompt.pad
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
