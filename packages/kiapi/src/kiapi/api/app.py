import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse

from kiapi.api import build_openapi
from kiapi.core.app import AppContext
from kiapi.core.capability import capability_spec_registry
from kiapi.core.logging import setup_logger
from kiapi.core.model import model_registry
from kiapi.core.worker import create_worker
from kiapi_relay import RelayRunner, relay_registry
from kiapi_relay import settings_manager as relay_settings_manager

from .audio.acestep.router import router as acestep_router
from .audio.audiogen.router import router as audiogen_router
from .chat.router import router as chat_router
from .embedding.router import router as embedding_router
from .files.router import router as files_router
from .health.router import router as health_router
from .image.depthpro.router import router as depthpro_router
from .image.ernie.router import router as ernie_router
from .image.flux2.router import router as flux2_router
from .image.ideogram4.router import router as ideogram4_router
from .image.qwen.router import router as qwen_router
from .image.seedvr2.router import router as seedvr2_router
from .image.zimage.router import router as zimage_router
from .jobs.router import router as jobs_router
from .models.router import router as models_router
from .video.ltx2.router import router as ltx2_router
from .web.router import router as web_router

logger = logging.getLogger(__name__)

COMMON_OPENAPI_PATHS = (
    "/health",
    "/v1/files",
    "/v1/jobs",
)
CAPABILITY_DESCRIPTION_DOMAIN_ORDER = (
    "chat",
    "embedding",
    "image",
    "audio",
    "video",
    "web",
)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    setup_logger()

    if not model_registry.list_specs() or not capability_spec_registry.list_specs():
        raise RuntimeError(
            "kiapi capabilities are not registered. "
            "Start the server with `kiapi run` instead of importing the ASGI app directly."
        )

    ctx = AppContext.create()
    worker = create_worker(ctx)

    app.state.ctx = ctx
    app.state.worker = worker

    worker.start()
    asyncio.create_task(worker.warmup())  # noqa: RUF006

    relay_runner: RelayRunner | None = None

    if relay_settings_manager.get_settings().default is not None:
        relay_runner = RelayRunner(relay_registry.resolve(), app)
        relay_runner.start()
        app.state.relay_runner = relay_runner

    yield

    if relay_runner is not None:
        await relay_runner.stop()

    await worker.stop()


app = FastAPI(title="kiapi", lifespan=lifespan, docs_url=None, redoc_url=None)


def root_openapi() -> dict:
    return build_openapi(
        app,
        title="kiapi Common API",
        description=_root_openapi_description(),
        path_prefixes=COMMON_OPENAPI_PATHS,
    )


def _root_openapi_description() -> str:
    lines = [
        "Common kiapi endpoints.",
        "",
        "Capability-specific docs:",
    ]
    specs = capability_spec_registry.list_specs()
    for domain in CAPABILITY_DESCRIPTION_DOMAIN_ORDER:
        domain_specs = [spec for spec in specs if spec.domain == domain]
        if not domain_specs:
            continue
        lines.append(f"- **{domain}**")
        for spec in domain_specs:
            lines.append(
                f"  - **{spec.title}** - {spec.summary} "
                f"[Swagger UI]({spec.docs_path}), "
                f"[ReDoc]({spec.redoc_path}), "
                f"[OpenAPI JSON]({spec.openapi_path})"
            )
    for spec in specs:
        if spec.domain in CAPABILITY_DESCRIPTION_DOMAIN_ORDER:
            continue
        if f"- **{spec.domain}**" not in lines:
            lines.append(f"- **{spec.domain}**")
        lines.append(
            f"  - **{spec.title}** - {spec.summary} "
            f"[Swagger UI]({spec.docs_path}), "
            f"[ReDoc]({spec.redoc_path}), "
            f"[OpenAPI JSON]({spec.openapi_path})"
        )
    return "\n".join(lines)


app.openapi = root_openapi  # type: ignore[method-assign]


@app.get("/docs", include_in_schema=False)
async def root_docs() -> HTMLResponse:
    return get_swagger_ui_html(openapi_url="/openapi.json", title="kiapi Common API")


@app.get("/redoc", include_in_schema=False)
async def root_redoc() -> HTMLResponse:
    return get_redoc_html(openapi_url="/openapi.json", title="kiapi Common API")


app.include_router(health_router)
app.include_router(files_router)
app.include_router(jobs_router)
app.include_router(chat_router)
app.include_router(models_router)
app.include_router(embedding_router)
app.include_router(depthpro_router)
app.include_router(ernie_router)
app.include_router(flux2_router)
app.include_router(ideogram4_router)
app.include_router(qwen_router)
app.include_router(seedvr2_router)
app.include_router(zimage_router)
app.include_router(acestep_router)
app.include_router(audiogen_router)
app.include_router(ltx2_router)
app.include_router(web_router)
