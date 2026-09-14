from kiapi.core.file import FileSettings


def test_file_settings_default_files_root_is_tmp() -> None:
    settings = FileSettings()

    assert settings.files_root == "/tmp/kiapi/files"
