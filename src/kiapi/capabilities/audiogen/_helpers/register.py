"""Register audiogen's models + OpenAPI description in the global registries."""

from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import HfSnapshotResource

from .._constants.description import DESCRIPTION
from .._models import audiogen


def register() -> None:
    capability_spec_registry.register(
        CapabilitySpec(
            name="audiogen",
            domain="audio",
            title="kiapi AudioGen API",
            summary="Generate short sound effects from text prompts.",
            description=DESCRIPTION,
            openapi_path="/v1/audio/audiogen/openapi.json",
            docs_path="/v1/audio/audiogen/docs",
            redoc_path="/v1/audio/audiogen/redoc",
            path_prefixes=("/v1/audio/audiogen",),
        )
    )

    model_registry.register(
        ModelSpec(
            name="medium",
            family="audiogen",
            domain="audio",
            repo="facebook/audiogen-medium",
            module=audiogen,
            weight_gb=7.1,  # measured on device (model card weights ~3.6 GB)
            peak_headroom_gb=2.0,
            framework="mlx",
            priority=0,
            default=True,
            setup_resources=(
                HfSnapshotResource(repo="facebook/audiogen-medium", disk_gb=3.6),
            ),
        )
    )
