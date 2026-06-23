"""LTX-2 capability defaults + caps, read from ``KIAPI_LTX2_`` env vars."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class LTX2Settings(BaseSettings):
    """Settings for LTX-2 models, video dimensions, frame counts, and progress display."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_LTX2_",
        extra="ignore",
        protected_namespaces=(),
    )

    model_repo: str = Field(
        default="prince-canuma/LTX-2-distilled",
        title="LTX-2 model repo",
        description="Hugging Face repo ID for the LTX-2 model used for video generation.",
    )

    text_encoder_repo: str | None = Field(
        default=None,
        title="Text encoder repo",
        description=(
            "Hugging Face repo ID for a text encoder from a separate repo.\n"
            "When None, the model's default text encoder is used."
        ),
    )

    # --------------------------------------------------
    # generate
    # --------------------------------------------------

    max_num_frames: int = Field(
        default=721,
        title="Maximum frame count",
        description="Upper limit for the video frame count accepted in a request.",
    )

    max_width: int = Field(
        default=768,
        title="Maximum width",
        description="Upper pixel limit for the video width accepted in a request.",
    )

    max_height: int = Field(
        default=768,
        title="Maximum height",
        description="Upper pixel limit for the video height accepted in a request.",
    )

    default_width: int = Field(
        default=512,
        title="Default width",
        description="Video width in pixels used when a request omits width.",
    )

    default_height: int = Field(
        default=512,
        title="Default height",
        description="Video height in pixels used when a request omits height.",
    )

    default_num_frames: int = Field(
        default=97,
        title="Default frame count",
        description="Generated frame count used when a request omits num_frames.",
    )

    default_fps: int = Field(
        default=24,
        title="Default FPS",
        description="Output video FPS used when a request omits fps.",
    )

    # mlx-video exposes no per-step hook, so we creep a synthetic 'liveness'
    # progress on a time-based schedule while it runs (keeps polling agents
    # waiting); the schedule is paced to hit ~80% at this expected duration. Base
    # seconds for a 97-frame 512x512 job; scaled by frame count and resolution.
    # 0 disables the creep (progress stays at the coarse 0.0 until completion).
    progress_eta_base_s: float = Field(
        default=90.0,
        title="Progress ETA base seconds",
        description=(
            "Expected seconds for synthetic progress, based on a 97-frame 512x512 LTX-2 job.\n"
            "The value is scaled by frame count and resolution. Set to 0 to disable it."
        ),
    )


settings_manager = SettingsManager(LTX2Settings)
