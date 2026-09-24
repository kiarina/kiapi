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
        default=1024,
        title="Default maximum generated tokens",
        description=(
            "Generation token limit used when a request omits max_completion_tokens.\n"
            "Generation also stops when the prompt plus the output fills the "
            "model's context window."
        ),
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

    apc_enabled: bool = Field(
        default=True,
        title="Enable automatic prefix caching",
        description=(
            "Reuse matching prompt prefixes between Qwen3.8 and "
            "Qwen3-Omni requests, including supported media inputs."
        ),
    )

    apc_num_blocks: int = Field(
        default=2048,
        ge=1,
        title="Automatic prefix cache blocks",
        description="Maximum number of in-memory APC blocks per loaded chat model.",
    )

    apc_block_size: int = Field(
        default=16,
        ge=1,
        title="Automatic prefix cache block size",
        description="Number of prompt tokens stored in each APC block.",
    )

    apc_memory_max_gb: float = Field(
        default=4.0,
        ge=0,
        title="Automatic prefix cache memory limit",
        description="Maximum estimated APC resident memory per loaded chat model in GiB.",
    )

    apc_tenant: str = Field(
        default="default",
        min_length=1,
        title="Automatic prefix cache tenant",
        description=(
            "Server-controlled isolation salt for prompt-prefix cache entries. "
            "Deployments serving separate trust domains must use separate values."
        ),
    )


settings_manager = SettingsManager(ChatSettings)
