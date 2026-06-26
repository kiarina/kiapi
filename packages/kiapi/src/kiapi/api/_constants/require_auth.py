from fastapi import Depends, HTTPException, Request

from .._settings import settings_manager


async def _require_auth(request: Request) -> None:
    settings = settings_manager.get_settings()
    token = settings.auth_token

    if token and request.headers.get("authorization") != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="unauthorized")


REQUIRE_AUTH = [Depends(_require_auth)]
