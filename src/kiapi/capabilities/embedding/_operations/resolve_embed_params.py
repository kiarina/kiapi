"""Merge an embedding request with settings defaults into the complete EmbedParams."""

from kiapi.capabilities import CapabilityError

from .._settings import EmbeddingSettings
from .._views.embed_params import EmbedParams
from .._views.embed_request import EmbedRequest

MAX_INPUTS = 2048


def resolve_embed_params(
    settings: EmbeddingSettings,
    req: EmbedRequest,
    *,
    variant: str,
    dimension_range: tuple[int, int],
) -> EmbedParams:
    inputs = req.items()
    if not inputs:
        raise CapabilityError("request has no input")
    if len(inputs) > MAX_INPUTS:
        raise CapabilityError(f"input has more than {MAX_INPUTS} items")

    minimum, maximum = dimension_range
    if req.dimensions is not None and not minimum <= req.dimensions <= maximum:
        raise CapabilityError(
            f"{variant} supports dimensions from {minimum} to {maximum}"
        )

    return EmbedParams(
        model=variant,
        inputs=inputs,
        max_length=settings.max_length,
        dimensions=req.dimensions,
        encoding_format=req.encoding_format,
    )
