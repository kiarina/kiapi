"""Register ideogram4's models + OpenAPI description in the global registries."""

from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import HfSnapshotResource

from .._constants.description import DESCRIPTION
from .._models import ideogram4
from .._settings import settings_manager


def register() -> None:
    capability_spec_registry.register(
        CapabilitySpec(
            name="ideogram4",
            domain="image",
            title="kiapi Ideogram 4 API",
            summary="Generate images from text prompts with Ideogram 4.",
            description=DESCRIPTION,
            openapi_path="/v1/image/ideogram4/openapi.json",
            docs_path="/v1/image/ideogram4/docs",
            redoc_path="/v1/image/ideogram4/redoc",
            path_prefixes=("/v1/image/ideogram4",),
        )
    )

    _s = settings_manager.get_settings()

    model_registry.register(
        ModelSpec(
            name="fp8",
            family="ideogram4",
            domain="image",
            repo=_s.model_repo,
            module=ideogram4,
            weight_gb=26.0,
            peak_headroom_gb=4.0,
            framework="mlx",
            priority=0,
            aliases=("ideogram4", "ideogram-4", "ideogram-ai/ideogram-4-fp8"),
            default=True,
            setup_resources=(HfSnapshotResource(repo=_s.model_repo, disk_gb=27.5),),
        )
    )
