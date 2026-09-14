import click
import questionary

from kiapi.core.model import ModelSpec, model_registry


def select_specs(
    *,
    all_selected: bool,
    domains: tuple[str, ...],
    families: tuple[str, ...],
    repos: tuple[str, ...],
    interactive: bool,
    action: str = "activate",
) -> list[ModelSpec]:
    specs = model_registry.list_specs()
    if all_selected:
        return specs

    if domains or families or repos:
        selected = [
            spec
            for spec in specs
            if _matches(spec, domains=domains, families=families, repos=repos)
        ]
        if not selected:
            raise click.ClickException("No matching models found.")
        return selected

    if not interactive:
        raise click.ClickException("Specify --all, --domain, --family, or --repo.")

    choices = [
        questionary.Choice(title=_spec_choice_title(spec), value=spec) for spec in specs
    ]
    selected = questionary.checkbox(
        f"Select models to {action}:", choices=choices
    ).ask()
    if not selected:
        raise click.ClickException("No models selected.")
    return list(selected)


def _matches(
    spec: ModelSpec,
    *,
    domains: tuple[str, ...],
    families: tuple[str, ...],
    repos: tuple[str, ...],
) -> bool:
    if domains and spec.domain in domains:
        return True
    if families and spec.family in families:
        return True
    if repos:
        values = {spec.repo, *spec.aliases}
        values.update(resource.label for resource in spec.setup_resources)
        if values.intersection(repos):
            return True
    return False


def _spec_choice_title(spec: ModelSpec) -> str:
    size = sum(resource.disk_gb or 0.0 for resource in spec.setup_resources)
    size_label = f" ~{size:g} GB" if size else ""
    default = " default" if spec.default else ""
    return f"{spec.domain}/{spec.family}/{spec.name}{default}{size_label}"
