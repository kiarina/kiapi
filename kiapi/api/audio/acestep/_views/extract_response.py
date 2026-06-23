"""``/v1/audio/acestep/extract`` result payload (the Job ``result`` shape).

Mirrors the dict returned by ``capabilities/acestep/_operations/handle_extract``:
one job runs source separation for every requested target and collects one stem
per target. It is an output-side projection of the model result (not a
model-coupled view), so it lives under ``api/audio/acestep/_views``.

``ExtractResponse`` is the sole public element; nested pieces stay private.
"""

from typing import Any

from pydantic import BaseModel, Field


class _Timings(BaseModel):
    total_s: float = Field(
        description="Wall-clock separation time in seconds for this stem."
    )


class _Stem(BaseModel):
    target: str = Field(description="Stem name, e.g. vocals / drums / bass / other.")
    model: str = Field(description="Resolved preset that produced the stem.")
    src: str = Field(description="Files-API id of the source track.")

    file_id: str = Field(
        description=(
            "Files-API id of this stem's WAV. Fetch metadata at GET /v1/files/{id} "
            "or bytes at /download."
        )
    )
    audio_bytes: int = Field(description="Size of the stem WAV in bytes.")

    params: dict[str, Any] = Field(
        description="Resolved parameters used to separate this stem."
    )
    timings: _Timings = Field(description="kiapi extension: server-side timing.")


class ExtractResponse(BaseModel):
    """Capability-specific ``result`` for a succeeded extract job.

    A single job produces one stem per requested target; ``artifacts`` lists the
    same file_ids in ``stems`` order.
    """

    task: str = Field(description="Always `extract` for this endpoint.")
    source_file_id: str = Field(
        description="Files-API id of the source track that was separated."
    )
    targets: list[str] = Field(
        description="The requested stems, in the order they appear in `stems`."
    )
    stems: list[_Stem] = Field(
        description="One produced stem per target; each references its own WAV file_id."
    )
