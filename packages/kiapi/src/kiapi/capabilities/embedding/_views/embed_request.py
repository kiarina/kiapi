"""Embedding request model — one item, one field per modality."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EmbedRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str | None = Field(
        default=None,
        description=(
            "Registry name, alias, or repo of the embedding model (see "
            "`GET /v1/embedding/models`). Omit to use the default model."
        ),
    )

    text: str | None = Field(
        default=None,
        description="Text to embed. Supported by every embedding model.",
    )
    image: str | None = Field(
        default=None,
        description=(
            "Image to embed, as a base64 string, data URL, http(s) URL, or local "
            "path. Only multimodal models accept it; sending it to a text-only "
            "model returns HTTP 400."
        ),
    )

    def inputs(self) -> dict[str, Any]:
        """Present modality inputs, keyed by modality name (skips unset ones)."""
        out: dict[str, Any] = {}
        if self.text is not None:
            out["text"] = self.text
        if self.image is not None:
            out["image"] = self.image
        return out
