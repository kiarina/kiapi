from typing import Any

import mlx.core as mx


def _embed(model: Any, ids: list[int]) -> Any:
    return model.talker.text_projection(
        model.talker.get_text_embeddings()(mx.array([ids]))
    )
