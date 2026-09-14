"""Register zimage's models + OpenAPI description in the global registries."""

from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import HfSnapshotResource

from .._constants.description import DESCRIPTION
from .._models import zimage
from .._settings import settings_manager


def register() -> None:
    capability_spec_registry.register(
        CapabilitySpec(
            name="zimage",
            domain="image",
            title="kiapi Z-Image API",
            summary="Generate images and train LoRA adapters with Z-Image models.",
            description=DESCRIPTION,
            openapi_path="/v1/image/zimage/openapi.json",
            docs_path="/v1/image/zimage/docs",
            redoc_path="/v1/image/zimage/redoc",
            path_prefixes=("/v1/image/zimage",),
        )
    )

    settings = settings_manager.get_settings()

    model_registry.register(
        ModelSpec(
            name="turbo",
            family="zimage",
            domain="image",
            repo=settings.turbo_repo,
            module=zimage,
            weight_gb=6.0,
            peak_headroom_gb=8.0,
            framework="mlx",
            priority=0,
            default=True,
            setup_resources=(
                HfSnapshotResource(repo=settings.turbo_repo, disk_gb=5.5),
            ),
        )
    )

    model_registry.register(
        ModelSpec(
            name="base",
            family="zimage",
            domain="image",
            repo=settings.base_repo,
            module=zimage,
            weight_gb=12.0,
            peak_headroom_gb=16.0,
            framework="mlx",
            priority=0,
            setup_resources=(
                HfSnapshotResource(repo=settings.base_repo, disk_gb=19.0),
            ),
        )
    )
