"""Register embedding's models + OpenAPI description in the global registries."""

from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import HfSnapshotResource

from .._constants.description import DESCRIPTION
from .._models import qwen3_text, qwen3_vl


def register() -> None:
    capability_spec_registry.register(
        CapabilitySpec(
            name="embedding",
            domain="embedding",
            title="kiapi Embedding API",
            summary="Create text and multimodal embeddings for retrieval and similarity search.",
            description=DESCRIPTION,
            openapi_path="/v1/embedding/openapi.json",
            docs_path="/v1/embedding/docs",
            redoc_path="/v1/embedding/redoc",
            path_prefixes=("/v1/embedding",),
        )
    )

    model_registry.register(
        ModelSpec(
            name="qwen3-embedding-8b",
            family="embedding",
            domain="embedding",
            repo="mlx-community/Qwen3-Embedding-8B-mxfp8",
            module=qwen3_text,
            weight_gb=7.3,  # measured on device (estimate was 8.0)
            peak_headroom_gb=2.0,
            framework="mlx",
            priority=10,
            aliases=("text", "qwen3-embedding", "qwen3_embedding"),
            default=True,
            setup_resources=(
                HfSnapshotResource(
                    repo="mlx-community/Qwen3-Embedding-8B-mxfp8",
                    disk_gb=7.82,
                ),
            ),
        )
    )
    model_registry.register(
        ModelSpec(
            name="qwen3-vl-embedding-2b",
            family="embedding",
            domain="embedding",
            repo="mlx-community/Qwen3-VL-Embedding-2B-mxfp8",
            module=qwen3_vl,
            weight_gb=2.4,  # measured on device (estimate was 2.0)
            peak_headroom_gb=2.0,  # image inputs add some headroom
            framework="mlx",
            priority=20,  # tiny + frequently used → keep resident
            aliases=("vl", "qwen3-vl-embedding", "qwen3_vl_embedding"),
            setup_resources=(
                HfSnapshotResource(
                    repo="mlx-community/Qwen3-VL-Embedding-2B-mxfp8",
                    disk_gb=2.59,
                ),
            ),
        )
    )
