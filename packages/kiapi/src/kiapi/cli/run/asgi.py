from fastapi import FastAPI

from kiapi.cli import register_all_capabilities


def create_app() -> FastAPI:
    """ASGI factory for uvicorn (used by hot reload).

    The reload subprocess re-imports the app fresh, so capability
    registration must run here rather than only in the `kiapi run` CLI.
    """
    register_all_capabilities()

    from kiapi.api.app import app

    return app
