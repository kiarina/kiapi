from starlette.requests import HTTPConnection

from kiapi.core.app import AppContext


def get_ctx(request: HTTPConnection) -> AppContext:
    return request.app.state.ctx  # type: ignore
