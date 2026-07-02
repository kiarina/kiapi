"""End-to-end verification for kiapi's image (seedvr2) capability.

Exercises sync upscale, raw image responses, async polling, validation errors,
and help/models discovery.

Usage:
    # start the server first, e.g.:
    #   KIAPI_PORT=8000 KIAPI_MEMORY_LIMIT_GB=110 uv run kiapi
    uv run python scripts/capabilities/verify_seedvr2.py

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
from PIL import Image

BASE_URL = os.environ.get("KIAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
UPSCALE_URL = f"{BASE_URL}/v1/image/seedvr2/upscale"


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
        files={"file": ("seedvr2-input.png", io.BytesIO(_png_bytes()), "image/png")},
    )
    if r.status_code != 200:
        raise RuntimeError(f"upload failed: {r.status_code} {r.text[:200]}")
    return r.json()["file_id"]  # type: ignore


def main() -> None:
    verify_dir = Path(os.environ.get("KIAPI_VERIFY_DIR", ".verify")) / "seedvr2"
    if verify_dir.exists():
        shutil.rmtree(verify_dir)
    verify_dir.mkdir(parents=True, exist_ok=True)
    saved_files: dict[str, list[Path]] = {}

    results: list[tuple[str, bool]] = []
    print(f"{'=' * 70}\n## kiapi seedvr2 verify  ({BASE_URL})\n{'=' * 70}")
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

        # 1. sync upscale with JSON response.
        t0 = time.time()
        r = client.post(
            UPSCALE_URL,
            json=_params(
                mode="sync",
                model="3b",
                image_file_id=image_id,
                resolution="2x",
                softness=0.0,
                seed=1,
            ),
        )
        body = r.json() if r.status_code == 200 else {}
        ok = (
            r.status_code == 200
            and body.get("status") == "succeeded"
            and (body.get("result") or {}).get("params", {}).get("kind") == "upscale"
            and (body.get("result") or {}).get("width") == 512
        )
        print(
            f"[1] {'✓' if ok else '✗'} ({time.time() - t0:5.1f}s) sync upscale -> 512px artifact"
        )
        results.append(("1", bool(ok)))
        if ok:
            fid1 = body.get("artifacts", [None])[0]
            if p := _save(fid1, f"1_sync_{fid1}.png"):
                saved_files.setdefault("1", []).append(p)
        if "--fast" in sys.argv:
            print("\n[FAST MODE] Exiting early.")
            sys.exit(0 if results[-1][1] else 1)

        # 1b. raw-bytes content negotiation.
        rr = client.post(
            UPSCALE_URL,
            headers={"Accept": "*/*"},
            json=_params(
                mode="sync",
                model="3b",
                image_file_id=image_id,
                resolution="2x",
                seed=2,
            ),
        )
        raw_ok = (
            rr.status_code == 200
            and rr.headers.get("content-type") == "image/png"
            and rr.content[:8] == b"\x89PNG\r\n\x1a\n"
            and rr.headers.get("x-kiapi-file-id", "").startswith("file_")
        )
        print(
            f"[1b] {'✓' if raw_ok else '✗'} raw bytes via Accept:*/* + X-Kiapi-File-Id"
        )
        results.append(("1b", bool(raw_ok)))
        if raw_ok:
            path = verify_dir / "1b_raw.png"
            path.write_bytes(rr.content)
            saved_files.setdefault("1b", []).append(path)

        # 2. async upscale with shortest-edge target.
        t0 = time.time()
        sub = client.post(
            UPSCALE_URL,
            json=_params(
                mode="async",
                model="3b",
                image_file_id=image_id,
                resolution=512,
                seed=3,
            ),
        )
        ok2 = sub.status_code == 202 and "job_id" in sub.json()
        fid = None
        if ok2:
            job = _poll(client, sub.json()["job_id"])
            ok2 = job["status"] == "succeeded" and bool(job["artifacts"])
            fid = job["artifacts"][0] if ok2 else None
        if fid:
            d = client.get(f"{BASE_URL}/v1/files/{fid}/download")
            ok2 = ok2 and d.status_code == 200 and d.content[:8] == b"\x89PNG\r\n\x1a\n"
            if ok2:
                path = verify_dir / f"2_async_{fid}.png"
                path.write_bytes(d.content)
                saved_files.setdefault("2", []).append(path)
        print(
            f"[2] {'✓' if ok2 else '✗'} ({time.time() - t0:5.1f}s) async upscale -> poll + download PNG"
        )
        results.append(("2", bool(ok2)))

        # 3. bad scale -> 422
        r = client.post(
            UPSCALE_URL,
            json=_params(model="3b", image_file_id=image_id, resolution="99x"),
        )
        ok3 = r.status_code == 422
        print(f"[3] {'✓' if ok3 else '✗'} too-large scale -> 422 (got {r.status_code})")
        results.append(("3", ok3))

        # 4. unknown file ID -> 400
        r = client.post(
            UPSCALE_URL, json=_params(model="3b", image_file_id="file_does_not_exist")
        )
        ok4 = r.status_code == 400
        print(
            f"[4] {'✓' if ok4 else '✗'} unknown image_file_id -> 400 (got {r.status_code})"
        )
        results.append(("4", ok4))

        # 5. discovery: models + help list seedvr2
        m = client.get(f"{BASE_URL}/v1/image/seedvr2/models").json()
        has_models = any(x["family"] == "seedvr2" and x["domain"] == "image" for x in m)
        h = client.get(f"{BASE_URL}/v1/image/seedvr2/openapi.json")
        ok5 = (
            has_models
            and h.status_code == 200
            and h.json().get("x-kiapi-capability") == "seedvr2"
        )
        print(
            f"[5] {'✓' if ok5 else '✗'} discovery: /v1/image/seedvr2/models + /v1/image/seedvr2/openapi.json"
        )
        results.append(("5", bool(ok5)))

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
