"""Register speech's models + OpenAPI description in the global registries."""

from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import HfSnapshotResource

from .._constants.description import DESCRIPTION
from .._models import qwen3_tts


def register() -> None:
    capability_spec_registry.register(
        CapabilitySpec(
            name="speech",
            domain="audio",
            title="kiapi Speech API",
            summary="Speak text in a registered voice (OpenAI-compatible audio/speech).",
            description=DESCRIPTION,
            openapi_path="/v1/audio/speech/openapi.json",
            docs_path="/v1/audio/speech/docs",
            redoc_path="/v1/audio/speech/redoc",
            path_prefixes=("/v1/audio/speech", "/v1/audio/voices"),
        )
    )

    model_registry.register(
        ModelSpec(
            name="qwen3-tts-1.7b",
            family="speech",
            domain="audio",
            repo="mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16",
            module=qwen3_tts,
            weight_gb=4.6,  # measured: 4.57 GB resident after load
            # Generation adds ~0.6 GB streaming and ~4.1 GB for a whole WAV.
            peak_headroom_gb=4.5,
            framework="mlx",
            priority=0,
            aliases=("qwen3-tts",),
            default=True,
            setup_resources=(
                HfSnapshotResource(
                    repo="mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16", disk_gb=4.5
                ),
            ),
        )
    )
