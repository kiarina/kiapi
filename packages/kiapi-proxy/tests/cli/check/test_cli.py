import pytest
from click.testing import CliRunner
from kiarina.utils.app import AlreadyRunningError

from kiapi_proxy.cli.check import cli as check_cli
from kiapi_proxy.cli.cli import main
from kiapi_relay import (
    RelayError,
    RelayJsonBody,
    RelayRequest,
    RelayRequestError,
    RelayResponse,
)


class _FakeRelay:
    def __init__(
        self, response: RelayResponse | None = None, error: Exception | None = None
    ) -> None:
        self.name = "local"
        self.node_id = ""
        self._response = response
        self._error = error
        self.requests: list[RelayRequest] = []

    async def request(
        self,
        request: RelayRequest,
        *,
        timeout_s: float = 1800.0,
    ) -> RelayResponse:
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


def test_check_reports_healthy_response(monkeypatch: pytest.MonkeyPatch) -> None:
    response = RelayResponse(
        status=200,
        headers={"content-type": "application/json"},
        body=RelayJsonBody(value={"status": "ok"}),
    )
    fake = _FakeRelay(response=response)
    monkeypatch.setattr(
        check_cli.relay_registry,
        "resolve",
        lambda specifier: fake,
    )

    result = CliRunner().invoke(main, ["check", "--relay", "local", "--timeout", "5"])

    assert result.exit_code == 0
    assert "checking local relay -> /health" in result.output
    assert "[ok] HTTP 200" in result.output
    assert '{"status": "ok"}' in result.output
    assert fake.node_id != ""
    assert fake.requests[0].path == "/health"


def test_check_fails_when_proxy_already_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeRelay(
        response=RelayResponse(status=200, body=RelayJsonBody(value={"status": "ok"}))
    )
    monkeypatch.setattr(
        check_cli.relay_registry,
        "resolve",
        lambda specifier: fake,
    )

    def _already_running(*args: object, **kwargs: object) -> None:
        raise AlreadyRunningError("another kiapi-proxy instance is already running")

    monkeypatch.setattr(check_cli.single_instance, "acquire", _already_running)

    result = CliRunner().invoke(main, ["check", "--relay", "local"])

    assert result.exit_code != 0
    assert "already running" in result.output
    # The relay must not be contacted when the identity is already owned.
    assert fake.requests == []


def test_check_fails_when_no_live_node(monkeypatch: pytest.MonkeyPatch) -> None:
    error = RelayRequestError(
        RelayError(
            code="no_relay_node",
            message="no live kiapi relay node is available",
            retryable=True,
        )
    )
    fake = _FakeRelay(error=error)
    monkeypatch.setattr(
        check_cli.relay_registry,
        "resolve",
        lambda specifier: fake,
    )

    result = CliRunner().invoke(main, ["check", "--relay", "local"])

    assert result.exit_code != 0
    assert "no_relay_node" in result.output


def test_check_fails_on_error_status(monkeypatch: pytest.MonkeyPatch) -> None:
    response = RelayResponse(
        status=503,
        headers={"content-type": "application/json"},
        body=RelayJsonBody(value={"error": "unavailable"}),
    )
    fake = _FakeRelay(response=response)
    monkeypatch.setattr(
        check_cli.relay_registry,
        "resolve",
        lambda specifier: fake,
    )

    result = CliRunner().invoke(main, ["check", "--relay", "local"])

    assert result.exit_code != 0
    assert "HTTP 503" in result.output
