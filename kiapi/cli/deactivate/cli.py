import click
import questionary

from kiapi.cli import (
    dedupe_resources,
    register_all_capabilities,
    run_resources,
    select_specs,
)
from kiapi.core.setup import SetupManager, SetupResource


@click.command()
@click.option("--all", "deactivate_all", is_flag=True, help="Deactivate all models")
@click.option("--domain", "domains", multiple=True, help="Deactivate domain")
@click.option("--family", "families", multiple=True, help="Deactivate family")
@click.option("--repo", "repos", multiple=True, help="Deactivate repo/image")
def deactivate(
    deactivate_all: bool,
    domains: tuple[str, ...],
    families: tuple[str, ...],
    repos: tuple[str, ...],
) -> None:
    """Select and remove Hugging Face snapshots, Docker images, and URL files."""
    register_all_capabilities()
    specs = select_specs(
        all_selected=deactivate_all,
        domains=domains,
        families=families,
        repos=repos,
        interactive=True,
        action="deactivate",
    )
    resources = dedupe_resources(specs)
    if not _confirm_deactivate(resources):
        click.echo("Canceled.")
        return
    run_resources("deactivate", resources, SetupManager())


def _confirm_deactivate(resources: list[SetupResource]) -> bool:
    if not resources:
        return True
    labels = ", ".join(resource.label for resource in resources)
    answer = questionary.confirm(
        f"Deactivate {len(resources)} setup resource(s)? {labels}",
        default=False,
    ).ask()
    return bool(answer)
