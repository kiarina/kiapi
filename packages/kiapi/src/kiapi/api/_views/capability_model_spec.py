from pydantic import BaseModel, Field

from kiapi.core.model import ModelSpec


class CapabilityModelSpec(BaseModel):
    """Public model discovery entry for capability-specific model lists."""

    name: str = Field(
        ...,
        description="Model variant name to pass in the request model field.",
        examples=["turbo"],
    )
    family: str = Field(
        ...,
        description="Capability family that resolves this model variant.",
        examples=["zimage"],
    )
    domain: str = Field(
        ...,
        description="Capability domain used for grouping model lists.",
        examples=["image"],
    )
    aliases: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Alternative names that also resolve to this model.",
        examples=[["omni", "qwen3-omni-30b"]],
    )
    default: bool = Field(
        default=False,
        description="Whether this is the default model when the request omits model.",
        examples=[True],
    )
    features: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Handler-declared modalities and features supported by this model.",
        examples=[["text", "image"]],
    )

    @classmethod
    def from_model_spec(cls, spec: ModelSpec) -> "CapabilityModelSpec":
        return cls(
            name=spec.name,
            family=spec.family,
            domain=spec.domain,
            aliases=spec.aliases,
            default=spec.default,
            features=tuple(sorted(spec.features)),
        )
