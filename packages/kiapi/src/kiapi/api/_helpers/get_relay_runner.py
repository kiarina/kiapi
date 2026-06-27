from fastapi import Request

from kiapi_relay import RelayRunner


def get_relay_runner(request: Request) -> RelayRunner | None:
    return getattr(request.app.state, "relay_runner", None)
