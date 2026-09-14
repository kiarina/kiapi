from .._schemas.capability_spec import CapabilitySpec


class CapabilitySpecRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, CapabilitySpec] = {}

    def register(self, spec: CapabilitySpec) -> None:
        self._specs[spec.name] = spec

    def get(self, name: str) -> CapabilitySpec | None:
        return self._specs.get(name)

    def list_specs(self) -> list[CapabilitySpec]:
        return sorted(self._specs.values(), key=lambda spec: (spec.domain, spec.name))

    def names(self) -> list[str]:
        return [spec.name for spec in self.list_specs()]


capability_spec_registry = CapabilitySpecRegistry()
