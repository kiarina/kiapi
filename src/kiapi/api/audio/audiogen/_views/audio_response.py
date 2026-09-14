"""``/v1/audio/audiogen/generate`` result payload (the Job ``result``).

Mirrors the dict returned by ``capabilities/audiogen/_models/audiogen.run`` so the
produced WAV is self-describing in OpenAPI. It is an output-side projection of
the model result, so it lives under ``api/audio/audiogen/_views``.

``AudioResponse`` is the sole public element; nested pieces stay private.
"""

from typing import Any

from pydantic import BaseModel, Field


class _Timings(BaseModel):
    total_s: float = Field(description="Wall-clock generation time in seconds.")


class AudioResponse(BaseModel):
    """Capability-specific ``result`` for a succeeded AudioGen generate job."""

    file_id: str = Field(
        description=(
            "Files-API id of the produced WAV. Fetch metadata at GET /v1/files/{id} "
            "or bytes at /download. This is also the artifact returned as raw bytes "
            "by a single-artifact sync call."
        )
    )
    audio_bytes: int = Field(description="Size of the produced WAV in bytes.")

    model: str = Field(description="Resolved AudioGen variant that produced the WAV.")
    prompt: str = Field(description="Prompt used to generate the sound effect.")
    duration_s: float = Field(
        description="Actual WAV duration in seconds, measured from the output samples."
    )
    sample_rate: int = Field(
        description="Output sample rate in Hz. AudioGen-medium produces 16 kHz mono WAV."
    )

    params: dict[str, Any] = Field(
        description=(
            "Resolved parameters actually used for the run (model, prompt, duration, "
            "seed, top_k, top_p, temperature, cfg_coef), so the result is reproducible."
        )
    )
    timings: _Timings = Field(description="kiapi extension: server-side timing.")
