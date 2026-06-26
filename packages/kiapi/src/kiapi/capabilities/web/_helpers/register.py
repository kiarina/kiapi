from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import DockerImageResource

from .._constants.description import DESCRIPTION
from .._models import crawl4ai, searxng
from .._settings import settings_manager


def register() -> None:
    capability_spec_registry.register(
        CapabilitySpec(
            name="web",
            domain="web",
            title="kiapi Web API",
            summary="Search the web and fetch pages as Markdown or PDF artifacts.",
            description=DESCRIPTION,
            openapi_path="/v1/web/openapi.json",
            docs_path="/v1/web/docs",
            redoc_path="/v1/web/redoc",
            path_prefixes=("/v1/web",),
        )
    )

    settings = settings_manager.get_settings()

    model_registry.register(
        ModelSpec(
            name="search",
            family="web",
            domain="web",
            repo=settings.search_image,
            module=searxng,
            weight_gb=0.5,
            peak_headroom_gb=0.2,
            framework="rss",
            priority=0,
            default=True,
            setup_resources=(
                DockerImageResource(image=settings.search_image, disk_gb=0.4),
            ),
        )
    )
    model_registry.register(
        ModelSpec(
            name="fetch",
            family="web",
            domain="web",
            repo=settings.fetch_image,
            module=crawl4ai,
            weight_gb=1.0,
            peak_headroom_gb=1.0,
            framework="rss",
            priority=0,
            setup_resources=(
                DockerImageResource(image=settings.fetch_image, disk_gb=9.6),
            ),
        )
    )
