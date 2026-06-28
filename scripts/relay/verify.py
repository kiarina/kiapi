"""End-to-end relay verification through LocalRelay.

Start kiapi with LocalRelay first, for example:

    KIAPI_RELAY_LOCAL_NODE_ID=local \
    KIAPI_RELAY_LOCAL_ROOT=/tmp/kiapi/relay \
    KIAPI_RELAY_LOCAL_PREFIX=kiapi \
    uv run kiapi run --relay local

Then run:

    uv run python scripts/relay/verify.py

This script intentionally exercises real capability endpoints through the relay
path. It is heavier than verify_local.py.
"""

from __future__ import annotations

import asyncio
import base64
import os
import sys
import time
from pathlib import Path
from typing import Any, cast

from _helpers import (
    assert_json,
    consume_body,
    data_url,
    query_path,
    relay_request,
    run_checks,
)

from kiapi_relay import Relay
from kiapi_relay.impl.local import create_local_relay

HERE = Path(__file__).resolve().parents[2]
ASSETS = Path(os.environ.get("KIAPI_ASSETS_DIR", HERE / "tests" / "assets"))
IMAGE = Path(os.environ.get("KIAPI_IMAGE", ASSETS / "miineko.png"))
UPLOAD_BYTES = b"relay multipart upload\n"


