from pydantic import BaseModel, Field


class ResidentModelStats(BaseModel):
    """Snapshot of one resident model held in the memory budget."""

    name: str = Field(..., description="Model variant name.", examples=["turbo"])
    family: str = Field(
        ...,
        description="Model family and API identifier.",
        examples=["zimage"],
    )
    domain: str = Field(
        ...,
        description="Capability domain such as chat, embedding, image, audio, video, or web.",
        examples=["image"],
    )
    repo: str = Field(
        ...,
        description="Upstream model repository, Docker image, or local resource label.",
        examples=["mflux/z-image-turbo"],
    )
    weight_gb: float = Field(
        ...,
        ge=0.0,
        description="Current resident weight estimate in GB.",
        examples=[6.0],
    )
    priority: int = Field(
        ...,
        description="Eviction priority. Lower values are evicted before higher values under budget pressure.",
        examples=[0],
    )
    idle_s: float = Field(
        ...,
        ge=0.0,
        description="Seconds since this resident model was last used.",
        examples=[12.5],
    )
    ttl_s: float | None = Field(
        default=None,
        description="Idle TTL in seconds. Null means the resident is pinned until budget pressure or shutdown.",
        examples=[1800.0],
    )
    expires_in_s: float | None = Field(
        default=None,
        description="Seconds until TTL eviction. Null when ttl_s is null.",
        examples=[1787.5],
    )
