"""Driver for ``mise run verify``.

Selects a verification target (kiapi / kiapi-relay / kiapi-proxy), starts the
servers it needs (with the chosen relay), runs the matching verification
scripts, then tears the servers back down.

Targets:

- ``kiapi``       start ``kiapi run`` and verify capabilities directly (no relay).
- ``kiapi-relay`` start ``kiapi run --relay <relay>`` and verify the relay
                  transport itself.
- ``kiapi-proxy`` start ``kiapi run --relay <relay>`` plus
                  ``kiapi-proxy run --relay <relay>`` and verify capabilities
                  through the proxy.

With no target flag the three choices (target, family, relay) are picked
interactively with fzf. Pass a target flag to skip the prompts and fall back to
the defaults (family=all, relay=local).

If kiapi / kiapi-proxy are already running as launchd services they are stopped
before verification and restarted afterwards. If they are running some other way
the servers this script starts will fail on the single-instance guard; that is
surfaced so the user can stop the stray process.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
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
RELAY_DIR = HERE / "relay"

KIAPI_PORT = int(os.environ.get("KIAPI_PORT", "8000"))
PROXY_PORT = int(os.environ.get("KIAPI_PROXY_PORT", "8080"))

TARGETS = ("kiapi", "kiapi-relay", "kiapi-proxy")
RELAYS = ("local", "gcp")

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
        sys.exit(
            "fzf is required for interactive selection; "
            "pass a target flag (e.g. --kiapi) instead."
        )
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
    require_relay: bool,
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
            with urllib.request.urlopen(url, timeout=2.0) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(0.5)
            continue
        if require_relay:
            relay = body.get("relay") or {}
            if not relay.get("running"):
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


def run_relay(relay: str, *, fast: bool) -> int:
    script = RELAY_DIR / f"verify_{relay}.py"
    if not script.exists():
        sys.exit(f"relay verification script not found: {script}")
    cmd = [sys.executable, str(script)]
    if fast:
        cmd.append("--fast")
    print()
    print("=" * 72)
    print(f"Running {script.relative_to(PROJECT_DIR)} ({relay} relay)")
    print("=" * 72)
    return subprocess.run(cmd, cwd=PROJECT_DIR).returncode


def verify(target: str, family: str | None, relay: str | None, *, fast: bool) -> int:
    families = discover_families()
    log_dir = Path(tempfile.mkdtemp(prefix="kiapi-verify-"))
    procs: list[subprocess.Popen[bytes]] = []
    restore: list[str] = []

    service_modules = ["kiapi"]
    if target == "kiapi-proxy":
        service_modules.append("kiapi_proxy")

    try:
        for module in service_modules:
            if service_loaded(module):
                print(
                    f"Stopping running {module} service (will restart afterwards) ..."
                )
                subprocess.run(module_cmd(module, "service", "stop"), check=True)
                restore.append(module)

        if target == "kiapi":
            proc, log_path = start_server("kiapi", module_cmd("kiapi", "run"), log_dir)
            procs.append(proc)
            wait_health(
                f"http://127.0.0.1:{KIAPI_PORT}/health",
                proc,
                log_path,
                require_relay=False,
            )
            assert family is not None
            return run_capabilities(
                family,
                families,
                base_url=f"http://127.0.0.1:{KIAPI_PORT}",
                verify_dir=".verify/kiapi",
                fast=fast,
            )

        if target == "kiapi-relay":
            assert relay is not None
            proc, log_path = start_server(
                "kiapi", module_cmd("kiapi", "run", "--relay", relay), log_dir
            )
            procs.append(proc)
            wait_health(
                f"http://127.0.0.1:{KIAPI_PORT}/health",
                proc,
                log_path,
                require_relay=True,
            )
            return run_relay(relay, fast=fast)

        # kiapi-proxy
        assert relay is not None
        assert family is not None
        kiapi_proc, kiapi_log = start_server(
            "kiapi", module_cmd("kiapi", "run", "--relay", relay), log_dir
        )
        procs.append(kiapi_proc)
        wait_health(
            f"http://127.0.0.1:{KIAPI_PORT}/health",
            kiapi_proc,
            kiapi_log,
            require_relay=True,
        )
        proxy_proc, proxy_log = start_server(
            "kiapi-proxy", module_cmd("kiapi_proxy", "run", "--relay", relay), log_dir
        )
        procs.append(proxy_proc)
        wait_health(
            f"http://127.0.0.1:{PROXY_PORT}/health",
            proxy_proc,
            proxy_log,
            require_relay=False,
        )
        return run_capabilities(
            family,
            families,
            base_url=f"http://127.0.0.1:{PROXY_PORT}",
            verify_dir=".verify/kiapi-proxy",
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


def resolve_selection(args: argparse.Namespace) -> tuple[str, str | None, str | None]:
    interactive = args.target is None
    families = discover_families()

    target = args.target or fzf_select(list(TARGETS), "Target")

    family: str | None = None
    if target in ("kiapi", "kiapi-proxy"):
        if args.family is not None:
            family = args.family
        elif interactive:
            family = fzf_select(["all", *sorted(families)], "Family")
        else:
            family = "all"
        if family != "all" and family not in families:
            sys.exit(
                f"unknown family: {family} "
                f"(choose from: all, {', '.join(sorted(families))})"
            )

    relay: str | None = None
    if target in ("kiapi-relay", "kiapi-proxy"):
        if args.relay is not None:
            relay = args.relay
        elif interactive:
            relay = fzf_select(list(RELAYS), "Relay")
        else:
            relay = "local"
        if relay not in RELAYS:
            sys.exit(f"unknown relay: {relay} (choose from: {', '.join(RELAYS)})")

    return target, family, relay


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run kiapi verification scripts.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--kiapi",
        dest="target",
        action="store_const",
        const="kiapi",
        help="Verify capabilities against kiapi directly.",
    )
    group.add_argument(
        "--kiapi-relay",
        dest="target",
        action="store_const",
        const="kiapi-relay",
        help="Verify the relay transport.",
    )
    group.add_argument(
        "--kiapi-proxy",
        dest="target",
        action="store_const",
        const="kiapi-proxy",
        help="Verify capabilities through kiapi-proxy.",
    )
    parser.add_argument("--family", help="Capability family (default: all).")
    parser.add_argument("--relay", help="Relay to use (default: local).")
    parser.add_argument(
        "--fast", action="store_true", help="Pass --fast to the verify scripts."
    )
    return parser.parse_args()


def _raise_keyboard_interrupt(signum: int, frame: FrameType | None) -> None:
    raise KeyboardInterrupt


def main() -> int:
    signal.signal(signal.SIGTERM, _raise_keyboard_interrupt)
    args = parse_args()
    target, family, relay = resolve_selection(args)
    print(
        f"Target: {target}"
        + (f" | family: {family}" if family is not None else "")
        + (f" | relay: {relay}" if relay is not None else "")
    )
    return verify(target, family, relay, fast=args.fast)


if __name__ == "__main__":
    sys.exit(main())
