"""Chat-capability generation defaults, read from the environment (``KIAPI_CHAT_``).

Separate from the global infra settings: each capability owns its own knobs. A
request may override these per call.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class ChatSettings(BaseSettings):
    """Settings for Chat Completions generation defaults and input-processing limits."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_CHAT_",
        extra="ignore",
        protected_namespaces=(),
    )

    default_max_tokens: int = Field(
        default=512,
        title="Default maximum generated tokens",
        description="Generation token limit used when a request omits max_tokens.",
    )

    default_temperature: float = Field(
        default=0.7,
        title="Default temperature",
        description=(
            "Sampling temperature used when a request omits temperature.\n"
            "Lower values are more stable; higher values are more diverse."
        ),
    )

    default_top_p: float = Field(
        default=1.0,
        title="Default top_p",
        description=(
            "Nucleus sampling threshold used when a request omits top_p.\n"
            "Use a value greater than 0 and less than or equal to 1.0."
        ),
    )

    default_fps: float = Field(
        default=1.0,
        title="Default video input sampling FPS",
        description=(
            "Default FPS for extracting frames from video input before passing them to the model.\n"
            "Higher values provide finer video understanding, but increase "
            "processing time and input size."
        ),
    )

    use_audio_in_video: bool = Field(
        default=True,
        title="Use audio in video",
        description=(
            "When true, audio tracks in video files are demuxed and passed to "
            "the model as audio input."
        ),
    )

    max_tokens_cap: int = Field(
        default=4096,
        title="Maximum generated token cap",
        description=(
            "Server-side upper limit for max_tokens accepted in a request.\n"
            "This protects the single worker queue from being blocked for a long time."
        ),
    )


settings_manager = SettingsManager(ChatSettings)
