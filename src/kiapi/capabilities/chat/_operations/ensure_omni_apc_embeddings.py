"""Keep full-prompt positions when mlx-vlm 0.7.1 restores an Omni prefix."""

from typing import Any


def ensure_omni_apc_embeddings() -> None:
    from mlx_vlm import apc
    from mlx_vlm.models.base import InputEmbeddingsFeatures
    from mlx_vlm.models.qwen3_omni_moe.qwen3_omni_moe import Model

    if getattr(Model, "supports_media_prefix_apc", False):
        return

    if getattr(Model, "_kiapi_apc_embeddings", False):
        return
    original_ids = apc.multimodal_token_ids_from_config

    def multimodal_token_ids(config: Any) -> set[int]:
        ids = original_ids(config)
        if getattr(config, "model_type", None) == "qwen3_omni_moe":
            thinker = config.thinker_config
            ids.update(original_ids(thinker))
            ids.add(int(thinker.audio_token_id))
        return ids

    apc.multimodal_token_ids_from_config = multimodal_token_ids
    original = Model.get_input_embeddings

    def get_input_embeddings(
        self: Any, input_ids: Any, pixel_values: Any = None, **kwargs: Any
    ) -> Any:
        positions = kwargs.get("position_ids")
        # APC only resumes a text suffix. The retained media tensors describe
        # the full prompt and must not be encoded/scattered into this suffix.
        if positions is not None and positions.shape[-1] > input_ids.shape[-1]:
            return InputEmbeddingsFeatures(
                inputs_embeds=self.language_model.model.embed_tokens(input_ids),
                position_ids=positions,
                rope_deltas=kwargs.get("rope_deltas"),
            )
        return original(self, input_ids, pixel_values, **kwargs)

    Model.get_input_embeddings = get_input_embeddings  # type: ignore[method-assign,assignment]
    Model._kiapi_apc_embeddings = True  # type: ignore[attr-defined]
