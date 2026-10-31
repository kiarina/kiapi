"""Embedding-capability defaults, read from the environment (``KIAPI_EMBEDDING_``)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class EmbeddingSettings(BaseSettings):
    """Settings for Embedding input length limits."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_EMBEDDING_",
        extra="ignore",
        protected_namespaces=(),
    )

    max_length: int = Field(
        default=32768,
        title="Maximum input token length",
        description=(
            "Maximum tokenized length of one text input.\n"
            "Longer inputs are rejected with HTTP 400."
        ),
    )


settings_manager = SettingsManager(EmbeddingSettings)
