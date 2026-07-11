import os
import plistlib
import subprocess
import sys
import time
from pathlib import Path

SERVICE_LABEL = os.getenv("KIAPI_SERVICE_LABEL", "io.github.kiarina.kiapi")


def get_launchd_domain() -> str:
    return f"gui/{os.getuid()}"


def get_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{SERVICE_LABEL}.plist"


def get_log_dir() -> Path:
    return Path("/tmp/kiapi/service")


def get_stdout_path() -> Path:
    return get_log_dir() / "out.log"


def get_stderr_path() -> Path:
    return get_log_dir() / "err.log"


def is_installed() -> bool:
    return get_plist_path().exists()


def is_loaded() -> bool:
    result = run_launchctl(["print", f"{get_launchd_domain()}/{SERVICE_LABEL}"])
    return result.returncode == 0


def install() -> None:
    get_log_dir().mkdir(parents=True, exist_ok=True)
    plist_path = get_plist_path()
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    plist = {
        "Label": SERVICE_LABEL,
        "ProgramArguments": [
            sys.executable,
            "-m",
            "kiapi",
            "run",
        ],
        "EnvironmentVariables": _build_environment_variables(),
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(get_stdout_path()),
        "StandardErrorPath": str(get_stderr_path()),
    }
    plist_path.write_bytes(plistlib.dumps(plist, sort_keys=False))


def _build_environment_variables() -> dict[str, str]:
    env = {"PYTHONUNBUFFERED": "1"}

    for name in ("XDG_CONFIG_HOME", "XDG_DATA_HOME"):
        value = os.environ.get(name)
        if value:
            env[name] = value

    return env


def start() -> None:
    domain = get_launchd_domain()
    result = run_launchctl(["bootstrap", domain, str(get_plist_path())])
    if result.returncode != 0:
        raise RuntimeError(_format_launchctl_error(result.stderr))

    result = run_launchctl(["kickstart", "-k", f"{domain}/{SERVICE_LABEL}"])
    if result.returncode != 0:
        raise RuntimeError(_format_launchctl_error(result.stderr))


def stop() -> None:
    result = run_launchctl(["bootout", f"{get_launchd_domain()}/{SERVICE_LABEL}"])
    if result.returncode != 0:
        raise RuntimeError(_format_launchctl_error(result.stderr))

    _wait_until_stopped()


def uninstall() -> None:
    get_plist_path().unlink()


def run_launchctl(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["launchctl", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _wait_until_stopped() -> None:
    for _ in range(20):
        if not is_loaded():
            return
        time.sleep(0.1)


def _format_launchctl_error(stderr: str) -> str:
    detail = stderr.strip()
    if not detail:
        return "launchctl failed"
    return detail
