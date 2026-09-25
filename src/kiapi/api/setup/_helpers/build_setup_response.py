from typing import Literal, Protocol

from kiapi.core.model import ModelSpec
from kiapi.core.setup import SetupResource, SetupStatus

from .._views.setup_model_state import SetupModelState
from .._views.setup_resource_state import SetupResourceState
from .._views.setup_response import SetupResponse
from .._views.setup_summary import SetupSummary


class _StatusManager(Protocol):
    def status(self, resource: SetupResource) -> SetupStatus: ...


def build_setup_response(
    specs: list[ModelSpec], manager: _StatusManager
) -> SetupResponse:
    # Models often share a resource (e.g. SeedVR2 3b and 7b), so check each once.
    states: dict[str, SetupResourceState] = {}
    models = []
    for spec in sorted(specs, key=lambda s: (s.domain, s.family)):
        resources = []
        for resource in spec.setup_resources:
            if resource.key not in states:
                status = manager.status(resource)
                states[resource.key] = SetupResourceState(
                    kind=resource.kind,
                    label=resource.label,
                    ready=status.ready,
                    disk_gb=resource.disk_gb,
                    detail=status.detail,
                    activate_command=f"kiapi activate --repo {resource.label}",
                )
            resources.append(states[resource.key])
        models.append(
            SetupModelState(
                domain=spec.domain,
                family=spec.family,
                name=spec.name,
                default=spec.default,
                status=_model_status(resources),
                size_gb=sum(r.disk_gb or 0.0 for r in resources),
                resources=resources,
            )
        )

    unique = list(states.values())
    summary = SetupSummary(
        models_total=len(models),
        models_ready=sum(1 for m in models if m.status != "missing"),
        resources_total=len(unique),
        resources_ready=sum(1 for r in unique if r.ready),
        installed_gb=sum(r.disk_gb or 0.0 for r in unique if r.ready),
        total_gb=sum(r.disk_gb or 0.0 for r in unique),
    )
    return SetupResponse(summary=summary, data=models)


def _model_status(
    resources: list[SetupResourceState],
) -> Literal["ready", "missing", "none"]:
    if not resources:
        return "none"
    return "ready" if all(r.ready for r in resources) else "missing"
