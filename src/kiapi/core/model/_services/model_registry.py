"""The model registry: the catalog of servable models across all families.

kiapi organizes models on two axes:

  - ``domain`` — the modality bucket for discovery/grouping: "chat", "embedding",
    "audio", "video", "image".
  - ``family`` — the provider/model family that owns an *operation vocabulary*,
    spelled as a single lowercase token from the upstream's package/model name
    ("acestep", "audiogen", "ltx2", "chat", "embedding"). The family is the
    resolution namespace and the capability OpenAPI document.

Generation endpoints are organized as ``/v1/<domain>/<family>/<op>`` — each
family exposes exactly its own operations and request shape (no forced common
schema). ``model`` selects a *variant within the family* (e.g. acestep
``xl-base`` / ``turbo``), named by the variant alone (it must not repeat the
family). chat/embedding stay standardized modality APIs (family == domain).
"""

from .._exceptions.unknown_model_error import UnknownModelError
from .._schemas.model_spec import ModelSpec
from .._types.model_domain import ModelDomain
from .._types.model_family import ModelFamily
from .._types.model_key import ModelKey
from .._types.model_name import ModelName


class ModelRegistry:
    def __init__(self) -> None:
        self._specs: list[ModelSpec] = []
        self._index: dict[tuple[ModelFamily, ModelKey], ModelSpec] = {}

    def register(self, spec: ModelSpec) -> None:
        for k in (spec.name, spec.repo, *spec.aliases):
            self._index[(spec.family, k.lower())] = spec
        self._specs.append(spec)

    def list_specs(self, family: ModelFamily | None = None) -> list[ModelSpec]:
        if family is None:
            return list(self._specs)
        return [s for s in self._specs if s.family == family]

    def families(self, domain: ModelDomain | None = None) -> list[ModelFamily]:
        seen: list[ModelFamily] = []
        for s in self._specs:
            if domain is not None and s.domain != domain:
                continue
            if s.family not in seen:
                seen.append(s.family)
        return seen

    def domains(self) -> list[ModelDomain]:
        seen: list[ModelDomain] = []
        for s in self._specs:
            if s.domain not in seen:
                seen.append(s.domain)
        return seen

    def domain_of(self, family: ModelFamily) -> ModelDomain | None:
        for s in self._specs:
            if s.family == family:
                return s.domain
        return None

    def default_name(self, family: ModelFamily) -> ModelName | None:
        specs = self.list_specs(family)
        if not specs:
            return None
        for s in specs:
            if s.default:
                return s.name
        return specs[0].name

    def resolve(self, family: ModelFamily, name: ModelName | None) -> ModelSpec:
        default = self.default_name(family)
        key = (name or default or "").strip().lower()
        spec = self._index.get((family, key))
        if spec is None:
            known = sorted({s.name for s in self.list_specs(family)})
            raise UnknownModelError(
                f"unknown {family} model {name!r}; available: {known}"
            )
        return spec


model_registry = ModelRegistry()
