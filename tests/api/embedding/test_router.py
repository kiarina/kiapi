import asyncio
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from kiapi.api import get_ctx, get_worker
from kiapi.api.embedding import router as router_module
from kiapi.capabilities import CapabilityError


class _Worker:
    async def submit(self, job: Any, fn: Callable[[], Any]) -> asyncio.Future[Any]:
        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        try:
            future.set_result(fn())
        except Exception as exc:
            future.set_exception(exc)
        return future


class _JobStore:
    def create(self, **kwargs: Any) -> object:
        return object()


class _Ctx:
    job_store = _JobStore()


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(router_module.router)
    app.dependency_overrides[get_ctx] = _Ctx
    app.dependency_overrides[get_worker] = _Worker
    with TestClient(app) as test_client:
        yield test_client


def _response() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [{"object": "embedding", "index": 0, "embedding": [1.0]}],
        "model": "m",
        "usage": {"prompt_tokens": 1, "total_tokens": 1},
        "timings": {"total_s": 0.1},
    }


def test_embeddings_returns_openai_shape(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(router_module, "handle_embed", lambda ctx, req: _response())

    response = client.post("/v1/embeddings", json={"input": "hello"})

    assert response.status_code == 200
    assert response.json() == _response()


def test_old_path_is_gone(client: TestClient) -> None:
    assert client.post("/v1/embedding", json={"text": "hello"}).status_code == 404


def test_capability_error_returns_400(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(ctx: Any, req: Any) -> None:
        raise CapabilityError("bad input")

    monkeypatch.setattr(router_module, "handle_embed", fail)

    response = client.post("/v1/embeddings", json={"input": "hello"})

    assert response.status_code == 400
    assert response.json() == {"detail": "bad input"}


def test_token_arrays_are_rejected(client: TestClient) -> None:
    response = client.post("/v1/embeddings", json={"input": [1, 2, 3]})

    assert response.status_code == 422
