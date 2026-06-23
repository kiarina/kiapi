"""Sound-effect capability defaults, read from the environment (``KIAPI_AUDIOGEN_``)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class AudiogenSettings(BaseSettings):
    """Settings for AudioGen sound-effect duration defaults and limits."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_AUDIOGEN_",
        extra="ignore",
        protected_namespaces=(),
    )

    max_duration: float = Field(
        default=10.0,
        title="Maximum generation seconds",
        description=(
            "Maximum sound-effect duration in seconds accepted in a request.\n"
            "AudioGen medium is naturally limited to about 10 seconds, and this "
            "also protects the worker."
        ),
    )

    default_duration: float = Field(
        default=5.0,
        title="Default generation seconds",
        description="Sound-effect duration in seconds used when a request omits duration.",
    )


settings_manager = SettingsManager(AudiogenSettings)
