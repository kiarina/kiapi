from typing import Protocol, runtime_checkable

from .._views.relay_error import RelayError
from .._views.relay_request import RelayRequest
from .._views.relay_response import RelayResponse


@runtime_checkable
class RelayDelivery(Protocol):
    @property
    def request(self) -> RelayRequest: ...

    async def start(self) -> None: ...

    async def complete(self, response: RelayResponse) -> None: ...

    async def fail(self, error: RelayError) -> None: ...
