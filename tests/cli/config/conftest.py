from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def reset_app_settings() -> Iterator[None]:
    from kiapi.core.app import settings_manager

    settings_manager.reset_user_config()
    yield
    settings_manager.reset_user_config()
