"""Register h3's model + OpenAPI description in the global registries."""

from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import HfSnapshotResource, UrlFileResource

from .._constants.description import DESCRIPTION
from .._constants.variants import H3_VARIANT
from .._models import h3
from .._settings import settings_manager
from .mlx_serve_paths import mlx_serve_archive


def register() -> None:
    capability_spec_registry.register(
        CapabilitySpec(
            name="h3",
            domain="video",
            title="kiapi MiniMax H3 API",
            summary="Generate video with stereo audio from text and image, video, and audio references.",
            description=DESCRIPTION,
            openapi_path="/v1/video/h3/openapi.json",
            docs_path="/v1/video/h3/docs",
            redoc_path="/v1/video/h3/redoc",
            path_prefixes=("/v1/video/h3",),
        )
    )

    settings = settings_manager.get_settings()
    model_registry.register(
        ModelSpec(
            name=H3_VARIANT,
            family="h3",
            domain="video",
            repo=settings.model_repo,
            module=h3,
            weight_gb=0.0,  # transient: mlx-serve runs only for the job
            # 43 GB measured at 960x544 / 124 frames with a reference video; the
            # 1344x768 canvas has not been measured.
            peak_headroom_gb=50.0,
            framework="rss",
            priority=0,
            aliases=("h3", "minimax-h3"),
            default=True,
            resident=False,
            setup_resources=(
                UrlFileResource(
                    url=settings.mlx_serve_url,
                    path=str(mlx_serve_archive(settings)),
                    disk_gb=0.1,
                ),
                HfSnapshotResource(repo=settings.model_repo, disk_gb=69.3),
                HfSnapshotResource(
                    repo=settings.turbo_lora_repo,
                    allow_patterns=(settings.turbo_lora_file,),
                    disk_gb=2.0,
                ),
            ),
        )
    )
