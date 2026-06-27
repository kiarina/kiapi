"""End-to-end verification for kiapi's image (qwen) capability.

Exercises txt2img, img2img, natural-language edit, raw image responses, async
polling, artifact download, validation errors, and help/models discovery.

Usage:
    # start the server first, e.g.:
    #   KIAPI_PORT=8000 KIAPI_MEMORY_LIMIT_GB=110 uv run kiapi
    uv run python scripts/capabilities/verify_qwen.py

Env:
    KIAPI_BASE_URL      server base URL (default http://127.0.0.1:8000)
    KIAPI_QWEN_WIDTH    verification image width (default 512)
    KIAPI_QWEN_HEIGHT   verification image height (default 512)
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
WIDTH = int(os.environ.get("KIAPI_QWEN_WIDTH", "512"))
HEIGHT = int(os.environ.get("KIAPI_QWEN_HEIGHT", "512"))
GEN_URL = f"{BASE_URL}/v1/image/qwen/generate"
EDIT_URL = f"{BASE_URL}/v1/image/qwen/edit"


def _poll(client: httpx.Client, job_id: str, timeout: float = 1800.0) -> Any:
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
    if init_image_file_id := kw.pop("init_image_file_id", None):
        kw["init_image"] = {"type": "file_id", "file_id": init_image_file_id}
    if image_file_ids := kw.pop("image_file_ids", None):
        kw["images"] = [
            {"type": "file_id", "file_id": file_id} for file_id in image_file_ids
        ]
    if loras := kw.get("loras"):
        kw["loras"] = [
            {
                "file": {"type": "file_id", "file_id": lora["file_id"]},
                "scale": lora.get("scale", 1.0),
            }
            for lora in loras
        ]
    return kw


def _png_bytes(color: tuple[int, int, int], size: int = 256) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (size, size), color).save(buf, format="PNG")
    return buf.getvalue()


def _upload_png(client: httpx.Client, name: str, color: tuple[int, int, int]) -> str:
    r = client.post(
        f"{BASE_URL}/v1/files",
        files={"file": (name, io.BytesIO(_png_bytes(color)), "image/png")},
    )
    if r.status_code != 200:
        raise RuntimeError(f"upload {name} failed: {r.status_code} {r.text[:200]}")
    return r.json()["file_id"]  # type: ignore


def main() -> None:
    verify_dir = Path(".verify/qwen")
    if verify_dir.exists():
        shutil.rmtree(verify_dir)
    verify_dir.mkdir(parents=True, exist_ok=True)
    saved_files: dict[str, list[Path]] = {}

    results: list[tuple[str, bool]] = []
    print(f"{'=' * 70}\n## kiapi qwen verify  ({BASE_URL})\n{'=' * 70}")
    with httpx.Client(timeout=2400.0, headers={"Accept": "application/json"}) as client:

        def _save(fid: Any, filename: str) -> Path | None:
            if not fid:
                return None
            r = client.get(f"{BASE_URL}/v1/files/{fid}/download")
            if r.status_code == 200:
                path = verify_dir / filename
                path.write_bytes(r.content)
                return path
            return None

        # 1. txt2img sync
        t0 = time.time()
        r = client.post(
            GEN_URL,
            json=_params(
                mode="sync",
                model="image",
                prompt="a clean cafe storefront, a wooden sign clearly reads CAFE",
                negative_prompt="blurry, low quality, distorted text",
                width=WIDTH,
                height=HEIGHT,
                seed=1,
            ),
        )
        body = r.json() if r.status_code == 200 else {}
        ok = (
            r.status_code == 200
            and body.get("status") == "succeeded"
            and body.get("artifacts")
        )
        print(
            f"[1] {'✓' if ok else '✗'} ({time.time() - t0:5.1f}s) txt2img sync -> succeeded + artifact"
        )
        results.append(("1", bool(ok)))
        if ok:
            fid1 = body.get("artifacts", [None])[0]
            if p := _save(fid1, f"1_sync_{fid1}.png"):
                saved_files.setdefault("1", []).append(p)
        if "--fast" in sys.argv:
            print("\n[FAST MODE] Exiting early.")
            sys.exit(0 if results[-1][1] else 1)

        # 1b. raw-bytes content negotiation
        rr = client.post(
            GEN_URL,
            headers={"Accept": "*/*"},
            json=_params(
                mode="sync",
                model="image",
                prompt="a tiny watercolor robot",
                width=256,
                height=256,
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

        # 2. img2img sync via Files API reference
        init_id = _upload_png(client, "qwen-init.png", (180, 120, 210))
        t0 = time.time()
        r = client.post(
            GEN_URL,
            json=_params(
                mode="sync",
                model="image",
                prompt="turn this swatch into a polished abstract illustration",
                init_image_file_id=init_id,
                image_strength=0.45,
                width=WIDTH,
                height=HEIGHT,
                seed=3,
            ),
        )
        body = r.json() if r.status_code == 200 else {}
        ok2 = (
            r.status_code == 200
            and body.get("status") == "succeeded"
            and (body.get("result") or {}).get("params", {}).get("kind") == "img2img"
        )
        print(
            f"[2] {'✓' if ok2 else '✗'} ({time.time() - t0:5.1f}s) img2img sync -> kind img2img"
        )
        results.append(("2", bool(ok2)))
        if ok2:
            fid2 = body.get("artifacts", [None])[0]
            if p := _save(fid2, f"2_img2img_{fid2}.png"):
                saved_files.setdefault("2", []).append(p)

        # 3. edit sync with two reference image IDs
        ref1 = _upload_png(client, "qwen-ref1.png", (230, 80, 120))
        ref2 = _upload_png(client, "qwen-ref2.png", (80, 170, 220))
        t0 = time.time()
        r = client.post(
            EDIT_URL,
            json=_params(
                mode="sync",
                model="edit-2509",
                prompt="combine the pink and blue references into a cheerful geometric poster",
                image_file_ids=[ref1, ref2],
                width=WIDTH,
                height=HEIGHT,
                seed=4,
            ),
        )
        body = r.json() if r.status_code == 200 else {}
        ok3 = (
            r.status_code == 200
            and body.get("status") == "succeeded"
            and (body.get("result") or {}).get("params", {}).get("kind") == "edit"
        )
        print(
            f"[3] {'✓' if ok3 else '✗'} ({time.time() - t0:5.1f}s) edit sync -> kind edit"
        )
        results.append(("3", bool(ok3)))
        if ok3:
            fid3 = body.get("artifacts", [None])[0]
            if p := _save(fid3, f"3_edit_{fid3}.png"):
                saved_files.setdefault("3", []).append(p)

        # 4. async txt2img + poll + download
        t0 = time.time()
        sub = client.post(
            GEN_URL,
            json=_params(
                mode="async",
                model="image",
                prompt="clouds over a quiet lake, painterly",
                width=256,
                height=256,
                seed=5,
            ),
        )
        ok4 = sub.status_code == 202 and "job_id" in sub.json()
        fid = None
        if ok4:
            job = _poll(client, sub.json()["job_id"])
            ok4 = job["status"] == "succeeded" and bool(job["artifacts"])
            fid = job["artifacts"][0] if ok4 else None
        if fid:
            d = client.get(f"{BASE_URL}/v1/files/{fid}/download")
            ok4 = ok4 and d.status_code == 200 and d.content[:8] == b"\x89PNG\r\n\x1a\n"
            if ok4:
                path = verify_dir / f"4_async_{fid}.png"
                path.write_bytes(d.content)
                saved_files.setdefault("4", []).append(path)
        print(
            f"[4] {'✓' if ok4 else '✗'} ({time.time() - t0:5.1f}s) async txt2img -> poll + download PNG"
        )
        results.append(("4", bool(ok4)))

        # 5. bad size -> 422
        r = client.post(
            GEN_URL, json=_params(model="image", prompt="x", width=513, height=512)
        )
        ok5 = r.status_code == 422
        print(
            f"[5] {'✓' if ok5 else '✗'} non-multiple-of-16 size -> 422 (got {r.status_code})"
        )
        results.append(("5", ok5))

        # 6. wrong model for endpoint -> 400
        bad_gen = client.post(GEN_URL, json=_params(model="edit-2509", prompt="x"))
        bad_edit = client.post(
            EDIT_URL, json=_params(model="image", prompt="x", image_file_ids=[ref1])
        )
        ok6 = bad_gen.status_code == 400 and bad_edit.status_code == 400
        print(f"[6] {'✓' if ok6 else '✗'} wrong endpoint model -> 400")
        results.append(("6", ok6))

        # 7. unknown file IDs -> 400
        bad_init = client.post(
            GEN_URL,
            json=_params(
                mode="sync",
                model="image",
                prompt="x",
                init_image_file_id="file_does_not_exist",
                width=256,
                height=256,
            ),
        )
        bad_edit = client.post(
            EDIT_URL,
            json=_params(
                mode="sync",
                model="edit-2509",
                prompt="x",
                image_file_ids=["file_does_not_exist"],
                width=256,
                height=256,
            ),
        )
        ok7 = bad_init.status_code == 400 and bad_edit.status_code == 400
        print(f"[7] {'✓' if ok7 else '✗'} unknown init/edit image file_id -> 400")
        results.append(("7", ok7))

        # 8. discovery: models + help list qwen
        m = client.get(f"{BASE_URL}/v1/image/qwen/models").json()
        has_models = any(x["family"] == "qwen" and x["domain"] == "image" for x in m)
        h = client.get(f"{BASE_URL}/v1/image/qwen/openapi.json")
        ok8 = (
            has_models
            and h.status_code == 200
            and h.json().get("x-kiapi-capability") == "qwen"
        )
        print(
            f"[8] {'✓' if ok8 else '✗'} discovery: /v1/image/qwen/models + /v1/image/qwen/openapi.json"
        )
        results.append(("8", bool(ok8)))

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
