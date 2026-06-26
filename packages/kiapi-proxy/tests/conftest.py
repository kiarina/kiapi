from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

import kiapi_relay
from kiapi_proxy.app import create_app
from kiapi_relay import RelayRequest, RelayResponse


class FakeRelay:
    """A relay stub that records the request and returns a canned response."""

    def __init__(self, response: RelayResponse) -> None:
        self.response = response
        self.received: RelayRequest | None = None

    async def request(
        self, request: RelayRequest, *, timeout_s: float = 1800.0
    ) -> RelayResponse:
        self.received = request
        return self.response


@pytest.fixture
def make_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[object]:
    """Return a factory that builds a TestClient wired to a FakeRelay."""
    created: list[FakeRelay] = []

    def factory(response: RelayResponse) -> tuple[TestClient, FakeRelay]:
        fake = FakeRelay(response)
        monkeypatch.setattr(
            kiapi_relay.relay_registry,
            "resolve",
            lambda component_input=None: fake,
        )
        created.append(fake)
        return TestClient(create_app()), fake

    yield factory
