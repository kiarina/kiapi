from dataclasses import dataclass, field


@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    domain: str
    title: str
    summary: str
    """One-line capability summary for root OpenAPI navigation."""
    description: str
    """Detailed Markdown description for the capability OpenAPI document."""
    openapi_path: str
    docs_path: str
    redoc_path: str
    path_prefixes: tuple[str, ...]
    include_paths: tuple[str, ...] = field(default_factory=tuple)
