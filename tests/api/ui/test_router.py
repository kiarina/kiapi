from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from kiapi.api.ui import router as ui_router


def _client(static_dir: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(ui_router, "STATIC_DIR", static_dir)
    app = FastAPI()
    app.include_router(ui_router.router)
    app.mount(
        ui_router.ASSETS_PATH,
        StaticFiles(directory=static_dir / "_ui", check_dir=False),
    )
    return TestClient(app)


def test_index_explains_how_to_build_when_ui_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    response = _client(tmp_path, monkeypatch).get("/")

    assert response.status_code == 200
    assert "mise run web:build" in response.text


def test_index_and_assets_are_served_when_built(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "_ui").mkdir()
    (tmp_path / "index.html").write_text("<div id=root></div>")
    (tmp_path / "_ui" / "app.js").write_text("console.log(1)")
    client = _client(tmp_path, monkeypatch)

    index = client.get("/")
    asset = client.get("/_ui/app.js")

    assert index.text == "<div id=root></div>"
    assert index.headers["cache-control"] == "no-cache"
    assert asset.status_code == 200
    assert asset.text == "console.log(1)"
