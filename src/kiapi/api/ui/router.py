"""Web UI: serves the built single-page app at `/` and its assets under `/_ui`."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).parent / "static"
ASSETS_PATH = "/_ui"

router = APIRouter(include_in_schema=False)

# Source checkouts have no built UI until `mise run web:build` runs.
_NOT_BUILT = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>kiapi</title></head>
<body style="font-family: system-ui, sans-serif; margin: 48px">
<h1>kiapi</h1>
<p>The web UI is not built. Run <code>mise run web:build</code>, or use the
<a href="/docs">API docs</a>.</p>
</body></html>
"""


@router.get("/", response_model=None)
async def index() -> FileResponse | HTMLResponse:
    index_html = STATIC_DIR / "index.html"
    if not index_html.is_file():
        return HTMLResponse(_NOT_BUILT)
    return FileResponse(index_html, headers={"Cache-Control": "no-cache"})


assets = StaticFiles(directory=STATIC_DIR / "_ui", check_dir=False)
