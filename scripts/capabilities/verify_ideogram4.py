"""End-to-end verification for kiapi's image (ideogram4) capability.

The model is gated and heavy. Start the server first and make sure Hugging Face
access to ideogram-ai/ideogram-4-fp8 is approved.

Usage:
    KIAPI_BASE_URL=http://127.0.0.1:8000 uv run python scripts/capabilities/verify_ideogram4.py
"""

import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import httpx

BASE_URL = os.environ.get("KIAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
GEN_URL = f"{BASE_URL}/v1/image/ideogram4/generate"


PROMPT = {
    "high_level_description": "A clean studio photo of a white notebook with the word MFLUX on the cover.",
    "compositional_deconstruction": {
        "background": "Warm wooden desk with soft window light.",
        "elements": [
            {
                "type": "text",
                "bbox": [420, 420, 620, 560],
                "text": "MFLUX",
                "desc": "Crisp black uppercase letters centered on the notebook.",
            }
        ],
    },
}


def _params(**kw: Any) -> Any:
    return kw


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


def main() -> None:
    verify_dir = Path(".verify/ideogram4")
    if verify_dir.exists():
        shutil.rmtree(verify_dir)
    verify_dir.mkdir(parents=True, exist_ok=True)
    saved_files: dict[str, list[Path]] = {}

    results: list[tuple[str, bool]] = []
    print(f"{'=' * 70}\n## kiapi ideogram4 verify  ({BASE_URL})\n{'=' * 70}")
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

        # 1. help/models discovery is cheap and should work before weights load.
        m = client.get(f"{BASE_URL}/v1/image/ideogram4/models").json()
        has_models = any(
            x["family"] == "ideogram4" and x["domain"] == "image" for x in m
        )
        h = client.get(f"{BASE_URL}/v1/image/ideogram4/openapi.json")
        ok1 = (
            has_models
            and h.status_code == 200
            and h.json().get("x-kiapi-capability") == "ideogram4"
        )
        print(
            f"[1] {'✓' if ok1 else '✗'} discovery: /v1/image/ideogram4/models + /v1/image/ideogram4/openapi.json"
        )
        results.append(("1", bool(ok1)))
        if "--fast" in sys.argv:
            print("\n[FAST MODE] Exiting early.")
            sys.exit(0 if results[-1][1] else 1)

        # 2. validation errors should fail before any job is enqueued.
        r = client.post(GEN_URL, json=_params(prompt=PROMPT, width=255, height=512))
        ok2 = r.status_code == 422
        print(f"[2] {'✓' if ok2 else '✗'} too-small width -> 422 (got {r.status_code})")
        results.append(("2", ok2))

        r = client.post(GEN_URL, json=_params(model="nope", prompt=PROMPT))
        ok3 = r.status_code == 400
        print(f"[3] {'✓' if ok3 else '✗'} unknown model -> 400 (got {r.status_code})")
        results.append(("3", ok3))

        if os.environ.get("KIAPI_VERIFY_IDEOGRAM4_GENERATE", "1") != "0":
            t0 = time.time()
            r = client.post(
                GEN_URL,
                json=_params(
                    mode="sync",
                    model="fp8",
                    prompt=PROMPT,
                    width=1024,
                    height=1024,
                    seed=42,
                    preset="V4_DEFAULT_20",
                ),
            )
            body = r.json() if r.status_code == 200 else {}
            ok4 = (
                r.status_code == 200
                and body.get("status") == "succeeded"
                and body.get("artifacts")
            )
            print(
                f"[4] {'✓' if ok4 else '✗'} ({time.time() - t0:5.1f}s) sync JSON-caption generation"
            )
            results.append(("4", bool(ok4)))
            if ok4:
                fid4 = body.get("artifacts", [None])[0]
                if p := _save(fid4, f"4_sync_{fid4}.png"):
                    saved_files.setdefault("4", []).append(p)

            sub = client.post(
                GEN_URL,
                json=_params(
                    mode="async",
                    prompt="A white ceramic teapot on a simple studio table.",
                    width=512,
                    height=512,
                    seed=43,
                    preset="V4_TURBO_12",
                ),
            )
            ok5 = sub.status_code == 202 and "job_id" in sub.json()
            if ok5:
                job = _poll(client, sub.json()["job_id"])
                ok5 = job["status"] == "succeeded" and bool(job["artifacts"])
            print(
                f"[5] {'✓' if ok5 else '✗'} async plain-text generation -> poll to succeeded"
            )
            results.append(("5", bool(ok5)))
            if ok5:
                fid5 = job.get("artifacts", [None])[0]
                if p := _save(fid5, f"5_async_{fid5}.png"):
                    saved_files.setdefault("5", []).append(p)

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
