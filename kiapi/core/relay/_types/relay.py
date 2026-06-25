from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from .relay_delivery import RelayDelivery


@runtime_checkable
class Relay(Protocol):
    def watch(self) -> AsyncIterator[RelayDelivery]: ...

    async def close(self) -> None: ...
