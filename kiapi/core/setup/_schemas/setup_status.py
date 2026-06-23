from dataclasses import dataclass


@dataclass(frozen=True)
class SetupStatus:
    ready: bool
    detail: str
