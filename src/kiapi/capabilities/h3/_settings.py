"""MiniMax H3 capability defaults + caps, read from ``KIAPI_H3_`` env vars."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class H3Settings(BaseSettings):
    """Settings for MiniMax H3 weights, the mlx-serve engine, and request limits."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_H3_",
        extra="ignore",
        protected_namespaces=(),
    )

    model_repo: str = Field(
        default="ddalcu/MiniMax-H3-REF2VA-MLX-Serve-8bit",
        title="Model repo",
        description="Hugging Face repo ID for the 8-bit Ref2VA pack that mlx-serve loads.",
    )

    turbo_lora_repo: str = Field(
        default="lightx2v/Minimax-h3-Turbo",
        title="Turbo LoRA repo",
        description="Hugging Face repo ID holding the Ref2VA Turbo LoRA.",
    )

    turbo_lora_file: str = Field(
        default="minimax_h3_ref2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors",
        title="Turbo LoRA file",
        description=(
            "Turbo LoRA file in the repo. Use the ComfyUI layout: mlx-serve does not "
            "match the diffusers layout's module names."
        ),
    )

    mlx_serve_url: str = Field(
        default=(
            "https://github.com/ddalcu/mlx-serve/releases/download/v26.10.1/"
            "mlx-serve-bin-macos-arm64.tar.gz"
        ),
        title="mlx-serve release URL",
        description="Release archive of the mlx-serve binary that runs MiniMax H3.",
    )

    mlx_serve_version: str = Field(
        default="26.10.1",
        title="mlx-serve version",
        description="Version label of `mlx_serve_url`; names the local install directory.",
    )

    prompt_guide_base_url: str = Field(
        default=(
            "https://raw.githubusercontent.com/MiniMax-AI/MiniMax-H3/"
            "d21241f0a4b3acbb34c97dae47fa417b7065e438/skills/h3-prompt-writing/"
            "references/"
        ),
        title="Prompt guide base URL",
        description=(
            "Directory URL of MiniMax's prompt guides (`base-en.txt` for text only, "
            "`ref-en.txt` for references) that `enhance_prompt` gives the chat model."
        ),
    )

    enhance_model: str = Field(
        default="qwen3.8-27b",
        title="Prompt rewrite model",
        description="kiapi chat model that rewrites prompts for `enhance_prompt`.",
    )

    enhance_max_tokens: int = Field(
        default=3000,
        title="Prompt rewrite max tokens",
        description="Maximum tokens the chat model may generate for one rewrite.",
    )

    startup_timeout_s: float = Field(
        default=300.0,
        title="Startup timeout seconds",
        description="Seconds to wait for the mlx-serve process to accept requests.",
    )

    # --------------------------------------------------
    # generate
    # --------------------------------------------------

    max_pixels: int = Field(
        default=1344 * 768,
        title="Maximum pixels",
        description="Upper limit for width * height (the released 768p canvas).",
    )

    max_num_frames: int = Field(
        default=362,
        title="Maximum frame count",
        description="Upper limit for the frame count (15 seconds at 24 fps).",
    )

    default_width: int = Field(
        default=960,
        title="Default width",
        description="Video width in pixels used when a request omits width.",
    )

    default_height: int = Field(
        default=544,
        title="Default height",
        description="Video height in pixels used when a request omits height.",
    )

    default_num_frames: int = Field(
        default=124,
        title="Default frame count",
        description="Generated frame count used when a request omits num_frames (~5.2 s).",
    )

    default_turbo_steps: int = Field(
        default=8,
        title="Default Turbo steps",
        description="Denoising steps used with the Turbo LoRA when a request omits steps.",
    )

    default_steps: int = Field(
        default=20,
        title="Default steps",
        description="Denoising steps used without Turbo when a request omits steps.",
    )


settings_manager = SettingsManager(H3Settings)
