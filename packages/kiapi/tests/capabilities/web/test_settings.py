from kiapi.capabilities.web._settings import WebSettings


def test_web_settings_default_backend_log_dir_is_under_tmp_kiapi() -> None:
    settings = WebSettings()

    assert settings.backend_log_dir == "/tmp/kiapi/logs/web"
