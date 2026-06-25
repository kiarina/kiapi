from typing import TYPE_CHECKING

from kiapi.core.relay import RelayError, RelayRequest, RelayResponse

from .._schemas.gcp_relay_notification import GCPRelayNotification

if TYPE_CHECKING:
    from .gcp_relay import GCPRelay


class GCPRelayDelivery:
    def __init__(
        self,
        relay: "GCPRelay",
        notification: GCPRelayNotification,
        request: RelayRequest,
    ) -> None:
        self._relay = relay
        self._notification = notification
        self._request = request
        self._finished = False

    @property
    def request(self) -> RelayRequest:
        return self._request

    async def start(self) -> None:
        await self._relay.mark_running(self._notification)

    async def complete(self, response: RelayResponse) -> None:
        if self._finished:
            return
        self._finished = True
        await self._relay.complete(self._notification, response)

    async def fail(self, error: RelayError) -> None:
        if self._finished:
            return
        self._finished = True
        await self._relay.fail(self._notification, error)
