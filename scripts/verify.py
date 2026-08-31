"""Driver for ``mise run verify``.

Starts ``kiapi run``, runs the selected capability verification scripts against
it, then tears the server back down.

With no flags the family is picked interactively with fzf. Pass ``--kiapi`` to
skip the prompt and fall back to the default (family=all).

If kiapi is already running as a launchd service it is stopped before
verification and restarted afterwards. If it is running some other way the
server this script starts will fail on the single-instance guard; that is
surfaced so the user can stop the stray process.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from types import FrameType

HERE = Path(__file__).resolve().parent
PROJECT_DIR = HERE.parent
CAPABILITIES_DIR = HERE / "capabilities"

KIAPI_PORT = int(os.environ.get("KIAPI_PORT", "8000"))

# Capability scripts that expect their "train" flag set (ported from the old
# mise task, which special-cased these three).
_TRAIN_ENV = {
    "verify_ernie": "KIAPI_VERIFY_ERNIE_TRAIN",
    "verify_flux2": "KIAPI_VERIFY_FLUX2_TRAIN",
    "verify_zimage": "KIAPI_VERIFY_ZIMAGE_TRAIN",
}


def discover_families() -> dict[str, list[Path]]:
    """Map each capability family to its verification scripts.

    The family name is the capability directory name; ``chat`` bundles both
    ``verify_chat.py`` and ``verify_chat_stream.py``.
    """
    families: dict[str, list[Path]] = {}
    for script in sorted(CAPABILITIES_DIR.glob("verify_*.py")):
        base = script.stem.removeprefix("verify_")
        family = "chat" if base in {"chat", "chat_stream"} else base
        families.setdefault(family, []).append(script)
    return families


def fzf_select(options: list[str], prompt: str) -> str:
    if not shutil.which("fzf"):
        sys.exit("fzf is required for interactive selection; pass --kiapi instead.")
    result = subprocess.run(
        ["fzf", f"--prompt={prompt}> ", "--height=40%", "--border"],
        input="\n".join(options),
        capture_output=True,
        text=True,
    )
    choice = result.stdout.strip()
    if not choice:
        sys.exit("No selection made.")
    return choice


def module_cmd(module: str, *extra: str) -> list[str]:
    return [sys.executable, "-m", module, *extra]


def run_cmd(module: str, port: int) -> list[str]:
    """Build a server start command with explicit host/port.

    Everything is passed explicitly so user settings (which may bind another
    port) cannot leak into the server verify starts.
    """
    return module_cmd(
        module,
        "run",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    )


def service_loaded(module: str) -> bool:
    result = subprocess.run(
        module_cmd(module, "service", "status"),
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith("Loaded:"):
            return line.split(":", 1)[1].strip() == "yes"
    return False


def ensure_port_free(name: str, port: int) -> None:
    """Abort if ``port`` is already served by a stray process.

    The launchd service is stopped before this runs, so anything still
    listening is an unmanaged instance. Verifying against it would be misleading
    (health checks would pass against the wrong server), so stop and let the user
    clear it.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            sys.exit(
                f"port {port} is already in use; a {name} instance appears to be "
                f"running outside of verify. Stop it and try again."
            )


def start_server(
    name: str, args: list[str], log_dir: Path
) -> tuple[subprocess.Popen[bytes], Path]:
    log_path = log_dir / f"{name}.log"
    log_file = log_path.open("wb")
    print(f"Starting {name}: {' '.join(args)}")
    proc = subprocess.Popen(
        args,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=PROJECT_DIR,
    )
    return proc, log_path


def wait_health(
    url: str,
    proc: subprocess.Popen[bytes],
    log_path: Path,
    *,
    timeout_s: float = 120.0,
) -> None:
    print(f"Waiting for {url} ...")
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            tail = log_path.read_text(errors="replace")[-2000:]
            sys.exit(
                f"{url}: server exited early (code {proc.returncode}). "
                f"Another instance may already be running.\n{tail}"
            )
        try:
            with urllib.request.urlopen(url, timeout=2.0):
                pass
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(0.5)
            continue
        print(f"  ready: {url}")
        return
    sys.exit(f"{url}: not healthy within {timeout_s:.0f}s")


def terminate(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def run_capabilities(
    family: str,
    families: dict[str, list[Path]],
    *,
    base_url: str,
    verify_dir: str,
    fast: bool,
) -> int:
    if family == "all":
        scripts = sorted({s for group in families.values() for s in group})
    else:
        scripts = families[family]

    base_env = os.environ.copy()
    base_env["KIAPI_BASE_URL"] = base_url
    base_env["KIAPI_VERIFY_DIR"] = verify_dir

    status = 0
    for script in scripts:
        env = base_env.copy()
        train = _TRAIN_ENV.get(script.stem)
        if train is not None:
            env[train] = "1"
        cmd = [sys.executable, str(script)]
        if fast:
            cmd.append("--fast")
        print()
        print("=" * 72)
        print(f"Running {script.relative_to(PROJECT_DIR)} -> {base_url}")
        print("=" * 72)
        if subprocess.run(cmd, env=env, cwd=PROJECT_DIR).returncode != 0:
            status = 1
    return status


def verify(family: str, *, fast: bool) -> int:
    families = discover_families()
    log_dir = Path(tempfile.mkdtemp(prefix="kiapi-verify-"))
    procs: list[subprocess.Popen[bytes]] = []
    restore: list[str] = []

    try:
        if service_loaded("kiapi"):
            print("Stopping running kiapi service (will restart afterwards) ...")
            subprocess.run(module_cmd("kiapi", "service", "stop"), check=True)
            restore.append("kiapi")

        ensure_port_free("kiapi", KIAPI_PORT)
        proc, log_path = start_server("kiapi", run_cmd("kiapi", KIAPI_PORT), log_dir)
        procs.append(proc)
        wait_health(
            f"http://127.0.0.1:{KIAPI_PORT}/health",
            proc,
            log_path,
        )
        return run_capabilities(
            family,
            families,
            base_url=f"http://127.0.0.1:{KIAPI_PORT}",
            verify_dir=".verify/kiapi",
            fast=fast,
        )
    finally:
        for proc in reversed(procs):
            terminate(proc)
        for module in restore:
            print(f"Restarting {module} service ...")
            try:
                subprocess.run(module_cmd(module, "service", "start"), check=True)
            except subprocess.CalledProcessError as exc:
                print(f"  warning: failed to restart {module} service: {exc}")


def resolve_family(args: argparse.Namespace) -> str:
    interactive = not args.kiapi
    families = discover_families()

    if args.family is not None:
        family = str(args.family)
    elif interactive:
        family = fzf_select(["all", *sorted(families)], "Family")
    else:
        family = "all"
    if family != "all" and family not in families:
        sys.exit(
            f"unknown family: {family} "
            f"(choose from: all, {', '.join(sorted(families))})"
        )
    return family


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run kiapi verification scripts.")
    parser.add_argument(
        "--kiapi",
        action="store_true",
        help="Skip the interactive prompt and use the defaults.",
    )
    parser.add_argument("--family", help="Capability family (default: all).")
    parser.add_argument(
        "--fast", action="store_true", help="Pass --fast to the verify scripts."
    )
    return parser.parse_args()


def _raise_keyboard_interrupt(signum: int, frame: FrameType | None) -> None:
    raise KeyboardInterrupt


def main() -> int:
    signal.signal(signal.SIGTERM, _raise_keyboard_interrupt)
    args = parse_args()
    family = resolve_family(args)
    print(f"Target: kiapi | family: {family}")
    return verify(family, fast=args.fast)


if __name__ == "__main__":
    sys.exit(main())
