import os
import shlex
import subprocess

import click

from kiapi_proxy.core.config import get_user_settings_path


@click.command(name="edit")
def edit() -> None:
    """Open the user settings file in an editor."""
    path = get_user_settings_path()
    if not path.exists():
        raise click.ClickException(
            f"Settings file does not exist: {path}\n"
            "Run `kiapi-proxy config init` to create it."
        )

    command = _resolve_editor_command(str(path))
    subprocess.run(command, check=True)


def _resolve_editor_command(path: str) -> list[str]:
    editor = os.getenv("VISUAL") or os.getenv("EDITOR")
    if editor:
        return [*shlex.split(editor), path]

    if os.name == "posix":
        return ["open", "-t", path]

    return ["notepad", path]
