"""Register ernie's models + OpenAPI description in the global registries."""

from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import HfSnapshotResource

from .._constants.description import DESCRIPTION
from .._models import ernie
from .._settings import settings_manager


def register() -> None:
    capability_spec_registry.register(
        CapabilitySpec(
            name="ernie",
            domain="image",
            title="kiapi ERNIE-Image API",
            summary="Generate, edit, and train LoRA adapters for ERNIE-Image models.",
            description=DESCRIPTION,
            openapi_path="/v1/image/ernie/openapi.json",
            docs_path="/v1/image/ernie/docs",
            redoc_path="/v1/image/ernie/redoc",
            path_prefixes=("/v1/image/ernie",),
        )
    )

    _s = settings_manager.get_settings()

    model_registry.register(
        ModelSpec(
            name="turbo",
            family="ernie",
            domain="image",
            repo=_s.turbo_model,
            module=ernie,
            weight_gb=6.0,
            peak_headroom_gb=4.0,
            framework="mlx",
            priority=0,
            aliases=("ernie-image-turbo", "baidu/ERNIE-Image-Turbo"),
            default=True,
            setup_resources=(HfSnapshotResource(repo=_s.turbo_model, disk_gb=31.6),),
        )
    )

    model_registry.register(
        ModelSpec(
            name="base",
            family="ernie",
            domain="image",
            repo=_s.base_model,
            module=ernie,
            weight_gb=12.0,
            peak_headroom_gb=8.0,
            framework="mlx",
            priority=0,
            aliases=("ernie-image", "baidu/ERNIE-Image"),
            setup_resources=(HfSnapshotResource(repo=_s.base_model, disk_gb=31.6),),
        )
    )
