from kiapi.core.app import AppContext

from .._services.worker import Worker
from .._settings import settings_manager


def create_worker(ctx: AppContext) -> Worker:
    settings = settings_manager.get_settings()
    return Worker(settings, ctx)
