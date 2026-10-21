import time
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

import mlx.core as mx

from ._text_source import TextSource


def embed(model: Any, ids: list[int]) -> Any:
    return model.talker.text_projection(
        model.talker.get_text_embeddings()(mx.array([ids]))
    )


@dataclass
class ClonePrompt:
    prefix: Any
    ref_text_ids: list[int]
    ref_codes: Any
    codec_embeds: Any
    pad: Any
    eos: Any

    @property
    def required_prefix_tokens(self) -> int:
        return max(0, int(self.codec_embeds.shape[1]) - len(self.ref_text_ids))


def prepare_clone(
    model: Any, audio: Any, transcript: str, language: str = "japanese"
) -> ClonePrompt:
    original, _, pad, codes = getattr(
        model, "_prepare_live_clone", model._prepare_icl_generation_inputs
    )("", audio, transcript, language)
    ref_ids = model.tokenizer.encode(
        f"<|im_start|>assistant\n{transcript}<|im_end|>\n"
    )[3:-2]
    n = len(ref_ids) + 1 + codes.shape[2] + 1
    prefix = original[:, : original.shape[1] - n]
    codec = model.talker.get_input_embeddings()(codes[:, 0, :])
    for i in range(model.config.talker_config.num_code_groups - 1):
        codec = codec + model.talker.code_predictor.codec_embedding[i](
            codes[:, i + 1, :]
        )
    bos = model.talker.get_input_embeddings()(
        mx.array([[model.config.talker_config.codec_bos_id]])
    )
    codec = mx.concatenate([bos, codec], axis=1)
    eos = embed(model, [model.config.tts_eos_token_id])
    mx.eval(prefix, codec, pad, codes, eos)
    return ClonePrompt(prefix, ref_ids, codes, codec, pad, eos)


def full_prompt(
    model: Any, prompt: ClonePrompt, target_ids: list[int]
) -> tuple[Any, Any]:
    """Reference-compatible full causal prompt, also exported for float32 parity."""
    text = mx.concatenate(
        [embed(model, prompt.ref_text_ids + target_ids), prompt.eos], axis=1
    )
    length = prompt.codec_embeds.shape[1]
    if text.shape[1] < length:
        text = mx.concatenate(
            [
                text,
                mx.broadcast_to(
                    prompt.pad, (1, length - text.shape[1], text.shape[-1])
                ),
            ],
            axis=1,
        )
    inputs = mx.concatenate(
        [prompt.prefix, text[:, :length] + prompt.codec_embeds], axis=1
    )
    trailing = text[:, length:] if text.shape[1] > length else prompt.pad
    return (inputs, trailing)


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
    text = embed(model, prompt.ref_text_ids + ids)
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
                    next_text = embed(model, [absolute[cursor]])
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
