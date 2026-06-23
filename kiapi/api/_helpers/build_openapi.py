from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

from kiapi import __version__
from kiapi.core.capability import CapabilitySpec


def build_openapi(
    app: FastAPI,
    *,
    title: str,
    path_prefixes: tuple[str, ...],
    include_paths: tuple[str, ...] = (),
    description: str | None = None,
    capability: CapabilitySpec | None = None,
) -> dict:
    routes = [
        route
        for route in app.routes
        if isinstance(route, APIRoute)
        and _path_matches(
            route.path,
            path_prefixes=path_prefixes,
            include_paths=include_paths,
        )
    ]
    schema = get_openapi(
        title=title,
        version=__version__,
        description=description,
        routes=routes,
    )

    if capability is not None:
        schema["x-kiapi-capability"] = capability.name
        schema["x-kiapi-domain"] = capability.domain
        schema["x-kiapi-root-openapi"] = "/openapi.json"

    return schema


def _path_matches(
    path: str,
    *,
    path_prefixes: tuple[str, ...],
    include_paths: tuple[str, ...],
) -> bool:
    return any(_matches_prefix(path, prefix) for prefix in path_prefixes) or path in (
        include_paths
    )


def _matches_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")
