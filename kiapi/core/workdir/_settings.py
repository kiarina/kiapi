from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class WorkDirSettings(BaseSettings):
    """Settings for per-request temporary work directories."""

    model_config = SettingsConfigDict(env_prefix="KIAPI_")

    tmp_root: str = Field(
        default="/tmp/kiapi/work",
        title="Temporary work directory root",
        description=(
            "Root directory for temporary work files created while handling requests.\n"
            "Each operation creates a purpose-specific child directory under this root."
        ),
    )


settings_manager = SettingsManager(WorkDirSettings)
