from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class AppSettings(BaseSettings):
    """Settings for application-wide user directories."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_PROXY_",
        extra="ignore",
    )

    user_cache_dir: str | None = Field(
        default=None,
        title="User cache directory",
        description=(
            "Directory where kiapi-proxy may store user-specific cache files.\n"
            "When unset, XDG_CACHE_HOME is used when available, otherwise the "
            "platform default for the running user is used.\n"
            "~ is expanded as the home directory of the running user."
        ),
    )
    user_config_dir: str | None = Field(
        default=None,
        title="User config directory",
        description=(
            "Directory where kiapi-proxy may store user-specific configuration "
            "files.\n"
            "When unset, XDG_CONFIG_HOME is used when available, otherwise the "
            "platform default for the running user is used.\n"
            "~ is expanded as the home directory of the running user."
        ),
    )
    user_data_dir: str | None = Field(
        default=None,
        title="User data directory",
        description=(
            "Directory where kiapi-proxy may store user-specific persistent data "
            "files.\n"
            "When unset, XDG_DATA_HOME is used when available, otherwise the "
            "platform default for the running user is used.\n"
            "~ is expanded as the home directory of the running user."
        ),
    )


settings_manager = SettingsManager(AppSettings)
