from typing import Protocol

from .setup_resource import SetupResource


class SetupTarget(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def setup_resources(self) -> tuple[SetupResource, ...]: ...
