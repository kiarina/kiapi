from fastapi import Request

from kiapi.core.app import AppContext


def get_ctx(request: Request) -> AppContext:
    return request.app.state.ctx  # type: ignore
