from fastapi import FastAPI
from kiarina.utils.app import configure

from kiapi.cli import register_all_capabilities


def create_app() -> FastAPI:
    """ASGI factory for uvicorn (used by hot reload).

    The reload subprocess re-imports the app fresh, so both the application
    identity and capability registration must run here rather than only in the
    `kiapi run` CLI.
    """
    configure("kiapi", "kiarina")
    register_all_capabilities()

    from kiapi.api.app import app

    return app
