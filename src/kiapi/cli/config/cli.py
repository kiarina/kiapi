import click

from .edit.cli import edit
from .init.cli import init
from .show.cli import show
from .template.cli import template


@click.group(name="config")
def config_cli() -> None:
    """Manage kiapi user settings."""


config_cli.add_command(init)
config_cli.add_command(show)
config_cli.add_command(edit)
config_cli.add_command(template)
