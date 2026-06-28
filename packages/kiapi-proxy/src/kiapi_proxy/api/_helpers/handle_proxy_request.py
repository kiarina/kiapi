import logging

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from kiapi_relay import Relay, RelayRequestError

from .._operations.build_proxy_response import build_proxy_response
from .._operations.build_relay_request import build_relay_request

logger = logging.getLogger(__name__)


async def handle_proxy_request(request: Request) -> Response:
    """Forward an incoming HTTP request over the relay and return the result."""
    relay: Relay = request.app.state.relay
    timeout_s: float = request.app.state.request_timeout_s

    try:
        relay_request = await build_relay_request(request)
    except ValueError as exc:
        return JSONResponse(
            {"error": {"code": "invalid_request", "message": str(exc)}},
            status_code=400,
        )

    try:
        relay_response = await relay.request(relay_request, timeout_s=timeout_s)
    except RelayRequestError as exc:
        status = 504 if exc.error.retryable else 502
        return JSONResponse({"error": exc.error.model_dump()}, status_code=status)
    except TimeoutError as exc:
        return JSONResponse(
            {"error": {"code": "relay_timeout", "message": str(exc)}},
            status_code=504,
        )
    except Exception:
        logger.exception("Relay request failed")
        return JSONResponse(
            {
                "error": {
                    "code": "relay_internal_error",
                    "message": "relay request failed",
                }
            },
            status_code=502,
        )

    return build_proxy_response(relay_response)
