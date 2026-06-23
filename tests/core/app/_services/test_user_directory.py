import os
from collections.abc import Iterator

import pytest

from kiapi.core.app._services import user_directory
from kiapi.core.app._settings import settings_manager


@pytest.fixture(autouse=True)
def reset_app_settings() -> Iterator[None]:
    settings_manager.reset_user_config()
    yield
    settings_manager.reset_user_config()


def test_get_user_cache_dir_uses_setting() -> None:
    settings_manager.user_config = {"user_cache_dir": "~/Library/Caches/custom-kiapi"}

    assert user_directory.get_user_cache_dir() == os.path.expanduser(
        "~/Library/Caches/custom-kiapi"
    )


def test_get_user_config_dir_uses_xdg_when_setting_is_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/xdg-config")

    assert user_directory.get_user_config_dir() == "/tmp/xdg-config/kiapi"


def test_get_user_data_dir_uses_platformdirs_when_setting_and_xdg_are_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakePlatformDirs:
        def __init__(self, *, appname: str, appauthor: str) -> None:
            self.appname = appname
            self.appauthor = appauthor
            self.user_data_dir = f"/platform/{appauthor}/{appname}/data"

    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(user_directory, "PlatformDirs", FakePlatformDirs)

    assert user_directory.get_user_data_dir() == "/platform/kiarina/kiapi/data"
