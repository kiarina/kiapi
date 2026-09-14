"""Register qwen's models + OpenAPI description in the global registries."""

from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import HfSnapshotResource

from .._constants.description import DESCRIPTION
from .._models import qwen
from .._settings import settings_manager


def register() -> None:
    capability_spec_registry.register(
        CapabilitySpec(
            name="qwen",
            domain="image",
            title="kiapi Qwen Image API",
            summary="Generate and edit images with Qwen Image models.",
            description=DESCRIPTION,
            openapi_path="/v1/image/qwen/openapi.json",
            docs_path="/v1/image/qwen/docs",
            redoc_path="/v1/image/qwen/redoc",
            path_prefixes=("/v1/image/qwen",),
        )
    )

    _s = settings_manager.get_settings()

    model_registry.register(
        ModelSpec(
            name="image",
            family="qwen",
            domain="image",
            repo=_s.image_model,
            module=qwen,
            weight_gb=22.0,
            peak_headroom_gb=8.0,
            framework="mlx",
            priority=0,
            aliases=("qwen-image", "Qwen/Qwen-Image"),
            default=True,
            setup_resources=(HfSnapshotResource(repo=_s.image_model, disk_gb=58.0),),
        )
    )

    model_registry.register(
        ModelSpec(
            name="edit-2509",
            family="qwen",
            domain="image",
            repo=_s.edit_model,
            module=qwen,
            weight_gb=22.0,
            peak_headroom_gb=8.0,
            framework="mlx",
            priority=0,
            aliases=("qwen-edit", "qwen-image-edit", "Qwen/Qwen-Image-Edit-2509"),
            setup_resources=(HfSnapshotResource(repo=_s.edit_model, disk_gb=58.0),),
        )
    )
