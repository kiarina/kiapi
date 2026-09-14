import click

from kiapi.cli import (
    dedupe_resources,
    register_all_capabilities,
    run_resources,
    select_specs,
)
from kiapi.core.setup import SetupManager

from ._operations.preflight_hf_access import preflight_hf_access


@click.command()
@click.option("--all", "activate_all", is_flag=True, help="Activate all models")
@click.option("--domain", "domains", multiple=True, help="Activate domain")
@click.option("--family", "families", multiple=True, help="Activate family")
@click.option("--repo", "repos", multiple=True, help="Activate repo/image")
def activate(
    activate_all: bool,
    domains: tuple[str, ...],
    families: tuple[str, ...],
    repos: tuple[str, ...],
) -> None:
    """Download Hugging Face snapshots and pull Docker images."""
    register_all_capabilities()
    specs = select_specs(
        all_selected=activate_all,
        domains=domains,
        families=families,
        repos=repos,
        interactive=True,
    )
    resources = dedupe_resources(specs)
    manager = SetupManager()
    preflight_hf_access(resources, manager)
    run_resources("activate", resources, manager)
