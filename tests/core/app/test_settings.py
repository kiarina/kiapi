from kiapi.core.app import AppSettings


def test_app_settings_fields_have_titles_and_descriptions() -> None:
    fields = AppSettings.model_fields

    for name in ("user_cache_dir", "user_config_dir", "user_data_dir"):
        field = fields[name]

        assert field.title
        assert field.description
