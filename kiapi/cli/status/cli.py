from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import click

from kiapi.cli import register_all_capabilities
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import SetupManager, SetupResource, SetupStatus


@click.command()
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show repository and setup resource details.",
)
def status(verbose: bool) -> None:
    """Show model and backend setup status."""
    register_all_capabilities()
    manager = SetupManager()
    specs = sorted(
        model_registry.list_specs(),
        key=lambda spec: (spec.domain, spec.family),
    )
    rows = _collect_rows(specs, manager)

    click.echo("kiapi setup status")
    click.echo()
    _echo_summary(rows)
    click.echo()
    _echo_table(rows, verbose=verbose)
    _echo_missing(rows)


@dataclass(frozen=True)
class ResourceRow:
    resource: SetupResource
    ready: bool
    detail: str

    @property
    def status(self) -> str:
        return "ready" if self.ready else "missing"


@dataclass(frozen=True)
class StatusRow:
    spec: ModelSpec
    resources: tuple[ResourceRow, ...]

    @property
    def domain(self) -> str:
        return self.spec.domain

    @property
    def family(self) -> str:
        return self.spec.family

    @property
    def model(self) -> str:
        suffix = " *" if self.spec.default else ""
        return f"{self.spec.name}{suffix}"

    @property
    def status(self) -> str:
        if not self.resources:
            return "none"
        if all(resource.ready for resource in self.resources):
            return "ready"
        return "missing"

    @property
    def ready_resources(self) -> int:
        return sum(1 for resource in self.resources if resource.ready)

    @property
    def total_resources(self) -> int:
        return len(self.resources)

    @property
    def resource_count(self) -> str:
        return f"{self.ready_resources}/{self.total_resources}"

    @property
    def size_gb(self) -> float:
        return sum(resource.resource.disk_gb or 0.0 for resource in self.resources)

    @property
    def size(self) -> str:
        return _format_size(self.size_gb)


class _StatusManager(Protocol):
    def status(self, resource: SetupResource) -> SetupStatus: ...


def _collect_rows(specs: list[ModelSpec], manager: _StatusManager) -> list[StatusRow]:
    rows = []
    for spec in specs:
        resources = []
        for resource in spec.setup_resources:
            state = manager.status(resource)
            resources.append(
                ResourceRow(
                    resource=resource,
                    ready=state.ready,
                    detail=state.detail,
                )
            )
        rows.append(StatusRow(spec=spec, resources=tuple(resources)))
    return rows


def _echo_summary(rows: list[StatusRow]) -> None:
    total_models = len(rows)
    ready_models = sum(1 for row in rows if row.status != "missing")
    resources = _dedupe_resource_rows(rows)
    total_resources = len(resources)
    ready_resources = sum(1 for resource in resources if resource.ready)
    missing_resources = total_resources - ready_resources
    installed_size_gb = sum(
        resource.resource.disk_gb or 0.0 for resource in resources if resource.ready
    )
    total_size_gb = sum(resource.resource.disk_gb or 0.0 for resource in resources)

    click.echo("Summary")
    click.echo(f"  Models:    {ready_models} ready / {total_models} total")
    click.echo(f"  Resources: {ready_resources} ready / {total_resources} total")
    click.echo(f"  Missing:   {missing_resources}")
    click.echo(
        f"  Size:      {_format_size(installed_size_gb)} installed / "
        f"{_format_size(total_size_gb)} total"
    )


def _echo_table(rows: list[StatusRow], *, verbose: bool) -> None:
    headers = ("Domain", "Family", "Model", "Status", "Resources", "Size")
    table_rows = [
        (
            row.domain,
            row.family,
            row.model,
            row.status,
            row.resource_count,
            row.size,
        )
        for row in rows
    ]
    widths = _column_widths(headers, table_rows)
    click.echo(_format_table_row(headers, widths))
    click.echo(_format_table_row(tuple("-" * width for width in widths), widths))
    for row, table_row in zip(rows, table_rows, strict=True):
        click.echo(_format_table_row(table_row, widths))
        if verbose:
            _echo_verbose_row(row)


def _echo_verbose_row(row: StatusRow) -> None:
    click.echo(f"  repository: {row.spec.repo}")
    click.echo("  resources:")
    if not row.resources:
        click.echo("    -")
    for resource in row.resources:
        size = _format_size(resource.resource.disk_gb)
        size_suffix = f" {size}" if size != "-" else ""
        click.echo(
            f"    {resource.status:<7} {resource.resource.kind:<12} "
            f"{resource.resource.label}{size_suffix}"
        )
        if resource.detail:
            click.echo(f"      detail: {resource.detail}")
    click.echo()


def _echo_missing(rows: list[StatusRow]) -> None:
    missing = [
        resource for resource in _dedupe_resource_rows(rows) if not resource.ready
    ]
    if not missing:
        click.echo()
        click.echo("All resources are ready.")
        return

    click.echo()
    click.echo("Missing resources")
    for resource in missing:
        size = _format_size(resource.resource.disk_gb)
        size_suffix = f" {size}" if size != "-" else ""
        click.echo(
            f"  missing {resource.resource.kind} {resource.resource.label}{size_suffix}"
        )
        if resource.detail:
            click.echo(f"    detail: {resource.detail}")
        click.echo(f"    Run: kiapi activate --repo {resource.resource.label}")


def _dedupe_resource_rows(rows: list[StatusRow]) -> list[ResourceRow]:
    resources: dict[str, ResourceRow] = {}
    for row in rows:
        for resource in row.resources:
            resources.setdefault(resource.resource.key, resource)
    return list(resources.values())


def _column_widths(
    headers: tuple[str, ...],
    rows: Sequence[tuple[str, ...]],
) -> tuple[int, ...]:
    return tuple(
        max(len(row[index]) for row in (headers, *rows))
        for index in range(len(headers))
    )


def _format_table_row(row: tuple[str, ...], widths: tuple[int, ...]) -> str:
    return "  ".join(
        value.ljust(width) for value, width in zip(row, widths, strict=True)
    )


def _format_size(size_gb: float | None) -> str:
    if not size_gb:
        return "-"
    return f"~{size_gb:g} GB"
