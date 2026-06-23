"""Register chat's models + OpenAPI description in the global registries."""

from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import HfSnapshotResource

from .._constants.description import DESCRIPTION
from .._models import qwen3_5, qwen3_omni


def register() -> None:
    capability_spec_registry.register(
        CapabilitySpec(
            name="chat",
            domain="chat",
            title="kiapi Chat API",
            summary="OpenAI-compatible Chat Completions for text and multimodal conversations.",
            description=DESCRIPTION,
            openapi_path="/v1/chat/openapi.json",
            docs_path="/v1/chat/docs",
            redoc_path="/v1/chat/redoc",
            path_prefixes=("/v1/chat",),
            include_paths=("/v1/models",),
        )
    )

    model_registry.register(
        ModelSpec(
            name="qwen3-omni",
            family="chat",
            domain="chat",
            repo="mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit",
            module=qwen3_omni,
            weight_gb=20.3,  # measured on device (estimate was 22.0)
            peak_headroom_gb=4.0,  # negligible for text/image; margin for heavy A/V
            framework="mlx",
            priority=0,
            aliases=("omni", "qwen3-omni-30b", "qwen3_omni_moe"),
            default=True,
            setup_resources=(
                HfSnapshotResource(
                    repo="mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit",
                    disk_gb=21.8,
                ),
            ),
        )
    )
    model_registry.register(
        ModelSpec(
            name="qwen3.6-27b",
            family="chat",
            domain="chat",
            repo="mlx-community/Qwen3.6-27B-4bit",
            module=qwen3_5,
            weight_gb=15.0,  # measured on device (estimate was 16.0)
            peak_headroom_gb=4.0,
            framework="mlx",
            priority=0,
            aliases=("qwen3.6", "qwen3_5", "qwen3-vl", "vlm"),
            setup_resources=(
                HfSnapshotResource(
                    repo="mlx-community/Qwen3.6-27B-4bit",
                    disk_gb=16.1,
                ),
            ),
        )
    )
