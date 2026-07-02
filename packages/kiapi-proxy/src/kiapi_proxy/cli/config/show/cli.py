import click

from kiapi_proxy.core.config import get_user_settings_path


@click.command(name="show")
def show() -> None:
    """Show the user settings file."""
    path = get_user_settings_path()
    if not path.exists():
        raise click.ClickException(f"Settings file does not exist: {path}")

    click.echo(path.read_text(encoding="utf-8"), nl=False)
