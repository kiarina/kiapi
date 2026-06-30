from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from .._views.relay_request import RelayRequest
from .._views.relay_response import RelayResponse
from .relay_delivery import RelayDelivery
from .relay_name import RelayName


@runtime_checkable
class Relay(Protocol):
    name: RelayName
    node_id: str

    def watch(self) -> AsyncIterator[RelayDelivery]: ...

    async def request(
        self,
        request: RelayRequest,
        *,
        timeout_s: float = 1800.0,
    ) -> RelayResponse: ...
