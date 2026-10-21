from fastapi import Depends, HTTPException
from starlette.requests import HTTPConnection

from .._settings import settings_manager


async def _require_auth(request: HTTPConnection) -> None:
    settings = settings_manager.get_settings()
    token = settings.auth_token

    if (
        token
        and request.headers.get("authorization") != f"Bearer {token.get_secret_value()}"
    ):
        raise HTTPException(status_code=401, detail="unauthorized")


REQUIRE_AUTH = [Depends(_require_auth)]
