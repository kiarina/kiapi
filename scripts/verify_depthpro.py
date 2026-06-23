"""End-to-end verification for kiapi's image (depthpro) capability.

Exercises depth estimation with the default two artifacts (PNG + NPZ), raw PNG
responses when include_depth_data=false, async polling, validation errors, and
help/models discovery.

Usage:
    # start the server first, e.g.:
    #   KIAPI_PORT=8000 KIAPI_MEMORY_LIMIT_GB=110 uv run kiapi
    uv run python scripts/verify_depthpro.py

Env:
    KIAPI_BASE_URL   server base URL (default http://127.0.0.1:8000)
"""

import io
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from PIL import Image

BASE_URL = os.environ.get("KIAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ESTIMATE_URL = f"{BASE_URL}/v1/image/depthpro/estimate"


def _poll(client: httpx.Client, job_id: str, timeout: float = 900.0) -> Any:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        j = client.get(f"{BASE_URL}/v1/jobs/{job_id}").json()
        if j["status"] not in ("queued", "running"):
            if last is not None:
                print()
            return j
        cur = (j.get("progress"), j.get("progress_label"))
        if cur[0] is not None and cur != last:
            label = f" {cur[1]}" if cur[1] else ""
            print(
                f"\r  [{job_id}] {j['status']} {cur[0] * 100:5.1f}%{label}",
                end="",
                flush=True,
            )
            last = cur
        time.sleep(1.0)
    raise TimeoutError(f"job {job_id} did not finish in {timeout}s")


def _params(**kw: Any) -> Any:
    if image_file_id := kw.pop("image_file_id", None):
        kw["image"] = {"type": "file_id", "file_id": image_file_id}
    return kw


def _png_bytes(size: int = 256) -> bytes:
    img = Image.new("RGB", (size, size), (180, 120, 210))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _upload_png(client: httpx.Client) -> str:
    r = client.post(
        f"{BASE_URL}/v1/files",
        files={"file": ("depthpro-input.png", io.BytesIO(_png_bytes()), "image/png")},
    )
    if r.status_code != 200:
        raise RuntimeError(f"upload failed: {r.status_code} {r.text[:200]}")
    return r.json()["file_id"]  # type: ignore


def main() -> None:
    verify_dir = Path(".verify/depthpro")
    if verify_dir.exists():
        shutil.rmtree(verify_dir)
    verify_dir.mkdir(parents=True, exist_ok=True)
    saved_files: dict[str, list[Path]] = {}

    results = []
    print(f"{'=' * 70}\n## kiapi depthpro verify  ({BASE_URL})\n{'=' * 70}")
    with httpx.Client(timeout=1200.0, headers={"Accept": "application/json"}) as client:

        def _save(fid: Any, filename: str) -> Path | None:
            if not fid:
                return None
            r = client.get(f"{BASE_URL}/v1/files/{fid}/download")
            if r.status_code == 200:
                path = verify_dir / filename
                path.write_bytes(r.content)
                return path
            return None

        image_id = _upload_png(client)

        # 1. Sync estimate with JSON response and the default two artifacts.
        t0 = time.time()
        r = client.post(
            ESTIMATE_URL,
            json=_params(
                mode="sync",
                model="base",
                image_file_id=image_id,
                quantize=8,
            ),
        )
        body = r.json() if r.status_code == 200 else {}
        result = body.get("result") or {}
        ok = (
            r.status_code == 200
            and body.get("status") == "succeeded"
            and len(body.get("artifacts") or []) == 2
            and result.get("depth_image_file_id")
            and result.get("depth_data_file_id")
            and result.get("array_shape")
        )
        print(
            f"[1] {'✓' if ok else '✗'} ({time.time() - t0:5.1f}s) sync estimate -> PNG + NPZ artifacts"
        )
        results.append(("1", bool(ok)))
        if ok:
            img_id = result.get("depth_image_file_id")
            if p := _save(img_id, f"1_sync_depth_{img_id}.png"):
                saved_files.setdefault("1", []).append(p)
            dat_id = result.get("depth_data_file_id")
            if p := _save(dat_id, f"1_sync_data_{dat_id}.npz"):
                saved_files.setdefault("1", []).append(p)
        if "--fast" in sys.argv:
            print("\n[FAST MODE] Exiting early.")
            sys.exit(0 if results[-1][1] else 1)

        # 2. Download and validate the raw NPZ artifact.
        ok2 = False
        if result.get("depth_data_file_id"):
            d = client.get(
                f"{BASE_URL}/v1/files/{result['depth_data_file_id']}/download"
            )
            if d.status_code == 200:
                with np.load(io.BytesIO(d.content)) as data:
                    ok2 = (
                        "depth" in data and "min_depth" in data and "max_depth" in data
                    )
        print(f"[2] {'✓' if ok2 else '✗'} depth data artifact -> valid NPZ")
        results.append(("2", bool(ok2)))
        if ok2:
            path = verify_dir / "2_valid_data.npz"
            path.write_bytes(d.content)
            saved_files.setdefault("2", []).append(path)

        # 3. Raw PNG content negotiation when only one artifact is produced.
        rr = client.post(
            ESTIMATE_URL,
            headers={"Accept": "*/*"},
            json=_params(
                mode="sync",
                model="base",
                image_file_id=image_id,
                include_depth_data=False,
            ),
        )
        raw_ok = (
            rr.status_code == 200
            and rr.headers.get("content-type") == "image/png"
            and rr.content[:8] == b"\x89PNG\r\n\x1a\n"
            and rr.headers.get("x-kiapi-file-id", "").startswith("file_")
        )
        print(
            f"[3] {'✓' if raw_ok else '✗'} raw PNG via include_depth_data=false + Accept:*/*"
        )
        results.append(("3", bool(raw_ok)))
        if raw_ok:
            path = verify_dir / "3_raw.png"
            path.write_bytes(rr.content)
            saved_files.setdefault("3", []).append(path)

        # 4. Async estimate + poll.
        t0 = time.time()
        sub = client.post(
            ESTIMATE_URL,
            json=_params(
                mode="async",
                model="base",
                image_file_id=image_id,
                include_depth_data=False,
            ),
        )
        ok4 = sub.status_code == 202 and "job_id" in sub.json()
        if ok4:
            job = _poll(client, sub.json()["job_id"])
            ok4 = job["status"] == "succeeded" and bool(job["artifacts"])
        print(
            f"[4] {'✓' if ok4 else '✗'} ({time.time() - t0:5.1f}s) async estimate -> poll to succeeded"
        )
        results.append(("4", bool(ok4)))
        if ok4:
            r_dict = job.get("result") or {}
            img_id = r_dict.get("depth_image_file_id")
            if p := _save(img_id, f"4_async_depth_{img_id}.png"):
                saved_files.setdefault("4", []).append(p)
            dat_id = r_dict.get("depth_data_file_id")
            if p := _save(dat_id, f"4_async_data_{dat_id}.npz"):
                saved_files.setdefault("4", []).append(p)

        # 5. Unknown image_file_id -> 400.
        r = client.post(
            ESTIMATE_URL,
            json=_params(model="base", image_file_id="file_does_not_exist"),
        )
        ok5 = r.status_code == 400
        print(
            f"[5] {'✓' if ok5 else '✗'} unknown image_file_id -> 400 (got {r.status_code})"
        )
        results.append(("5", ok5))

        # 6. Bad quantize -> 422.
        r = client.post(
            ESTIMATE_URL,
            json=_params(model="base", image_file_id=image_id, quantize=7),
        )
        ok6 = r.status_code == 422
        print(
            f"[6] {'✓' if ok6 else '✗'} invalid quantize -> 422 (got {r.status_code})"
        )
        results.append(("6", ok6))

        # 7. Discovery: models + help list depthpro.
        m = client.get(f"{BASE_URL}/v1/image/depthpro/models").json()
        has_models = any(
            x["family"] == "depthpro" and x["domain"] == "image" for x in m
        )
        h = client.get(f"{BASE_URL}/v1/image/depthpro/openapi.json")
        ok7 = (
            has_models
            and h.status_code == 200
            and h.json().get("x-kiapi-capability") == "depthpro"
        )
        print(
            f"[7] {'✓' if ok7 else '✗'} discovery: /v1/image/depthpro/models + /v1/image/depthpro/openapi.json"
        )
        results.append(("7", bool(ok7)))

    print(f"\n{'=' * 70}\n## SUMMARY\n{'=' * 70}")
    passed = sum(1 for _, ok in results if ok)
    for cid, ok in results:
        if not ok:
            print(f"  FAIL: {cid}")
        else:
            files = saved_files.get(cid)
            if files:
                file_list = ", ".join(str(f) for f in files)
                print(f"  PASS: {cid} (Saved: {file_list})")
            else:
                print(f"  PASS: {cid}")
    print(f"\n{passed}/{len(results)} passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
