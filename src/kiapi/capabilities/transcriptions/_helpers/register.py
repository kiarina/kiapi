"""Register transcription's models + OpenAPI description in the global registries."""

from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import HfSnapshotResource

from .._constants.description import DESCRIPTION
from .._models import qwen3_asr


def register() -> None:
    capability_spec_registry.register(
        CapabilitySpec(
            name="transcriptions",
            domain="audio",
            title="kiapi Transcription API",
            summary="Transcribe audio to text (OpenAI-compatible audio/transcriptions).",
            description=DESCRIPTION,
            openapi_path="/v1/audio/transcriptions/openapi.json",
            docs_path="/v1/audio/transcriptions/docs",
            redoc_path="/v1/audio/transcriptions/redoc",
            path_prefixes=("/v1/audio/transcriptions",),
        )
    )

    model_registry.register(
        ModelSpec(
            name="qwen3-asr-1.7b",
            family="transcriptions",
            domain="audio",
            repo="mlx-community/Qwen3-ASR-1.7B-bf16",
            module=qwen3_asr,
            # The ASR model and the forced aligner; measured 5.5 GB after load.
            weight_gb=5.5,
            # Measured 2.3 GB over the weights for a 3-minute chunk.
            peak_headroom_gb=2.5,
            framework="mlx",
            priority=0,
            aliases=("qwen3-asr",),
            default=True,
            setup_resources=(
                HfSnapshotResource(
                    repo="mlx-community/Qwen3-ASR-1.7B-bf16", disk_gb=4.1
                ),
                HfSnapshotResource(repo=qwen3_asr.ALIGNER_REPO, disk_gb=1.8),
            ),
        )
    )
