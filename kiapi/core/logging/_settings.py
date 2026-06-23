from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager

from ._types.log_level import LogLevel


class LoggingSettings(BaseSettings):
    """Settings for the global kiapi logging level."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_",
        extra="ignore",
    )

    log_level: LogLevel = Field(
        default="INFO",
        title="Log level",
        description=(
            "Verbosity of emitted logs.\n"
            "Standard Python logging levels such as DEBUG, INFO, WARNING, ERROR, "
            "and CRITICAL are accepted."
        ),
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def _to_upper(cls, v: str) -> str:
        if isinstance(v, str):
            return v.upper()
        return v  # type: ignore


settings_manager = SettingsManager(LoggingSettings)
