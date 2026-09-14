from fastapi import APIRouter, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse

from kiapi.api._helpers.build_openapi import build_openapi
from kiapi.api._views.capability_model_spec import CapabilityModelSpec
from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import model_registry


def register_capability_endpoints(
    router: APIRouter,
    *,
    name: str,
    base_path: str,
) -> None:
    """Register the shared per-capability tail endpoints on ``router``.

    Every capability exposes the same four boilerplate endpoints that differ
    only by capability ``name`` (== family == model-registry token) and the
    ``base_path`` under which they live:

    - ``GET {base_path}/models``        — public model catalog for ``name``
    - ``GET {base_path}/openapi.json``  — capability OpenAPI (operation layer)
    - ``GET {base_path}/docs``          — Swagger UI for that OpenAPI
    - ``GET {base_path}/redoc``         — ReDoc for that OpenAPI

    The capability spec is resolved per-request (it may not be registered when
    the router module is imported), mirroring the previous hand-written handlers.
    """

    def _spec() -> CapabilitySpec:
        spec = capability_spec_registry.get(name)
        if spec is None:
            raise RuntimeError(f"kiapi capability {name!r} is not registered")
        return spec

    @router.get(f"{base_path}/models", response_model=list[CapabilityModelSpec])
    async def list_models() -> list[CapabilityModelSpec]:
        """List the servable models for this capability.

        Returns the public catalog of every variant selectable via the ``model``
        field on this capability's endpoints.
        """
        return [
            CapabilityModelSpec.from_model_spec(spec)
            for spec in model_registry.list_specs(name)
        ]

    @router.get(f"{base_path}/openapi.json", include_in_schema=False)
    async def capability_openapi(request: Request) -> dict:
        spec = _spec()
        return build_openapi(
            request.app,
            title=spec.title,
            description=spec.description,
            path_prefixes=spec.path_prefixes,
            include_paths=spec.include_paths,
            capability=spec,
        )

    @router.get(f"{base_path}/docs", include_in_schema=False)
    async def capability_docs() -> HTMLResponse:
        spec = _spec()
        return get_swagger_ui_html(openapi_url=spec.openapi_path, title=spec.title)

    @router.get(f"{base_path}/redoc", include_in_schema=False)
    async def capability_redoc() -> HTMLResponse:
        spec = _spec()
        return get_redoc_html(openapi_url=spec.openapi_path, title=spec.title)
