from dataclasses import dataclass

from kiapi.core.model import ModelSpec


@dataclass
class ResidentModel:
    spec: ModelSpec
    payload: object
    """Whatever the handler's ``load()`` returned (opaque to the manager)."""
    weight_gb: float
    """Resident footprint in GB — measured at load, else the spec estimate."""
    last_used: float
    """``time.monotonic()`` of the most recent acquire; drives LRU + idle TTL."""
