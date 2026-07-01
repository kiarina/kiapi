from pathlib import Path

import pytest

from kiapi.core.config import get_user_settings_path


def test_get_user_settings_path_uses_user_config_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("KIARINA_UTILS_APP_USER_CONFIG_DIR", str(tmp_path / "config"))

    assert get_user_settings_path() == tmp_path / "config" / "settings.yaml"
