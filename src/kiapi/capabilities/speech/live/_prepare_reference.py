import time
from typing import Any

import mlx.core as mx

from ._clone_prompt import ClonePrompt
from ._copy_state import _copy_state
from ._embed import _embed
from ._prepared_reference import PreparedReference


def prepare_reference(model: Any, prompt: ClonePrompt) -> PreparedReference:
    started = time.perf_counter()
    length = int(prompt.codec_embeds.shape[1])
    text = mx.concatenate([_embed(model, prompt.ref_text_ids), prompt.eos], axis=1)
    if text.shape[1] > length:
        raise ValueError("Reference text exceeds reference codec region")
    text = mx.concatenate(
        [
            text,
            mx.broadcast_to(prompt.pad, (1, length - text.shape[1], text.shape[-1])),
        ],
        axis=1,
    )
    cfg = model.config.talker_config
    codec_eos = model.talker.get_input_embeddings()(
        mx.array([[cfg.codec_eos_token_id]])
    )
    prefill = mx.concatenate(
        [
            prompt.prefix,
            text + prompt.codec_embeds,
            prompt.pad + codec_eos,
            prompt.prefix,
        ],
        axis=1,
    )
    cache = model.talker.make_cache()
    logits, hidden = model.talker(prefill, cache=cache)
    mx.eval(logits, hidden)
    decoder = model.speech_tokenizer.decoder
    decoder.reset_streaming_state()
    try:
        mx.eval(decoder.streaming_step(prompt.ref_codes))
        state = {
            name: {
                key: _copy_state(getattr(module, key))
                for key in ("_buffer", "_overflow", "_transformer_cache")
                if hasattr(module, key)
            }
            for name, module in decoder.named_modules()
        }
        # named_modules may exclude the root decoder.
        state[""] = {"_transformer_cache": _copy_state(decoder._transformer_cache)}
        bridge = model.talker.get_input_embeddings()(mx.array([[cfg.codec_bos_id]]))
        mx.eval(bridge)
        return PreparedReference(
            prompt,
            _copy_state(cache),
            bridge,
            state,
            int(prefill.shape[1]),
            time.perf_counter() - started,
        )
    finally:
        decoder.reset_streaming_state()
