from kiapi.core.workdir import WorkDirSettings


def test_work_dir_settings_default_tmp_root_is_under_tmp_kiapi() -> None:
    settings = WorkDirSettings()

    assert settings.tmp_root == "/tmp/kiapi/work"


def test_work_dir_settings_env_override(monkeypatch) -> None:  # type: ignore
    monkeypatch.setenv("KIAPI_TMP_ROOT", "/tmp/custom-kiapi-work")

    settings = WorkDirSettings()

    assert settings.tmp_root == "/tmp/custom-kiapi-work"
