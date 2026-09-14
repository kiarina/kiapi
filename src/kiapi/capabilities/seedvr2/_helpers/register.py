"""Register seedvr2's models + OpenAPI description in the global registries."""

from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import HfSnapshotResource

from .._constants.description import DESCRIPTION
from .._models import seedvr2
from .._settings import settings_manager


def register() -> None:
    capability_spec_registry.register(
        CapabilitySpec(
            name="seedvr2",
            domain="image",
            title="kiapi SeedVR2 API",
            summary="Upscale and restore images with SeedVR2.",
            description=DESCRIPTION,
            openapi_path="/v1/image/seedvr2/openapi.json",
            docs_path="/v1/image/seedvr2/docs",
            redoc_path="/v1/image/seedvr2/redoc",
            path_prefixes=("/v1/image/seedvr2",),
        )
    )

    _s = settings_manager.get_settings()

    model_registry.register(
        ModelSpec(
            name="3b",
            family="seedvr2",
            domain="image",
            repo=f"{_s.model_repo}#3b",
            module=seedvr2,
            weight_gb=2.7,
            peak_headroom_gb=1.5,
            framework="mlx",
            priority=0,
            aliases=("seedvr2-3b", "seedvr2"),
            default=True,
            setup_resources=(HfSnapshotResource(repo=_s.model_repo, disk_gb=7.3),),
        )
    )

    model_registry.register(
        ModelSpec(
            name="7b",
            family="seedvr2",
            domain="image",
            repo=f"{_s.model_repo}#7b",
            module=seedvr2,
            weight_gb=7.0,
            peak_headroom_gb=4.0,
            framework="mlx",
            priority=0,
            aliases=("seedvr2-7b", "seedvr2-7B"),
            setup_resources=(HfSnapshotResource(repo=_s.model_repo, disk_gb=17.0),),
        )
    )
