from collections.abc import Iterator
from pathlib import Path

import pytest

from kiapi.api import settings_manager as api_settings_manager
from kiapi.core.config import load_user_settings
from kiapi.core.config._exceptions.user_config_error import UserConfigError


@pytest.fixture(autouse=True)
def reset_api_settings() -> Iterator[None]:
    api_settings_manager.reset_user_config()
    yield
    api_settings_manager.reset_user_config()


def test_load_user_settings_loads_yaml_into_settings_manager(tmp_path: Path) -> None:
    path = tmp_path / "settings.yaml"
    path.write_text("kiapi.api:\n  port: 9000\n", encoding="utf-8")

    load_user_settings(path)

    assert api_settings_manager.get_settings().port == 9000


def test_load_user_settings_ignores_missing_file(tmp_path: Path) -> None:
    load_user_settings(tmp_path / "settings.yaml")

    assert api_settings_manager.user_config == {}


def test_load_user_settings_warns_for_missing_modules(tmp_path: Path) -> None:
    path = tmp_path / "settings.yaml"
    path.write_text("kiapi.missing:\n  value: nope\n", encoding="utf-8")

    with pytest.warns(UserWarning, match="kiapi.missing"):
        load_user_settings(path)


def test_load_user_settings_rejects_non_mapping_yaml(tmp_path: Path) -> None:
    path = tmp_path / "settings.yaml"
    path.write_text("- nope\n", encoding="utf-8")

    with pytest.raises(UserConfigError, match="YAML mapping"):
        load_user_settings(path)


def test_load_user_settings_rejects_non_mapping_module_config(tmp_path: Path) -> None:
    path = tmp_path / "settings.yaml"
    path.write_text("kiapi.api: nope\n", encoding="utf-8")

    with pytest.raises(UserConfigError, match="must be a mapping"):
        load_user_settings(path)
