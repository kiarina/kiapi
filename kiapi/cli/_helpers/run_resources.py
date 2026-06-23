import click

from kiapi.core.setup import SetupManager, SetupResource


def run_resources(
    action: str, resources: list[SetupResource], manager: SetupManager
) -> None:
    if not resources:
        click.echo("No setup resources.")
        return

    for resource in resources:
        click.echo(f"{action}: {resource.kind} {resource.label}")
        try:
            if action == "activate":
                state = manager.activate(resource)
            else:
                state = manager.deactivate(resource)
        except Exception as exc:
            raise click.ClickException(f"{resource.label}: {exc}") from exc

        mark = "ok" if state.ready else "missing"
        click.echo(f"  [{mark}] {state.detail}")
