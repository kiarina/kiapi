"""Merge an embedding request with settings defaults into the complete EmbedParams."""

from .._settings import EmbeddingSettings
from .._views.embed_params import EmbedParams
from .._views.embed_request import EmbedRequest


def resolve_embed_params(
    settings: EmbeddingSettings,
    req: EmbedRequest,
    *,
    variant: str,
) -> EmbedParams:
    return EmbedParams(
        model=variant,
        inputs=req.inputs(),
        max_length=settings.max_length,
    )
