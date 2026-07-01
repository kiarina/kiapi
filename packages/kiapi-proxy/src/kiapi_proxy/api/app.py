from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from kiarina.utils.app import single_instance, user_directory
from starlette.responses import Response

from kiapi_relay import get_or_create_node_id, relay_registry

from ._helpers.handle_proxy_request import handle_proxy_request
from ._settings import settings_manager

_RELAY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = settings_manager.get_settings()

    # Prevent a second kiapi-proxy from sharing this node identity, then resolve
    # the persistent node ID used to address relayed responses back to us.
    single_instance.acquire()
    data_dir = user_directory.get_user_data_dir()
    node_id = get_or_create_node_id(data_dir)

    # Resolve the relay once at startup so a misconfiguration fails fast.
    relay = relay_registry.resolve(settings.relay)
    relay.node_id = node_id
    app.state.relay = relay
    app.state.request_timeout_s = settings.request_timeout_s
    try:
        yield
    finally:
        single_instance.release()


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
