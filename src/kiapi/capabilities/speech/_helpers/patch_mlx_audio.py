"""Align mlx-audio 0.6.1 Qwen3-TTS voice cloning with the reference implementation.

Each MLX module matches qwen-tts 0.1.1 (PyTorch) in float32, but mlx-audio's
voice-clone generation differs in how it calls them, and listeners heard the
difference:

- Repetition penalty: mlx-audio raises it to at least 1.5 and applies it to the
  last 64 tokens; qwen-tts applies the checkpoint's 1.05 to every generated token.
- Prompt layout: qwen-tts (``non_streaming_mode=False``) overlays the text
  (reference transcript + input + eos) on the reference codes position by
  position and feeds leftover text one token per step; mlx-audio puts all text
  over codec pad, then the reference codes over text pad.
- Streaming: mlx-audio resets the streaming decoder and decodes only generated
  codes, so the first chunk lacks the reference as left context and the onset
  sounds off. Priming the decoder with the end of the reference fixes it.

Measurements and listening results:
https://github.com/kiarina/labs/tree/main/2026/10/20/japanese-zero-shot-tts-compare
"""

from typing import Any

# Codes waiting to prime the next streaming decode; set per voice-clone prompt.
# Safe as module state: all inference runs on the single worker thread.
_pending: dict[str, Any] = {"codes": None, "tokens": 0, "in_icl": False}
_patched = False

REPETITION_PENALTY = 1.05


def set_prime_tokens(tokens: int) -> None:
    _pending["tokens"] = tokens


def clear_pending_prime() -> None:
    _pending["codes"] = None
    _pending["in_icl"] = False


def patch_mlx_audio() -> None:
    global _patched
    if _patched:
        return

    import mlx.core as mx
    from mlx_audio.tts.models.qwen3_tts.qwen3_tts import (  # type: ignore[import-untyped]
        Model,
    )
    from mlx_audio.tts.models.qwen3_tts.speech_tokenizer import (  # type: ignore[import-untyped]
        Qwen3TTSSpeechTokenizerDecoder,
    )

    prepare_icl = Model._prepare_icl_generation_inputs
    generate_icl = Model._generate_icl
    sample_token = Model._sample_token
    reset_streaming_state = Qwen3TTSSpeechTokenizerDecoder.reset_streaming_state

    def _reference_layout(
        self: Any, input_embeds: Any, text: str, ref_text: str, ref_codes: Any
    ) -> tuple[Any, Any]:
        talker, config = self.talker, self.config.talker_config
        ref_ids = mx.array(
            self.tokenizer.encode(f"<|im_start|>assistant\n{ref_text}<|im_end|>\n")
        )[None, 3:-2]
        text_ids = mx.array(
            self.tokenizer.encode(
                f"<|im_start|>assistant\n{text}<|im_end|>\n<|im_start|>assistant\n"
            )
        )[None, 3:-5]
        special = talker.text_projection(
            talker.get_text_embeddings()(
                mx.array([[self.config.tts_eos_token_id, self.config.tts_pad_token_id]])
            )
        )
        tts_eos, tts_pad = special[:, 0:1], special[:, 1:2]
        text_embed = talker.text_projection(
            talker.get_text_embeddings()(mx.concatenate([ref_ids, text_ids], axis=1))
        )
        text_embed = mx.concatenate([text_embed, tts_eos], axis=1)
        codec_embed = talker.get_input_embeddings()(ref_codes[:, 0, :])
        for i in range(config.num_code_groups - 1):
            codec_embed = codec_embed + talker.code_predictor.codec_embedding[i](
                ref_codes[:, i + 1, :]
            )
        codec_embed = mx.concatenate(
            [
                talker.get_input_embeddings()(mx.array([[config.codec_bos_id]])),
                codec_embed,
            ],
            axis=1,
        )
        text_lens, codec_lens = text_embed.shape[1], codec_embed.shape[1]
        # Role and codec prefix are the same in both layouts.
        prefix = input_embeds[:, : input_embeds.shape[1] - text_lens - codec_lens]
        if text_lens > codec_lens:
            icl = text_embed[:, :codec_lens] + codec_embed
            trailing = text_embed[:, codec_lens:]
        else:
            pad = mx.broadcast_to(
                tts_pad, (1, codec_lens - text_lens, tts_pad.shape[-1])
            )
            icl = mx.concatenate([text_embed, pad], axis=1) + codec_embed
            trailing = tts_pad
        return mx.concatenate([prefix, icl], axis=1), trailing

    def _prepare_icl(
        self: Any, text: str, ref_audio: Any, ref_text: str, language: str = "auto"
    ) -> Any:
        input_embeds, trailing, pad_embed, ref_codes = prepare_icl(
            self, text, ref_audio, ref_text, language
        )
        _pending["codes"] = ref_codes
        input_embeds, trailing = _reference_layout(
            self, input_embeds, text, ref_text, ref_codes
        )
        return input_embeds, trailing, pad_embed, ref_codes

    def _generate(self: Any, *args: Any, **kwargs: Any) -> Any:
        kwargs["repetition_penalty"] = REPETITION_PENALTY
        _pending["in_icl"] = True
        try:
            yield from generate_icl(self, *args, **kwargs)
        finally:
            _pending["in_icl"] = False

    def _sample(self: Any, logits: Any, *args: Any, **kwargs: Any) -> Any:
        if _pending["in_icl"] and kwargs.get("generated_tokens"):
            kwargs["repetition_context_size"] = len(kwargs["generated_tokens"])
        return sample_token(self, logits, *args, **kwargs)

    def _reset(self: Any) -> None:
        reset_streaming_state(self)
        codes, _pending["codes"] = _pending["codes"], None
        if codes is not None:
            if _pending["tokens"] > 0:
                codes = codes[:, :, -_pending["tokens"] :]
            mx.eval(self.streaming_step(codes))  # keep the decoder state only

    Model._prepare_live_clone = prepare_icl
    Model._prepare_icl_generation_inputs = _prepare_icl
    Model._generate_icl = _generate
    Model._sample_token = _sample
    Qwen3TTSSpeechTokenizerDecoder.reset_streaming_state = _reset
    _patched = True
