"""Register ltx2's models + OpenAPI description in the global registries."""

from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import HfSnapshotResource, PythonPackageResource

from .._constants.description import DESCRIPTION
from .._constants.variants import LTX2_VARIANT, LTX25_VARIANT
from .._models import ltx2, ltx25
from .._settings import settings_manager

# LTX-2.5 support is still under review upstream (Blaizzy/mlx-video#52), so this
# pins the PR head through a fork branch that is never force-pushed.
MLX_VIDEO_SPEC = (
    "mlx-video @ git+https://github.com/kiarina/mlx-video.git"
    "@cbb2c10f2a25305b0bf09169ab6b865ab86e3332"
)

# The upstream repo also holds dev and diffusers weights; fetch only what the
# distilled / DFR pipelines load.
LTX25_FILES = (
    "diffusion_models/ltx-2.5-22b-distilled-transformer-bf16.safetensors",
    "text_encoders/gemma4-12b-with-proj-ltx-2.5-bf16.safetensors",
    "vae/ltx-2.5-video-vae-conv-bf16.safetensors",
    "vae/ltx-2.5-video-vae-bf16.safetensors",
    "vae/ltx-2.5-audio-vae-bf16.safetensors",
    "latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors",
    "model_patches/ltx-2.5-duration-head-bf16.safetensors",
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
    mlx_video = PythonPackageResource(
        package="mlx-video",
        spec=MLX_VIDEO_SPEC,
        import_name="mlx_video.models.ltx_2.generate",
        # LTX25_MODEL_REPO makes an older mlx-video install read as not ready,
        # so `kiapi activate` replaces it.
        verify_attrs=("PipelineType", "generate_video", "LTX25_MODEL_REPO"),
        label_name="mlx-video-ltx2",
    )

    model_registry.register(
        ModelSpec(
            name=LTX25_VARIANT,
            family="ltx2",
            domain="video",
            repo=settings.ltx25_model_repo,
            module=ltx25,
            weight_gb=0.0,  # transient: not held resident
            peak_headroom_gb=44.0,  # DFR peak 41.25 GB; reconciled on device
            framework="mlx",
            priority=0,
            default=True,
            resident=False,
            setup_resources=(
                mlx_video,
                HfSnapshotResource(
                    repo=settings.ltx25_model_repo,
                    allow_patterns=LTX25_FILES,
                    disk_gb=72.6,
                ),
                HfSnapshotResource(repo=settings.prompt_enhancer_repo, disk_gb=10.2),
                HfSnapshotResource(
                    repo=settings.detailing_lora_repo,
                    allow_patterns=("*.safetensors",),
                    disk_gb=0.3,
                ),
            ),
        )
    )

    model_registry.register(
        ModelSpec(
            name=LTX2_VARIANT,
            family="ltx2",
            domain="video",
            repo=settings.model_repo,
            module=ltx2,
            weight_gb=0.0,  # transient: not held resident
            peak_headroom_gb=40.0,  # transient peak to reserve; reconciled on device
            framework="mlx",
            priority=0,
            resident=False,
            setup_resources=(
                mlx_video,
                HfSnapshotResource(repo=settings.model_repo, disk_gb=101.0),
            ),
        )
    )
