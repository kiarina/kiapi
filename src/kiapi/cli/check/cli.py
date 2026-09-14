import importlib
import re
import traceback

import click

from kiapi.cli import register_all_capabilities, select_specs
from kiapi.core.app import AppContext
from kiapi.core.model import ModelSpec

from ._operations.check_context import CheckOperation
from ._schemas.check_result import CheckResult

_NON_IDENTIFIER = re.compile(r"[^0-9a-zA-Z]+")


@click.command()
@click.option("--all", "check_all", is_flag=True, help="Check all models")
@click.option("--domain", "domains", multiple=True, help="Check domain")
@click.option("--family", "families", multiple=True, help="Check family")
@click.option("--repo", "repos", multiple=True, help="Check repo/image")
def check(
    check_all: bool,
    domains: tuple[str, ...],
    families: tuple[str, ...],
    repos: tuple[str, ...],
) -> None:
    """Run lightweight smoke checks for activated models."""
    register_all_capabilities()
    specs = select_specs(
        all_selected=check_all,
        domains=domains,
        families=families,
        repos=repos,
        interactive=True,
        action="check",
    )

    ctx = AppContext.create()
    failures = 0
    try:
        for spec in specs:
            click.echo(f"checking {spec.domain}/{spec.family}/{spec.name} ...")
            result = _run_check(ctx, spec)
            mark = "ok" if result.ok else "failed"
            click.echo(f"  [{mark}] {result.message}")
            failures += 0 if result.ok else 1
    finally:
        ctx.memory_manager.shutdown()

    if failures:
        raise click.ClickException(f"{failures} check(s) failed.")


def _run_check(ctx: AppContext, spec: ModelSpec) -> CheckResult:
    try:
        check_operation = _resolve_check_operation(spec)
    except ModuleNotFoundError:
        return CheckResult(
            ok=False,
            message=f"{spec.domain}/{spec.family}/{spec.name}: check is not implemented",
        )

    try:
        return check_operation(ctx, spec)
    except Exception as exc:
        traceback.print_exc()
        return CheckResult(
            ok=False,
            message=f"{spec.domain}/{spec.family}/{spec.name}: {exc}",
        )


def _resolve_check_operation(spec: ModelSpec) -> CheckOperation:
    module_name = _module_name(spec)
    module = importlib.import_module(
        f"kiapi.cli.check._helpers.{module_name}",
    )
    check_operation = module.check
    return check_operation  # type: ignore[no-any-return]


def _module_name(spec: ModelSpec) -> str:
    parts = ("check", spec.domain, spec.family, spec.name)
    return "_".join(_slug(part) for part in parts)


def _slug(value: str) -> str:
    return _NON_IDENTIFIER.sub("_", value.strip().lower()).strip("_")
