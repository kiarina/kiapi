"""Register flux2's models + OpenAPI description in the global registries."""

from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import HfSnapshotResource

from .._constants.description import DESCRIPTION
from .._models import flux2
from .._settings import settings_manager


def register() -> None:
    capability_spec_registry.register(
        CapabilitySpec(
            name="flux2",
            domain="image",
            title="kiapi FLUX.2 API",
            summary="Generate, edit, and train LoRA adapters for FLUX.2 image models.",
            description=DESCRIPTION,
            openapi_path="/v1/image/flux2/openapi.json",
            docs_path="/v1/image/flux2/docs",
            redoc_path="/v1/image/flux2/redoc",
            path_prefixes=("/v1/image/flux2",),
        )
    )

    _s = settings_manager.get_settings()
    setup_repos = {
        "flux2-klein-9b": "black-forest-labs/FLUX.2-klein-9B",
        "flux2-klein-base-4b": "black-forest-labs/FLUX.2-klein-base-4B",
        "flux2-klein-base-9b": "black-forest-labs/FLUX.2-klein-base-9B",
    }

    model_registry.register(
        ModelSpec(
            name="klein-9b",
            family="flux2",
            domain="image",
            repo=_s.klein_9b_model,
            module=flux2,
            weight_gb=29.0,  # measured peak RSS ~28.99 GiB for 512 text/img2img
            peak_headroom_gb=4.0,  # edit measured ~31.6 GiB; keep margin for larger inputs
            framework="mlx",
            priority=0,
            aliases=("flux2-klein-9b", "black-forest-labs/FLUX.2-klein-9B"),
            default=True,
            setup_resources=(
                HfSnapshotResource(
                    repo=setup_repos.get(_s.klein_9b_model, _s.klein_9b_model),
                    disk_gb=52.9,
                ),
            ),
        )
    )
    model_registry.register(
        ModelSpec(
            name="klein-base-4b",
            family="flux2",
            domain="image",
            repo=_s.klein_base_4b_model,
            module=flux2,
            weight_gb=9.5,  # measured peak RSS ~9.1 GiB, q8, 512 text, 40 steps
            peak_headroom_gb=3.0,
            framework="mlx",
            priority=0,
            aliases=("flux2-klein-base-4b", "black-forest-labs/FLUX.2-klein-base-4B"),
            setup_resources=(
                HfSnapshotResource(
                    repo=setup_repos.get(
                        _s.klein_base_4b_model, _s.klein_base_4b_model
                    ),
                    disk_gb=23.7,
                ),
            ),
        )
    )
    model_registry.register(
        ModelSpec(
            name="klein-base-9b",
            family="flux2",
            domain="image",
            repo=_s.klein_base_9b_model,
            module=flux2,
            weight_gb=18.0,  # measured peak RSS ~16.8 GiB, q8, 512 text, 40 steps
            peak_headroom_gb=4.0,
            framework="mlx",
            priority=0,
            aliases=("flux2-klein-base-9b", "black-forest-labs/FLUX.2-klein-base-9B"),
            setup_resources=(
                HfSnapshotResource(
                    repo=setup_repos.get(
                        _s.klein_base_9b_model, _s.klein_base_9b_model
                    ),
                    disk_gb=52.9,
                ),
            ),
        )
    )
