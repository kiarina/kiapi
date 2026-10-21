from typing import Any

import mlx.core as mx

from ._clone_prompt import ClonePrompt
from ._embed import _embed


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
    eos = _embed(model, [model.config.tts_eos_token_id])
    mx.eval(prefix, codec, pad, codes, eos)
    return ClonePrompt(prefix, ref_ids, codes, codec, pad, eos)
