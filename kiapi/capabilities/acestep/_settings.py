"""ace-step capability config, read from the environment (``KIAPI_ACESTEP_``).

Unset path settings are resolved under ``kiapi.core.app.get_user_data_dir()/acestep``.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class AceStepSettings(BaseSettings):
    """Settings for the ACE-Step isolated venv subprocess, checkpoints, and generation duration."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_ACESTEP_",
        extra="ignore",
        protected_namespaces=(),
    )

    python_path: str | None = Field(
        default=None,
        title="ACE-Step Python executable",
        description=(
            "Python path for the dedicated venv where ACE-Step dependencies are installed.\n"
            "When unset, kiapi uses the ACE-Step venv under the user data directory."
        ),
    )

    project_root: str | None = Field(
        default=None,
        title="ACE-Step working directory",
        description=(
            "Directory where ACE-Step writes support files such as .cache/acestep.\n"
            "When unset, kiapi uses an ACE-Step project directory under the user data directory."
        ),
    )

    checkpoint_dir: str | None = Field(
        default=None,
        title="ACE-Step checkpoint directory",
        description=(
            "Directory containing checkpoint subdirectories such as "
            "acestep-5Hz-lm-1.7B and acestep-v15-*.\n"
            "When unset, kiapi uses the ACE-Step checkpoint directory under the "
            "user data directory."
        ),
    )

    llm_model: str = Field(
        default="acestep-5Hz-lm-1.7B",
        title="Shared LLM checkpoint name",
        description=(
            "Subdirectory name under checkpoint_dir for the ACE-Step language model checkpoint."
        ),
    )

    ready_timeout_s: float = Field(
        default=600.0,
        title="Subprocess ready timeout seconds",
        description=(
            "Maximum seconds to wait for the ACE-Step subprocess to load models "
            "and become ready."
        ),
    )

    job_timeout_s: float = Field(
        default=1200.0,
        title="Generation job timeout seconds",
        description="Maximum runtime seconds allowed for one ACE-Step generation job.",
    )

    max_duration: int = Field(
        default=300,
        title="Maximum generation seconds",
        description=(
            "Upper limit for music generation duration in seconds accepted in a request.\n"
            "Longer values occupy the worker and keep memory resident for longer."
        ),
    )


settings_manager = SettingsManager(AceStepSettings)
