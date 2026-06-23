from pathlib import Path
from typing import Any, cast

import yaml
from pydantic_settings_manager import UserConfig, UserConfigs, load_user_configs

from .._exceptions.user_config_error import UserConfigError
from .get_user_settings_path import get_user_settings_path


def load_user_settings(path: Path | None = None) -> None:
    settings_path = path or get_user_settings_path()
    if not settings_path.exists():
        return

    try:
        data = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise UserConfigError(f"Failed to read {settings_path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise UserConfigError(f"Failed to parse {settings_path}: {exc}") from exc

    if data is None:
        return

    if not isinstance(data, dict):
        raise UserConfigError(
            f"Settings file must contain a YAML mapping: {settings_path}"
        )

    user_configs = _normalize_user_configs(data, settings_path)

    try:
        load_user_configs(user_configs)
    except (ImportError, AttributeError, TypeError, ValueError) as exc:
        raise UserConfigError(f"Failed to load {settings_path}: {exc}") from exc


def _normalize_user_configs(data: dict[Any, Any], settings_path: Path) -> UserConfigs:
    user_configs: UserConfigs = {}

    for key, value in data.items():
        if not isinstance(key, str):
            raise UserConfigError(
                f"Settings file keys must be module names: {settings_path}"
            )
        if not isinstance(value, dict):
            raise UserConfigError(
                f"Configuration for module {key} must be a mapping: {settings_path}"
            )

        user_configs[key] = cast(UserConfig, value)

    return user_configs
