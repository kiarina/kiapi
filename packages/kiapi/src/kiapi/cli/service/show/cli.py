import click

from kiapi.cli.service import service_manager


@click.command(name="show")
def show() -> None:
    """Show the installed launchd property list."""
    path = service_manager.get_plist_path()
    if not path.exists():
        raise click.ClickException(f"Service is not installed: {path}")

    click.echo(path.read_text(encoding="utf-8"), nl=False)
