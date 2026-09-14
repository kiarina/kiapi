from pydantic import BaseModel, Field

from .resident_model_stats import ResidentModelStats


class MemoryStats(BaseModel):
    """Resident model memory budget snapshot, served by ``/health``."""

    loaded: list[ResidentModelStats] = Field(
        default_factory=list,
        description="Resident models currently held in memory.",
    )
    resident_gb: float = Field(
        ...,
        ge=0.0,
        description="Total resident model weight currently counted against the budget.",
        examples=[12.0],
    )
    budget_gb: float = Field(
        ...,
        gt=0.0,
        description="Effective global memory budget in GB shared by all resident models and the running job's peak headroom.",
        examples=[100.0],
    )
