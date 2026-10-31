"""OpenAI-compatible embedding request model, with image items as a kiapi extension."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EmbedItem(BaseModel):
    """One input with a field per modality (kiapi extension to OpenAI's `input`)."""

    model_config = ConfigDict(extra="forbid")

    text: str | None = Field(
        default=None,
        title="Text",
        description="Text to embed.",
    )
    image: str | None = Field(
        default=None,
        title="Image",
        description=(
            "Image to embed, as a base64 string, data URL, or http(s) URL. Only "
            "multimodal models accept it."
        ),
    )

    def inputs(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.text is not None:
            out["text"] = self.text
        if self.image is not None:
            out["image"] = self.image
        return out


class EmbedRequest(BaseModel):
    """Request body of `POST /v1/embeddings`."""

    model_config = ConfigDict(extra="allow")

    model: str | None = Field(
        default=None,
        title="Model",
        description=(
            "Registry name, alias, or repo of the embedding model (see "
            "`GET /v1/embedding/models`). Omit to use the default model."
        ),
    )
    input: str | EmbedItem | list[str | EmbedItem] = Field(
        title="Input",
        description=(
            "Text to embed, an array of inputs, or an `{text, image}` object for "
            "multimodal models. Each array element returns one embedding. Token "
            "arrays are not accepted."
        ),
    )
    dimensions: int | None = Field(
        default=None,
        ge=1,
        title="Dimensions",
        description=(
            "Output vector length. The vector is truncated and L2-normalized again. "
            "Supported: 32-4096 for `qwen3-embedding-8b`, 64-2048 for "
            "`qwen3-vl-embedding-2b`."
        ),
    )
    encoding_format: Literal["float", "base64"] = Field(
        default="float",
        title="Encoding format",
        description="`float` returns a number array; `base64` returns little-endian float32 bytes.",
    )

    def items(self) -> list[dict[str, Any]]:
        values = self.input if isinstance(self.input, list) else [self.input]
        return [
            {"text": value} if isinstance(value, str) else value.inputs()
            for value in values
        ]
