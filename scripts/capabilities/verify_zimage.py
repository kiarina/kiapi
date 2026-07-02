"""End-to-end verification for kiapi's image (zimage) capability.

Exercises txt2img (sync + async), the PNG artifact download, the error
paths (bad size / unknown model / unknown lora), and help/models discovery.
Ported in spirit from test-mflux's Z-Image checks.

Usage:
    # start the server first, e.g.:
    #   KIAPI_PORT=8000 KIAPI_MEMORY_LIMIT_GB=110 uv run kiapi
    uv run python scripts/capabilities/verify_zimage.py

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

BASE_URL = os.environ.get("KIAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
GEN_URL = f"{BASE_URL}/v1/image/zimage/generate"


def _poll(client: httpx.Client, job_id: str, timeout: float = 600.0) -> Any:
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
    if loras := kw.get("loras"):
        kw["loras"] = [
            {
                "file": {"type": "file_id", "file_id": lora["file_id"]},
                "scale": lora.get("scale", 1.0),
            }
            for lora in loras
        ]
    return kw


def _make_dataset_zip() -> bytes:
    """Build a tiny in-memory txt2img dataset zip (a couple of 256² solid images
    with same-stem captions) — enough to exercise the training path end-to-end."""
    import zipfile

    from PIL import Image

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, color in enumerate([(200, 80, 120), (90, 140, 200)]):
            img_buf = io.BytesIO()
            Image.new("RGB", (256, 256), color).save(img_buf, format="PNG")
            zf.writestr(f"sample_{i:02d}.png", img_buf.getvalue())
            zf.writestr(f"sample_{i:02d}.txt", "kiapi test swatch, flat solid color\n")
    return buf.getvalue()


def main() -> None:
    verify_dir = Path(os.environ.get("KIAPI_VERIFY_DIR", ".verify")) / "zimage"
    if verify_dir.exists():
        shutil.rmtree(verify_dir)
    verify_dir.mkdir(parents=True, exist_ok=True)
    saved_files: dict[str, list[Path]] = {}

    results: list[tuple[str, bool]] = []
    print(f"{'=' * 70}\n## kiapi zimage verify  ({BASE_URL})\n{'=' * 70}")
    # JSON-meta assertions below rely on Accept: application/json; the raw-bytes
    # path (default for direct clients) is exercised separately in case [1b].
    with httpx.Client(timeout=900.0, headers={"Accept": "application/json"}) as client:

        def _save(fid: Any, filename: str) -> Path | None:
            if not fid:
                return None
            r = client.get(f"{BASE_URL}/v1/files/{fid}/download")
            if r.status_code == 200:
                path = verify_dir / filename
                path.write_bytes(r.content)
                return path
            return None

        # 1. txt2img sync (turbo, small)
        t0 = time.time()
        r = client.post(
            GEN_URL,
            json=_params(
                mode="sync",
                model="turbo",
                prompt="a red fox in snow, photo",
                width=512,
                height=512,
                steps=9,
                seed=1,
            ),
        )
        body = r.json() if r.status_code == 200 else {}
        ok = (
            r.status_code == 200
            and body.get("status") == "succeeded"
            and body.get("artifacts")
        )
        body.get("artifacts", [None])[0] if ok else None
        print(
            f"[1] {'✓' if ok else '✗'} ({time.time() - t0:5.1f}s) txt2img sync -> succeeded + artifact\n     {str(body)[:140]}"
        )
        results.append(("1", bool(ok)))
        if ok:
            fid1 = body.get("artifacts", [None])[0]
            if p := _save(fid1, f"1_sync_{fid1}.png"):
                saved_files.setdefault("1", []).append(p)
        if "--fast" in sys.argv:
            print("\n[FAST MODE] Exiting early.")
            sys.exit(0 if results[-1][1] else 1)

        # 1b. raw-bytes content negotiation: a non-JSON Accept returns the PNG
        #     bytes directly, with the file_id in the X-Kiapi-File-Id header.
        rr = client.post(
            GEN_URL,
            headers={"Accept": "*/*"},
            json=_params(
                mode="sync",
                model="turbo",
                prompt="a teacup",
                width=256,
                height=256,
                seed=1,
            ),
        )
        raw_ok = (
            rr.status_code == 200
            and rr.headers.get("content-type") == "image/png"
            and rr.content[:8] == b"\x89PNG\r\n\x1a\n"
            and rr.headers.get("x-kiapi-file-id", "").startswith("file_")
        )
        # and the meta is still fetchable via the header's file_id
        if raw_ok:
            meta = client.get(
                f"{BASE_URL}/v1/files/{rr.headers['x-kiapi-file-id']}"
            ).json()
            raw_ok = meta.get("meta", {}).get("params", {}).get("seed") == 1
        print(
            f"[1b] {'✓' if raw_ok else '✗'} raw bytes via Accept:*/* + X-Kiapi-File-Id (meta refetchable)"
        )
        results.append(("1b", bool(raw_ok)))
        if raw_ok:
            path = verify_dir / "1b_raw.png"
            path.write_bytes(rr.content)
            saved_files.setdefault("1b", []).append(path)

        # 2. txt2img async + poll
        t0 = time.time()
        sub = client.post(
            GEN_URL,
            json=_params(
                mode="async",
                prompt="a lighthouse at dusk, painterly",
                width=512,
                height=512,
                seed=2,
            ),
        )
        ok2 = sub.status_code == 202 and "job_id" in sub.json()
        fid = None
        if ok2:
            job = _poll(client, sub.json()["job_id"])
            ok2 = job["status"] == "succeeded" and bool(job["artifacts"])
            fid = job["artifacts"][0] if ok2 else None
        print(
            f"[2] {'✓' if ok2 else '✗'} ({time.time() - t0:5.1f}s) txt2img async -> 202 + poll to succeeded"
        )
        results.append(("2", bool(ok2)))

        # 3. download the async artifact, expect a valid PNG
        ok3 = False
        if fid:
            d = client.get(f"{BASE_URL}/v1/files/{fid}/download")
            ok3 = (
                d.status_code == 200
                and d.content[:8] == b"\x89PNG\r\n\x1a\n"
                and len(d.content) > 1000
            )
            if ok3:
                path = verify_dir / f"3_async_{fid}.png"
                path.write_bytes(d.content)
                saved_files.setdefault("3", []).append(path)
        print(f"[3] {'✓' if ok3 else '✗'} download artifact -> valid PNG ({fid})")
        results.append(("3", bool(ok3)))

        # 4. bad size (not multiple of 16) -> 422
        r = client.post(GEN_URL, json=_params(prompt="x", width=513, height=512))
        ok4 = r.status_code == 422
        print(
            f"[4] {'✓' if ok4 else '✗'} non-multiple-of-16 size -> 422 (got {r.status_code})"
        )
        results.append(("4", ok4))

        # 5. unknown model -> 400
        r = client.post(GEN_URL, json=_params(model="nope", prompt="x"))
        ok5 = r.status_code == 400
        print(f"[5] {'✓' if ok5 else '✗'} unknown model -> 400 (got {r.status_code})")
        results.append(("5", ok5))

        # 6. unknown lora file_id -> 400 (resolved at run time → mapped to 400)
        r = client.post(
            GEN_URL,
            json=_params(
                mode="sync",
                prompt="x",
                width=256,
                height=256,
                loras=[{"file_id": "file_does_not_exist"}],
            ),
        )
        ok6 = r.status_code == 400
        print(
            f"[6] {'✓' if ok6 else '✗'} unknown lora file_id -> 400 (got {r.status_code})"
        )
        results.append(("6", ok6))

        # 7. discovery: models + help list zimage
        m = client.get(f"{BASE_URL}/v1/image/zimage/models").json()
        has_models = any(x["family"] == "zimage" and x["domain"] == "image" for x in m)
        h = client.get(f"{BASE_URL}/v1/image/zimage/openapi.json")
        ok7 = (
            has_models
            and h.status_code == 200
            and h.json().get("x-kiapi-capability") == "zimage"
        )
        print(
            f"[7] {'✓' if ok7 else '✗'} discovery: /v1/image/zimage/models + /v1/image/zimage/openapi.json"
        )
        results.append(("7", bool(ok7)))

        # 7b. output format selection: jpeg + webp magic bytes + content-type
        magics = {
            "jpeg": (b"\xff\xd8\xff", "image/jpeg"),
            "webp": (b"RIFF", "image/webp"),
        }
        ok7b = True
        for fmt, (magic, ctype) in magics.items():
            r = client.post(
                GEN_URL,
                json=_params(
                    mode="sync",
                    model="turbo",
                    prompt="a small ceramic cup",
                    width=256,
                    height=256,
                    seed=1,
                    format=fmt,
                    quality=80,
                ),
            )
            fid = r.json().get("artifacts", [None])[0] if r.status_code == 200 else None
            good = False
            if fid:
                d = client.get(f"{BASE_URL}/v1/files/{fid}/download")
                good = (
                    d.content[:4].startswith(magic)
                    and d.headers.get("content-type") == ctype
                )
                if good:
                    ext = "jpg" if fmt == "jpeg" else fmt
                    path = verify_dir / f"7b_format_{fmt}_{fid}.{ext}"
                    path.write_bytes(d.content)
                    saved_files.setdefault("7b", []).append(path)
            ok7b = ok7b and good
        print(
            f"[7b] {'✓' if ok7b else '✗'} output format jpeg/webp -> correct magic + content-type"
        )
        results.append(("7b", bool(ok7b)))

        # --- training (gated; set KIAPI_VERIFY_ZIMAGE_TRAIN=0 to skip the slow path) ---
        if os.environ.get("KIAPI_VERIFY_ZIMAGE_TRAIN", "1") != "0":
            zip_bytes = _make_dataset_zip()

            # 8. train missing dataset -> 400
            r = client.post(
                f"{BASE_URL}/v1/image/zimage/train",
                json={
                    "model": "turbo",
                    "dataset": {"type": "file_id", "file_id": "file_nope"},
                },
            )
            ok8 = r.status_code == 400
            print(
                f"[8] {'✓' if ok8 else '✗'} train unknown dataset_file_id -> 400 (got {r.status_code})"
            )
            results.append(("8", ok8))

            # 9. upload dataset zip -> train async -> poll -> adapter file_id
            up = client.post(
                f"{BASE_URL}/v1/files",
                files={"file": ("ds.zip", io.BytesIO(zip_bytes), "application/zip")},
            )
            ds_fid = up.json().get("file_id") if up.status_code == 200 else None
            adapter_fid = None
            t0 = time.time()
            sub = client.post(
                f"{BASE_URL}/v1/image/zimage/train",
                json={
                    "model": "turbo",
                    "dataset": {"type": "file_id", "file_id": ds_fid},
                    "num_epochs": 1,
                    "lora_rank": 8,
                    "max_resolution": 256,
                },
            )
            ok9 = sub.status_code == 202 and "job_id" in sub.json()
            if ok9:
                job = _poll(client, sub.json()["job_id"], timeout=900.0)
                ok9 = job["status"] == "succeeded" and bool(job["artifacts"])
                adapter_fid = job["result"].get("adapter_file_id") if ok9 else None
            print(
                f"[9] {'✓' if ok9 else '✗'} ({time.time() - t0:5.1f}s) train async -> 202 + adapter ({adapter_fid})"
            )
            results.append(("9", bool(ok9)))
            if adapter_fid:
                if p := _save(adapter_fid, f"9_adapter_{adapter_fid}.zip"):
                    saved_files.setdefault("9", []).append(p)

            # 10. generate using the trained adapter (transient LoRA path)
            ok10 = False
            if adapter_fid:
                r = client.post(
                    GEN_URL,
                    json=_params(
                        mode="sync",
                        model="turbo",
                        prompt="miineko spirit mascot in a garden",
                        width=256,
                        height=256,
                        seed=7,
                        loras=[{"file_id": adapter_fid, "scale": 1.0}],
                    ),
                )
                b = r.json() if r.status_code == 200 else {}
                ok10 = (
                    r.status_code == 200
                    and b.get("status") == "succeeded"
                    and b.get("artifacts")  # type: ignore
                )
                if ok10:
                    fid10 = b.get("artifacts", [None])[0]
                    if p := _save(fid10, f"10_lora_{fid10}.png"):
                        saved_files.setdefault("10", []).append(p)
            print(
                f"[10] {'✓' if ok10 else '✗'} generate with trained LoRA -> succeeded"
            )
            results.append(("10", bool(ok10)))

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
