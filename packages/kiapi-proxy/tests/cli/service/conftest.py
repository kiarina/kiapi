from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner, Result

from kiapi_proxy.cli.cli import main


def invoke_service(
    tmp_path: Path,
    command: str,
) -> Result:
    return CliRunner().invoke(
        main,
        ["service", command],
        env={
            "HOME": str(tmp_path),
            "KIARINA_UTILS_APP_USER_CONFIG_DIR": str(tmp_path / "config"),
        },
    )


def write_service_plist(home: Path) -> Path:
    plist = home / "Library" / "LaunchAgents" / "io.github.kiarina.kiapi-proxy.plist"
    plist.parent.mkdir(parents=True)
    plist.write_text("installed", encoding="utf-8")
    return plist


def record_launchctl(
    calls: list[list[str]],
    args: list[str],
) -> SimpleNamespace:
    calls.append(args)
    return SimpleNamespace(returncode=0, stderr="")
