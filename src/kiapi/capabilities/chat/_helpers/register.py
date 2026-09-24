"""Register chat's models + OpenAPI description in the global registries."""

from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import HfSnapshotResource

from .._constants.description import DESCRIPTION
from .._models import qwen3_5, qwen3_omni, qwen4_exp
from .._settings import settings_manager


def register() -> None:
    settings = settings_manager.get_settings()
    headroom = 4.0 + (settings.apc_memory_max_gb if settings.apc_enabled else 0.0)
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
            peak_headroom_gb=headroom,
            framework="mlx",
            priority=0,
            aliases=("omni", "qwen3-omni-30b", "qwen3_omni_moe"),
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
            name="qwen3.8-27b",
            family="chat",
            domain="chat",
            repo="mlx-community/Qwen3.8-27B-4bit",
            module=qwen3_5,
            weight_gb=16.0,
            peak_headroom_gb=headroom,
            framework="mlx",
            priority=0,
            aliases=("qwen3_5", "qwen3-vl"),
            setup_resources=(
                HfSnapshotResource(
                    repo="mlx-community/Qwen3.8-27B-4bit",
                    disk_gb=16.1,
                ),
            ),
        )
    )
    model_registry.register(
        ModelSpec(
            name="qwen3.8-flash-next",
            family="chat",
            domain="chat",
            repo="mlx-community/Qwen3.8-Flash-Next-4bit",
            module=qwen4_exp,
            # Measured with the memory-mapped PLE table; 111.5 GB when resident.
            weight_gb=79.5,
            peak_headroom_gb=headroom,
            framework="mlx",
            priority=0,
            aliases=("vlm", "qwen3.8", "qwen3.8-flash", "flash-next"),
            setup_resources=(
                HfSnapshotResource(
                    repo="mlx-community/Qwen3.8-Flash-Next-4bit",
                    disk_gb=111.5,
                ),
            ),
        )
    )
