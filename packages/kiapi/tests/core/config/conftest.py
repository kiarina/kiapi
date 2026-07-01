from collections.abc import Iterator

import pytest
from kiarina.utils.app import settings_manager as app_settings_manager


@pytest.fixture(autouse=True)
def reset_app_settings() -> Iterator[None]:
    app_settings_manager.reset_user_config()
    yield
    app_settings_manager.reset_user_config()
