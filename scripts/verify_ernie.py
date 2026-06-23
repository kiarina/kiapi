"""End-to-end verification for kiapi's image (ernie) capability.

Exercises text-to-image generation, single-image edit, raw image responses,
async polling, artifact download, validation errors, and help/models discovery.
LoRA training is available but skipped by default because training is heavy; set
KIAPI_VERIFY_ERNIE_TRAIN=1 to run it.

Usage:
    # start the server first, e.g.:
    #   KIAPI_PORT=8000 KIAPI_MEMORY_LIMIT_GB=110 uv run kiapi
    uv run python scripts/verify_ernie.py

Env:
    KIAPI_BASE_URL             server base URL (default http://127.0.0.1:8000)
    KIAPI_ERNIE_MODEL          model for generate/edit (default turbo)
    KIAPI_ERNIE_WIDTH          verification image width (default 512)
    KIAPI_ERNIE_HEIGHT         verification image height (default 512)
    KIAPI_VERIFY_ERNIE_TRAIN   set 1 to run LoRA training (default 0)
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
MODEL = os.environ.get("KIAPI_ERNIE_MODEL", "turbo")
WIDTH = int(os.environ.get("KIAPI_ERNIE_WIDTH", "512"))
HEIGHT = int(os.environ.get("KIAPI_ERNIE_HEIGHT", "512"))
GEN_URL = f"{BASE_URL}/v1/image/ernie/generate"
EDIT_URL = f"{BASE_URL}/v1/image/ernie/edit"
TRAIN_URL = f"{BASE_URL}/v1/image/ernie/train"


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
    if image_file_id := kw.pop("image_file_id", None):
        kw["image"] = {"type": "file_id", "file_id": image_file_id}
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


def _make_dataset_zip() -> bytes:
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, color in enumerate([(210, 70, 90), (80, 150, 210)]):
            zf.writestr(f"sample_{i:02d}.png", _png_bytes(color))
            zf.writestr(
                f"sample_{i:02d}.txt", "kiapi ernie test swatch, flat solid color\n"
            )
    return buf.getvalue()


def main() -> None:
    verify_dir = Path(".verify/ernie")
    if verify_dir.exists():
        shutil.rmtree(verify_dir)
    verify_dir.mkdir(parents=True, exist_ok=True)
    saved_files: dict[str, list[Path]] = {}

    results: list[tuple[str, bool]] = []
    print(f"{'=' * 70}\n## kiapi ernie verify  ({BASE_URL})\n{'=' * 70}")
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

        # 1. discovery is cheap and should work before weights load.
        m = client.get(f"{BASE_URL}/v1/image/ernie/models").json()
        has_models = any(x["family"] == "ernie" and x["domain"] == "image" for x in m)
        h = client.get(f"{BASE_URL}/v1/image/ernie/openapi.json")
        ok1 = (
            has_models
            and h.status_code == 200
            and h.json().get("x-kiapi-capability") == "ernie"
        )
        print(
            f"[1] {'✓' if ok1 else '✗'} discovery: /v1/image/ernie/models + /v1/image/ernie/openapi.json"
        )
        results.append(("1", bool(ok1)))
        if "--fast" in sys.argv:
            print("\n[FAST MODE] Exiting early.")
            sys.exit(0 if results[-1][1] else 1)

        # 2. text-to-image sync.
        t0 = time.time()
        r = client.post(
            GEN_URL,
            json=_params(
                mode="sync",
                model=MODEL,
                prompt="a small ceramic coffee cup on a wooden desk, soft morning light",
                width=WIDTH,
                height=HEIGHT,
                steps=8,
                seed=1,
            ),
        )
        body = r.json() if r.status_code == 200 else {}
        ok2 = (
            r.status_code == 200
            and body.get("status") == "succeeded"
            and body.get("artifacts")
            and (body.get("result") or {}).get("params", {}).get("kind") == "txt2img"
        )
        print(
            f"[2] {'✓' if ok2 else '✗'} ({time.time() - t0:5.1f}s) generate sync -> kind txt2img"
        )
        results.append(("2", bool(ok2)))
        if ok2:
            fid2 = body.get("artifacts", [None])[0]
            if p := _save(fid2, f"2_sync_{fid2}.png"):
                saved_files.setdefault("2", []).append(p)

        # 2b. raw-bytes content negotiation.
        rr = client.post(
            GEN_URL,
            headers={"Accept": "*/*"},
            json=_params(
                mode="sync",
                model=MODEL,
                prompt="a tiny watercolor robot",
                width=256,
                height=256,
                steps=8,
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
            f"[2b] {'✓' if raw_ok else '✗'} raw bytes via Accept:*/* + X-Kiapi-File-Id"
        )
        results.append(("2b", bool(raw_ok)))
        if raw_ok:
            path = verify_dir / "2b_raw.png"
            path.write_bytes(rr.content)
            saved_files.setdefault("2b", []).append(path)

        # 3. edit sync via a Files API reference. ERNIE edit is single-image.
        image_id = _upload_png(client, "ernie-edit-input.png", (180, 120, 210))
        t0 = time.time()
        r = client.post(
            EDIT_URL,
            json=_params(
                mode="sync",
                model=MODEL,
                prompt="turn this color swatch into a soft watercolor poster",
                image_file_id=image_id,
                image_strength=0.55,
                width=WIDTH,
                height=HEIGHT,
                steps=8,
                seed=3,
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

        # 4. async text-to-image + poll + download.
        t0 = time.time()
        sub = client.post(
            GEN_URL,
            json=_params(
                mode="async",
                model=MODEL,
                prompt="clouds over a quiet lake, painterly",
                width=256,
                height=256,
                steps=8,
                seed=4,
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
            f"[4] {'✓' if ok4 else '✗'} ({time.time() - t0:5.1f}s) async generate -> poll + download PNG"
        )
        results.append(("4", bool(ok4)))

        # 5. bad size -> 422.
        r = client.post(
            GEN_URL, json=_params(model=MODEL, prompt="x", width=513, height=512)
        )
        ok5 = r.status_code == 422
        print(
            f"[5] {'✓' if ok5 else '✗'} non-multiple-of-16 size -> 422 (got {r.status_code})"
        )
        results.append(("5", ok5))

        # 6. edit non-square guard -> 422 by default.
        r = client.post(
            EDIT_URL,
            json=_params(
                model=MODEL,
                prompt="x",
                image_file_id=image_id,
                width=512,
                height=768,
            ),
        )
        ok6 = r.status_code == 422
        print(
            f"[6] {'✓' if ok6 else '✗'} non-square edit size guard -> 422 (got {r.status_code})"
        )
        results.append(("6", ok6))

        # 7. unknown model / file IDs.
        bad_model = client.post(GEN_URL, json=_params(model="nope", prompt="x"))
        bad_edit = client.post(
            EDIT_URL,
            json=_params(
                mode="sync",
                model=MODEL,
                prompt="x",
                image_file_id="file_does_not_exist",
                width=256,
                height=256,
            ),
        )
        bad_lora = client.post(
            GEN_URL,
            json=_params(
                mode="sync",
                model=MODEL,
                prompt="x",
                width=256,
                height=256,
                loras=[{"file_id": "file_does_not_exist"}],
            ),
        )
        ok7 = (
            bad_model.status_code == 400
            and bad_edit.status_code == 400
            and bad_lora.status_code == 400
        )
        print(f"[7] {'✓' if ok7 else '✗'} unknown model/image/lora -> 400")
        results.append(("7", ok7))

        # 8. output format selection.
        magics = {
            "jpeg": (b"\xff\xd8\xff", "image/jpeg"),
            "webp": (b"RIFF", "image/webp"),
        }
        ok8 = True
        for fmt, (magic, ctype) in magics.items():
            r = client.post(
                GEN_URL,
                json=_params(
                    mode="sync",
                    model=MODEL,
                    prompt="a tiny cup",
                    width=256,
                    height=256,
                    steps=8,
                    seed=5,
                    format=fmt,
                    quality=80,
                ),
            )
            out_fid = (
                r.json().get("artifacts", [None])[0] if r.status_code == 200 else None
            )
            good = False
            if out_fid:
                d = client.get(f"{BASE_URL}/v1/files/{out_fid}/download")
                good = (
                    d.content[:4].startswith(magic)
                    and d.headers.get("content-type") == ctype
                )
                if good:
                    ext = "jpg" if fmt == "jpeg" else fmt
                    path = verify_dir / f"8_format_{fmt}_{out_fid}.{ext}"
                    path.write_bytes(d.content)
                    saved_files.setdefault("8", []).append(path)
            ok8 = ok8 and good
        print(
            f"[8] {'✓' if ok8 else '✗'} output format jpeg/webp -> correct magic + content-type"
        )
        results.append(("8", bool(ok8)))

        # 9. train validation + optional slow training path.
        r = client.post(
            TRAIN_URL,
            json={
                "model": MODEL,
                "dataset": {"type": "file_id", "file_id": "file_nope"},
            },
        )
        ok9 = r.status_code == 400
        print(
            f"[9] {'✓' if ok9 else '✗'} train unknown dataset_file_id -> 400 (got {r.status_code})"
        )
        results.append(("9", ok9))

        if os.environ.get("KIAPI_VERIFY_ERNIE_TRAIN", "0") == "1":
            up = client.post(
                f"{BASE_URL}/v1/files",
                files={
                    "file": (
                        "ernie_ds.zip",
                        io.BytesIO(_make_dataset_zip()),
                        "application/zip",
                    )
                },
            )
            ds_fid = up.json().get("file_id") if up.status_code == 200 else None
            t0 = time.time()
            sub = client.post(
                TRAIN_URL,
                json={
                    "model": MODEL,
                    "dataset": {"type": "file_id", "file_id": ds_fid},
                    "num_epochs": 1,
                    "lora_rank": 8,
                    "max_resolution": 256,
                },
            )
            ok10 = sub.status_code == 202 and "job_id" in sub.json()
            adapter_fid = None
            if ok10:
                job = _poll(client, sub.json()["job_id"], timeout=1800.0)
                ok10 = job["status"] == "succeeded" and bool(job["artifacts"])
                adapter_fid = job["result"].get("adapter_file_id") if ok10 else None
            print(
                f"[10] {'✓' if ok10 else '✗'} ({time.time() - t0:5.1f}s) train async -> adapter ({adapter_fid})"
            )
            results.append(("10", bool(ok10)))
            if adapter_fid:
                if p := _save(adapter_fid, f"10_adapter_{adapter_fid}.zip"):
                    saved_files.setdefault("10", []).append(p)
        else:
            print(
                "[10] - skipped ERNIE LoRA training (set KIAPI_VERIFY_ERNIE_TRAIN=1 to run)"
            )

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
