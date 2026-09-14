"""Register ltx2's models + OpenAPI description in the global registries."""

from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import HfSnapshotResource, PythonPackageResource

from .._constants.description import DESCRIPTION
from .._models import ltx2
from .._settings import settings_manager

MLX_VIDEO_SPEC = (
    "mlx-video @ git+https://github.com/Blaizzy/mlx-video.git"
    "@87db56a51758fefb748a359b90a5283bb8ba4837"
)


def register() -> None:
    capability_spec_registry.register(
        CapabilitySpec(
            name="ltx2",
            domain="video",
            title="kiapi LTX-2 API",
            summary="Generate video from text, image, and music or audio inputs.",
            description=DESCRIPTION,
            openapi_path="/v1/video/ltx2/openapi.json",
            docs_path="/v1/video/ltx2/docs",
            redoc_path="/v1/video/ltx2/redoc",
            path_prefixes=("/v1/video/ltx2",),
        )
    )

    settings = settings_manager.get_settings()

    model_registry.register(
        ModelSpec(
            name="distilled",
            family="ltx2",
            domain="video",
            repo=settings.model_repo,
            module=ltx2,
            weight_gb=0.0,  # transient: not held resident
            peak_headroom_gb=40.0,  # transient peak to reserve; reconciled on device
            framework="mlx",
            priority=0,
            default=True,
            resident=False,
            setup_resources=(
                PythonPackageResource(
                    package="mlx-video",
                    spec=MLX_VIDEO_SPEC,
                    import_name="mlx_video.models.ltx_2.generate",
                    verify_attrs=("PipelineType", "generate_video"),
                    label_name="mlx-video-ltx2",
                ),
                HfSnapshotResource(repo=settings.model_repo, disk_gb=101.0),
            ),
        )
    )
