"""A single LoRA adapter reference (file + scale) applied to an ernie run."""

from pydantic import BaseModel, Field

from kiapi.core.file import FileRef


class LoraRef(BaseModel):
    """One LoRA adapter to apply, by Files-API reference and blend scale.

    Any lora forces a one-off transient model (slower, not reused). Up to 4 may
    be passed in a request's ``loras`` list.
    """

    file: FileRef = Field(
        description=(
            "The LoRA adapter (`.safetensors`) to apply, as a Files-API file id, "
            "http(s) URL, or data URL."
        ),
    )
    scale: float = Field(
        default=1.0,
        description=(
            "Blend strength for this adapter. 1.0 applies it at full weight; lower "
            "values weaken its effect, higher values exaggerate it."
        ),
    )
