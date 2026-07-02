from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._constants.require_auth import REQUIRE_AUTH
    from ._helpers.build_job_responses import build_job_responses
    from ._helpers.build_openapi import build_openapi
    from ._helpers.build_train_responses import build_train_responses
    from ._helpers.get_accept import get_accept
    from ._helpers.get_ctx import get_ctx
    from ._helpers.get_relay_runner import get_relay_runner
    from ._helpers.get_worker import get_worker
    from ._helpers.register_capability_endpoints import register_capability_endpoints
    from ._helpers.submit_and_maybe_wait import submit_and_maybe_wait
    from ._settings import settings_manager

__all__ = [
    "REQUIRE_AUTH",
    "build_job_responses",
    "build_openapi",
    "build_train_responses",
    "get_accept",
    "get_ctx",
    "get_relay_runner",
    "get_worker",
    "register_capability_endpoints",
    "settings_manager",
    "submit_and_maybe_wait",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "REQUIRE_AUTH": "._constants.require_auth",
        "build_job_responses": "._helpers.build_job_responses",
        "build_openapi": "._helpers.build_openapi",
        "build_train_responses": "._helpers.build_train_responses",
        "get_accept": "._helpers.get_accept",
        "get_ctx": "._helpers.get_ctx",
        "get_relay_runner": "._helpers.get_relay_runner",
        "get_worker": "._helpers.get_worker",
        "register_capability_endpoints": "._helpers.register_capability_endpoints",
        "settings_manager": "._settings",
        "submit_and_maybe_wait": "._helpers.submit_and_maybe_wait",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