async def main() -> int:
    fast = "--fast" in sys.argv
    client = create_local_relay()
    state: dict[str, Any] = {}

    async def health() -> str:
        result = await relay_request(client, "GET", "/health", timeout_s=60.0)
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["status"] == "ok", body
        return "GET /health"

    async def files_list() -> str:
        result = await relay_request(client, "GET", "/v1/files", timeout_s=60.0)
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["object"] == "list", body
        return f"{len(body['data'])} files listed"

    async def jobs_list() -> str:
        result = await relay_request(client, "GET", "/v1/jobs", timeout_s=60.0)
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["object"] == "list", body
        return f"{len(body['data'])} jobs listed"

    async def files_upload() -> str:
        result = await relay_request(
            client,
            "POST",
            "/v1/files",
            headers={"Accept": "application/json"},
            multipart={
                "files": [
                    {
                        "field": "file",
                        "filename": "relay-upload.txt",
                        "content_type": "text/plain",
                        "content_base64": base64.b64encode(UPLOAD_BYTES).decode(
                            "ascii"
                        ),
                    }
                ]
            },
            timeout_s=60.0,
        )
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["file_id"], body
        assert body["filename"] == "relay-upload.txt", body
        assert body["content_type"] == "text/plain", body
        state["uploaded_file_id"] = body["file_id"]
        return f"file_id={body['file_id']}"

    async def chat_text() -> str:
        result = await relay_request(
            client,
            "POST",
            "/v1/chat/completions",
            body={
                "messages": [{"role": "user", "content": "Say hello in one word."}],
                "max_completion_tokens": 16,
            },
            timeout_s=1200.0,
        )
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["choices"][0]["message"]["content"], body
        return "non-stream text completion"

    async def chat_media() -> str:
        result = await relay_request(
            client,
            "POST",
            "/v1/chat/completions",
            body={
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What animal is in this image?"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": data_url(IMAGE, "image/png"),
                                },
                            },
                        ],
                    }
                ],
                "max_completion_tokens": 48,
            },
            timeout_s=1200.0,
        )
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["choices"][0]["message"]["content"], body
        return "image input completion"

    async def chat_stream() -> str:
        result = await relay_request(
            client,
            "POST",
            "/v1/chat/completions",
            body={
                "messages": [{"role": "user", "content": "Count to three."}],
                "stream": True,
                "max_completion_tokens": 32,
            },
            timeout_s=1200.0,
        )
        body = assert_json(result)
        assert result.status == 200, result.status
        assert isinstance(body, list), body
        assert body and body[-1] == "[DONE]", body[-3:]
        return f"{len(body)} stream events"

    async def embedding_text() -> str:
        result = await relay_request(
            client,
            "POST",
            "/v1/embedding",
            body={"text": "relay text embedding"},
            timeout_s=600.0,
        )
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["dimension"] == len(body["embedding"]), body
        return f"dimension={body['dimension']}"

    async def embedding_image() -> str:
        result = await relay_request(
            client,
            "POST",
            "/v1/embedding",
            body={"model": "vl", "image": data_url(IMAGE, "image/png")},
            timeout_s=600.0,
        )
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["dimension"] == len(body["embedding"]), body
        return f"dimension={body['dimension']}"

    async def ernie_generate() -> str:
        result = await relay_request(
            client,
            "POST",
            "/v1/image/ernie/generate",
            headers={"Accept": "application/json"},
            body={
                "mode": "sync",
                "model": os.environ.get("KIAPI_ERNIE_MODEL", "turbo"),
                "prompt": "a tiny ceramic cup on a desk",
                "width": int(os.environ.get("KIAPI_RELAY_VERIFY_IMAGE_WIDTH", "256")),
                "height": int(os.environ.get("KIAPI_RELAY_VERIFY_IMAGE_HEIGHT", "256")),
                "steps": int(os.environ.get("KIAPI_RELAY_VERIFY_IMAGE_STEPS", "8")),
                "seed": 11,
            },
            timeout_s=2400.0,
        )
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["status"] == "succeeded", body
        state["image_file_id"] = body["artifacts"][0]
        state["image_job_id"] = body["id"]
        return f"file_id={state['image_file_id']}"

    async def ernie_edit() -> str:
        result = await relay_request(
            client,
            "POST",
            "/v1/image/ernie/edit",
            headers={"Accept": "application/json"},
            body={
                "mode": "sync",
                "model": os.environ.get("KIAPI_ERNIE_MODEL", "turbo"),
                "prompt": "turn this into a soft watercolor poster",
                "image": {"type": "data_url", "data_url": data_url(IMAGE, "image/png")},
                "image_strength": 0.55,
                "width": int(os.environ.get("KIAPI_RELAY_VERIFY_IMAGE_WIDTH", "256")),
                "height": int(os.environ.get("KIAPI_RELAY_VERIFY_IMAGE_HEIGHT", "256")),
                "steps": int(os.environ.get("KIAPI_RELAY_VERIFY_IMAGE_STEPS", "8")),
                "seed": 12,
            },
            timeout_s=2400.0,
        )
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["status"] == "succeeded", body
        assert body["artifacts"], body
        return f"file_id={body['artifacts'][0]}"

    async def audiogen_sync() -> str:
        result = await relay_request(
            client,
            "POST",
            "/v1/audio/audiogen/generate",
            headers={"Accept": "application/json"},
            body={
                "mode": "sync",
                "prompt": "soft rain on a window",
                "duration": float(os.environ.get("KIAPI_RELAY_VERIFY_AUDIO_S", "1.5")),
                "seed": 21,
            },
            timeout_s=900.0,
        )
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["status"] == "succeeded", body
        state["audio_file_id"] = body["artifacts"][0]
        return f"file_id={state['audio_file_id']}"

    async def audiogen_async() -> str:
        result = await relay_request(
            client,
            "POST",
            "/v1/audio/audiogen/generate",
            headers={"Accept": "application/json"},
            body={
                "mode": "async",
                "prompt": "single bell chime",
                "duration": float(os.environ.get("KIAPI_RELAY_VERIFY_AUDIO_S", "1.5")),
                "seed": 22,
            },
            timeout_s=120.0,
        )
        body = assert_json(result)
        assert result.status == 202, result.status
        job = await _poll_job(client, body["job_id"], timeout_s=900.0)
        assert job["status"] == "succeeded", job
        state["async_job_id"] = body["job_id"]
        return f"job_id={body['job_id']}"

    async def ltx2_text2video() -> str:
        result = await relay_request(
            client,
            "POST",
            "/v1/video/ltx2/generate",
            headers={"Accept": "application/json"},
            body={
                "mode": "sync",
                "prompt": "clouds drifting slowly",
                "width": int(os.environ.get("KIAPI_RELAY_VERIFY_VIDEO_WIDTH", "256")),
                "height": int(os.environ.get("KIAPI_RELAY_VERIFY_VIDEO_HEIGHT", "256")),
                "num_frames": int(
                    os.environ.get("KIAPI_RELAY_VERIFY_VIDEO_FRAMES", "17")
                ),
                "fps": 24,
                "seed": 31,
            },
            timeout_s=1800.0,
        )
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["status"] == "succeeded", body
        assert body["result"]["mode"] == "T2V", body
        state["video_file_id"] = body["artifacts"][0]
        return f"file_id={state['video_file_id']}"

    async def ltx2_image2video() -> str:
        result = await relay_request(
            client,
            "POST",
            "/v1/video/ltx2/generate",
            headers={"Accept": "application/json"},
            body={
                "mode": "sync",
                "prompt": "gentle camera zoom",
                "image": {"type": "data_url", "data_url": data_url(IMAGE, "image/png")},
                "width": int(os.environ.get("KIAPI_RELAY_VERIFY_VIDEO_WIDTH", "256")),
                "height": int(os.environ.get("KIAPI_RELAY_VERIFY_VIDEO_HEIGHT", "256")),
                "num_frames": int(
                    os.environ.get("KIAPI_RELAY_VERIFY_VIDEO_FRAMES", "17")
                ),
                "fps": 24,
                "seed": 32,
            },
            timeout_s=1800.0,
        )
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["status"] == "succeeded", body
        assert body["result"]["mode"] == "I2V", body
        return f"file_id={body['artifacts'][0]}"

    async def web_search() -> str:
        result = await relay_request(
            client,
            "POST",
            "/v1/web/search",
            body={"query": "kiapi github", "max_results": 3},
            timeout_s=300.0,
        )
        body = assert_json(result)
        assert result.status == 200, result.status
        assert isinstance(body["results"], list), body
        return f"{len(body['results'])} results"

    async def web_fetch() -> str:
        result = await relay_request(
            client,
            "GET",
            query_path("/v1/web/fetch", url="https://example.com"),
            headers={"Accept": "text/markdown"},
            timeout_s=300.0,
        )
        assert result.status == 200, result.status
        content = consume_body(result)
        assert b"Example Domain" in content, content[:120]
        file_id = result.headers.get("x-kiapi-file-id")
        assert file_id, result.headers
        state["fetch_file_id"] = file_id
        return f"file_id={file_id}"

    async def file_metadata_download_delete() -> str:
        file_id = (
            state.get("uploaded_file_id")
            or state.get("fetch_file_id")
            or state.get("image_file_id")
        )
        assert file_id, "no file_id captured from earlier checks"
        metadata = await relay_request(
            client, "GET", f"/v1/files/{file_id}", timeout_s=60.0
        )
        body = assert_json(metadata)
        assert metadata.status == 200, metadata.status
        assert body["file_id"] == file_id, body

        download = await relay_request(
            client, "GET", f"/v1/files/{file_id}/download", timeout_s=120.0
        )
        assert download.status == 200, download.status
        content = consume_body(download)
        assert content, "empty download"
        if file_id == state.get("uploaded_file_id"):
            assert content == UPLOAD_BYTES, content

        deleted = await relay_request(
            client, "DELETE", f"/v1/files/{file_id}", timeout_s=60.0
        )
        deleted_body = assert_json(deleted)
        assert deleted.status == 200, deleted.status
        assert deleted_body["deleted"] is True, deleted_body
        return f"metadata/download/delete {file_id}"

    async def job_get_delete() -> str:
        job_id = state.get("async_job_id") or state.get("image_job_id")
        assert job_id, "no job_id captured from earlier checks"
        result = await relay_request(
            client, "GET", f"/v1/jobs/{job_id}", timeout_s=60.0
        )
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["id"] == job_id, body

        deleted = await relay_request(
            client, "DELETE", f"/v1/jobs/{job_id}", timeout_s=60.0
        )
        deleted_body = assert_json(deleted)
        assert deleted.status == 200, deleted.status
        assert deleted_body["deleted"] is True, deleted_body
        return f"get/delete {job_id}"

    checks = [
        ("core /health", health),
        ("core /v1/files list", files_list),
        ("core /v1/jobs list", jobs_list),
        ("core /v1/files upload multipart", files_upload),
        ("chat text non-stream", chat_text),
        ("chat image input", chat_media),
        ("chat text stream", chat_stream),
        ("embedding text", embedding_text),
        ("embedding image", embedding_image),
        ("image ernie generate sync", ernie_generate),
        ("image ernie edit sync", ernie_edit),
        ("audio audiogen generate sync", audiogen_sync),
        ("audio audiogen generate async", audiogen_async),
        ("video ltx2 text2video", ltx2_text2video),
        ("video ltx2 image2video", ltx2_image2video),
        ("web search", web_search),
        ("web fetch", web_fetch),
        ("core /v1/files metadata/download/delete", file_metadata_download_delete),
        ("core /v1/jobs get/delete", job_get_delete),
    ]

    return await run_checks(checks, fast=fast)


async def _poll_job(client: Relay, job_id: str, *, timeout_s: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        result = await relay_request(
            client, "GET", f"/v1/jobs/{job_id}", timeout_s=60.0
        )
        body = assert_json(result)
        if body["status"] not in {"queued", "running"}:
            return cast(dict[str, Any], body)
        progress = body.get("progress")
        label = body.get("progress_label") or ""
        if isinstance(progress, int | float):
            print(f"  job {job_id}: {progress * 100:.1f}% {label}".rstrip())
        else:
            print(f"  job {job_id}: {body['status']}")
        await asyncio.sleep(1.0)
    raise TimeoutError(f"job {job_id} did not finish in {timeout_s}s")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
