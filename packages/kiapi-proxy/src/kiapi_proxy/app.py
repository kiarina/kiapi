from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.responses import Response

from kiapi_relay import relay_registry

from ._services.proxy_handler import handle_proxy_request
from ._settings import settings_manager

_RELAY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = settings_manager.get_settings()
    # Resolve the relay once at startup so a misconfiguration fails fast.
    app.state.relay = relay_registry.resolve(settings.relay)
    app.state.request_timeout_s = settings.request_timeout_s
    yield


def create_app() -> FastAPI:
    # Disable the built-in docs/openapi routes so every path is relayed to kiapi.
    app = FastAPI(
        title="kiapi-proxy",
        lifespan=lifespan,
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )

    async def proxy(request: Request, path: str) -> Response:
        return await handle_proxy_request(request)

    app.add_api_route("/{path:path}", proxy, methods=_RELAY_METHODS)
    return app


app = create_app()
