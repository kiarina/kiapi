from fastapi import FastAPI
from kiarina.utils.app import configure

from kiapi.cli import register_all_capabilities
from kiapi.core.config import load_user_settings


def create_app() -> FastAPI:
    configure("kiapi", "kiarina")
    load_user_settings()
    register_all_capabilities()

    from kiapi.api.app import app

    return app
