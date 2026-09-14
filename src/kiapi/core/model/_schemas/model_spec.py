"""A registry entry: everything needed to discover, resolve, load, and budget a
servable model variant.

Each :class:`ModelSpec` ties together:

  - the public ``name`` (the variant) used in a request's ``model`` field,
  - its ``family`` (resolution namespace + cache-key prefix + OpenAPI topic) and
    ``domain`` (grouping),
  - the Hugging Face ``repo`` to load,
  - the per-model **handler module** that owns its own flow,
  - memory estimates (``weight_gb`` / ``peak_headroom_gb``), ``priority``,
    ``framework``, ``resident``, ``ttl_seconds`` (see core/memory.py).

A handler module must expose:

    FEATURES : set[str]                      # modalities/features, family-specific
    load(spec) -> payload                    # load weights, return an opaque payload
    run(payload, req, settings) -> result    # one job's worth of work
    # optional:
    warmup(payload) -> None                  # prime kernels (else: load only)
    release(payload) -> None                 # extra cleanup beyond framework default

Estimates are intentionally rough; core/memory.py reconciles ``weight_gb`` with
the real measured footprint after the first load.

This is a Pydantic model so the family model-list endpoints
(``/v1/{domain}/{family}/models``) can serialize specs directly and have their
fields documented in OpenAPI. The handler ``module`` is excluded from output.
"""

from types import ModuleType

from pydantic import BaseModel, ConfigDict, Field, computed_field
from pydantic.json_schema import SkipJsonSchema

from kiapi.core.setup import SetupResource

from .._types.model_alias import ModelAlias
from .._types.model_domain import ModelDomain
from .._types.model_family import ModelFamily
from .._types.model_name import ModelName
from .._types.model_repo import ModelRepo


class ModelSpec(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    name: ModelName = Field(
        ...,
        description="Public model variant name passed in a request's model field; "
        "named by the variant alone, never repeating the family.",
        examples=["turbo"],
    )
    family: ModelFamily = Field(
        ...,
        description="Family that owns the operation vocabulary and resolves this "
        "variant; also used as the API identifier and OpenAPI topic.",
        examples=["zimage"],
    )
    domain: ModelDomain = Field(
        ...,
        description="Modality bucket used for discovery and grouping.",
        examples=["image"],
    )
    repo: ModelRepo = Field(
        ...,
        description="Hugging Face repo id (or local path) the weights load from.",
        examples=["mflux/z-image-turbo"],
    )
    module: SkipJsonSchema[ModuleType] = Field(
        ...,
        exclude=True,
        description="Per-model handler module that owns this model's load/run flow "
        "(internal; not serialized).",
    )
    weight_gb: float = Field(
        ...,
        ge=0.0,
        description="Rough estimate of resident weight footprint in GB. "
        "core/memory reconciles this with the measured footprint after first load.",
        examples=[6.0],
    )
    peak_headroom_gb: float = Field(
        ...,
        ge=0.0,
        description="Rough estimate of peak memory above the weights during a job, "
        "in GB — the extra budget headroom kept free while running.",
        examples=[4.0],
    )
    framework: str = Field(
        default="mlx",
        description='Backend that owns this model\'s memory (e.g. "mlx", or "rss" '
        "for a subprocess whose footprint kiapi can only see as process RSS).",
        examples=["mlx"],
    )
    priority: int = Field(
        default=0,
        description="Eviction priority. Residents are evicted by (priority asc, "
        "last_used asc); a higher value keeps a model resident under churn.",
        examples=[0],
    )
    aliases: tuple[ModelAlias, ...] = Field(
        default_factory=tuple,
        description="Extra names that also resolve to this spec.",
        examples=[["omni", "qwen3-omni-30b"]],
    )
    default: bool = Field(
        default=False,
        exclude=True,
        description="Whether this is the family's default variant when a request "
        "omits model. If no spec sets it, the first-registered spec is the default "
        "(internal; not serialized).",
    )
    resident: bool = Field(
        default=True,
        description="Whether the model is held resident after loading. Transient "
        "specs (resident=False) load+free per call and reserve budget instead of "
        "acquiring it.",
        examples=[True],
    )
    ttl_seconds: float | None = Field(
        default=None,
        description="Optional idle TTL (seconds). None inherits the global default; "
        "a value <= 0 means never expire (pin resident).",
        examples=[1800.0],
    )
    setup_resources: tuple[SetupResource, ...] = Field(
        default_factory=tuple,
        description="Resources that must be activated before this model can run: "
        "Hugging Face snapshots, Docker images, local paths, URL files, or Python "
        "virtual environments.",
    )

    @property
    def key(self) -> str:
        """Stable identity in the resident cache (unique per loaded weights)."""
        return f"{self.family}:{self.repo}"

    @computed_field(  # type: ignore[prop-decorator]
        description="Handler-declared modalities/features (NOT the family).",
        examples=[["text", "image"]],
    )
    @property
    def features(self) -> set[str]:
        return set(getattr(self.module, "FEATURES", set()))
