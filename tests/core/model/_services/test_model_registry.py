from types import ModuleType

import pytest

from kiapi.core.model import ModelDomain, ModelRegistry, ModelSpec, UnknownModelError


def _spec(
    name: str,
    *,
    family: str = "acestep",
    domain: ModelDomain = "audio",
    repo: str | None = None,
    aliases: tuple[str, ...] = (),
    default: bool = False,
) -> ModelSpec:
    return ModelSpec(
        name=name,
        family=family,
        domain=domain,
        repo=repo or f"org/{family}-{name}",
        module=ModuleType("fake_handler"),
        weight_gb=1.0,
        peak_headroom_gb=1.0,
        aliases=aliases,
        default=default,
    )


@pytest.fixture
def registry() -> ModelRegistry:
    return ModelRegistry()


# -- list_specs ---------------------------------------------------------------


def test_list_specs_empty(registry: ModelRegistry) -> None:
    assert registry.list_specs() == []


def test_list_specs_all_and_by_family(registry: ModelRegistry) -> None:
    a = _spec("turbo", family="acestep")
    b = _spec("xl-base", family="acestep")
    c = _spec("klein-9b", family="flux2", domain="image")
    for s in (a, b, c):
        registry.register(s)

    assert registry.list_specs() == [a, b, c]
    assert registry.list_specs("acestep") == [a, b]
    assert registry.list_specs("flux2") == [c]
    assert registry.list_specs("missing") == []


# -- families / domains -------------------------------------------------------


def test_families_preserves_registration_order_and_dedupes(
    registry: ModelRegistry,
) -> None:
    registry.register(_spec("turbo", family="acestep", domain="audio"))
    registry.register(_spec("klein-9b", family="flux2", domain="image"))
    registry.register(_spec("xl-base", family="acestep", domain="audio"))

    assert registry.families() == ["acestep", "flux2"]


def test_families_filtered_by_domain(registry: ModelRegistry) -> None:
    registry.register(_spec("turbo", family="acestep", domain="audio"))
    registry.register(_spec("klein-9b", family="flux2", domain="image"))
    registry.register(_spec("qwen", family="qwen", domain="image"))

    assert registry.families(domain="image") == ["flux2", "qwen"]
    assert registry.families(domain="audio") == ["acestep"]


def test_domains_dedupes_in_order(registry: ModelRegistry) -> None:
    registry.register(_spec("turbo", family="acestep", domain="audio"))
    registry.register(_spec("klein-9b", family="flux2", domain="image"))
    registry.register(_spec("xl-base", family="acestep", domain="audio"))

    assert registry.domains() == ["audio", "image"]


def test_domain_of(registry: ModelRegistry) -> None:
    registry.register(_spec("klein-9b", family="flux2", domain="image"))

    assert registry.domain_of("flux2") == "image"
    assert registry.domain_of("unknown") is None


# -- default_name -------------------------------------------------------------


def test_default_name_none_when_empty(registry: ModelRegistry) -> None:
    assert registry.default_name("acestep") is None


def test_default_name_honours_default_flag(registry: ModelRegistry) -> None:
    registry.register(_spec("turbo", family="acestep"))
    registry.register(_spec("xl-base", family="acestep", default=True))

    assert registry.default_name("acestep") == "xl-base"


def test_default_name_falls_back_to_first_registered(registry: ModelRegistry) -> None:
    registry.register(_spec("turbo", family="acestep"))
    registry.register(_spec("xl-base", family="acestep"))

    assert registry.default_name("acestep") == "turbo"


# -- resolve ------------------------------------------------------------------


def test_resolve_by_name(registry: ModelRegistry) -> None:
    spec = _spec("turbo", family="acestep")
    registry.register(spec)

    assert registry.resolve("acestep", "turbo") is spec


def test_resolve_is_case_insensitive(registry: ModelRegistry) -> None:
    spec = _spec("Turbo", family="acestep")
    registry.register(spec)

    assert registry.resolve("acestep", "TURBO") is spec


def test_resolve_by_repo_and_alias(registry: ModelRegistry) -> None:
    spec = _spec(
        "turbo",
        family="acestep",
        repo="org/acestep-turbo",
        aliases=("fast", "quick"),
    )
    registry.register(spec)

    assert registry.resolve("acestep", "org/acestep-turbo") is spec
    assert registry.resolve("acestep", "fast") is spec
    assert registry.resolve("acestep", "quick") is spec


def test_resolve_none_uses_default(registry: ModelRegistry) -> None:
    turbo = _spec("turbo", family="acestep")
    xl = _spec("xl-base", family="acestep", default=True)
    registry.register(turbo)
    registry.register(xl)

    assert registry.resolve("acestep", None) is xl


def test_resolve_unknown_raises(registry: ModelRegistry) -> None:
    registry.register(_spec("turbo", family="acestep"))

    with pytest.raises(UnknownModelError) as exc:
        registry.resolve("acestep", "nope")

    # message lists the available variant names
    assert "turbo" in str(exc.value)


def test_resolve_unknown_family_raises(registry: ModelRegistry) -> None:
    with pytest.raises(UnknownModelError):
        registry.resolve("nonexistent", None)
