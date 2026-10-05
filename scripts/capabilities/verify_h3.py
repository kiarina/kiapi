"""End-to-end verification for kiapi's MiniMax H3 capability.

Exercises text-only generation, image + audio references, a video reference with
its soundtrack, and the validation error paths. Every run starts and stops
mlx-serve; small sizes keep each case at a few minutes.

Usage:
    # start the server first, e.g.:
    #   KIAPI_PORT=8000 KIAPI_MEMORY_LIMIT_GB=110 uv run kiapi
    uv run python scripts/capabilities/verify_h3.py [--fast]

Env:
    KIAPI_BASE_URL   server base URL (default http://127.0.0.1:8000)
"""

import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import httpx

BASE_URL = os.environ.get("KIAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
VIDEO_URL = f"{BASE_URL}/v1/video/h3/generate"
ASSETS = Path(__file__).resolve().parents[2] / "tests" / "assets"
SMALL = {"width": 256, "height": 256, "num_frames": 22, "seed": 1}


def _upload(client: httpx.Client, path: Path, content_type: str) -> dict[str, str]:
    with path.open("rb") as f:
        r = client.post(
            f"{BASE_URL}/v1/files", files={"file": (path.name, f, content_type)}
        )
    r.raise_for_status()
    return {"type": "file_id", "file_id": r.json()["file_id"]}


def _poll(client: httpx.Client, job_id: str, timeout: float = 3600.0) -> Any:
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"{BASE_URL}/v1/jobs/{job_id}").json()
        if job["status"] not in ("queued", "running"):
            print()
            return job
        label = job.get("progress_label") or ""
        print(f"\r  {(job.get('progress') or 0) * 100:5.1f}% {label:<30}", end="")
        time.sleep(5.0)
    raise TimeoutError(f"job {job_id} did not finish in {timeout}s")


def _generate(
    client: httpx.Client, verify_dir: Path, cid: str, desc: str, body: dict, check: Any
) -> bool:
    t0 = time.time()
    sub = client.post(VIDEO_URL, json={"mode": "async", **body})
    ok = sub.status_code == 202
    job: dict[str, Any] = {}
    if ok:
        job = _poll(client, sub.json()["job_id"])
        ok = job["status"] == "succeeded" and bool(check(job.get("result") or {}))
    if ok:
        fid = job["artifacts"][0]
        data = client.get(f"{BASE_URL}/v1/files/{fid}/download").content
        ok = len(data) > 1000
        (verify_dir / f"{cid}_{fid}.mp4").write_bytes(data)
    print(f"[{cid}] {'✓' if ok else '✗'} ({time.time() - t0:6.1f}s) {desc}")
    if not ok:
        print(f"      status={sub.status_code} job={str(job or sub.text)[:400]}")
    return ok


def _rejected(client: httpx.Client, cid: str, desc: str, body: dict) -> bool:
    r = client.post(VIDEO_URL, json=body)
    ok = r.status_code == 422
    print(f"[{cid}] {'✓' if ok else '✗'} {desc} -> 422 (got {r.status_code})")
    return ok


def main() -> None:
    verify_dir = Path(os.environ.get("KIAPI_VERIFY_DIR", ".verify")) / "h3"
    shutil.rmtree(verify_dir, ignore_errors=True)
    verify_dir.mkdir(parents=True)
    results: list[bool] = []
    print(f"{'=' * 70}\n## kiapi h3 verify  ({BASE_URL})\n{'=' * 70}")

    with httpx.Client(timeout=600.0, headers={"Accept": "application/json"}) as client:
        results.append(
            _generate(
                client,
                verify_dir,
                "1",
                "text only (Turbo, prompt as is) -> mp4 with audio",
                {
                    "prompt": "a red fox walks through fresh snow, soft wind",
                    "enhance_prompt": False,
                    **SMALL,
                },
                lambda res: res["has_audio"] and res["params"]["steps"] == 8,
            )
        )
        if "--fast" in sys.argv:
            sys.exit(0 if all(results) else 1)

        image = _upload(client, ASSETS / "miineko.png", "image/png")
        song = _upload(client, ASSETS / "song.wav", "audio/wav")
        results.append(
            _generate(
                client,
                verify_dir,
                "2",
                "image + audio references, rewritten prompt",
                {
                    "prompt": (
                        "The pink cat character from <Picture 1> dances to the "
                        "music of <Audio 1> on a small stage."
                    ),
                    "images": [image],
                    "audios": [song],
                    **SMALL,
                },
                lambda res: (
                    res["references"] == {"images": 1, "videos": 0, "audios": 1}
                    and "subject_definitions:"
                    in (res["params"]["enhanced_prompt"] or "")
                ),
            )
        )

        video = _upload(client, ASSETS / "pv.mp4", "video/mp4")
        results.append(
            _generate(
                client,
                verify_dir,
                "3",
                "video reference with its soundtrack",
                {
                    "prompt": (
                        "Continue <Video 1> with the same camera and style, "
                        "keeping its sound <Audio 1>."
                    ),
                    "videos": [video],
                    "use_video_audio": True,
                    **SMALL,
                },
                lambda res: res["references"]["videos"] == 1 and res["has_audio"],
            )
        )

        results.append(
            _rejected(
                client, "4", "num_frames off 5+17k", {"prompt": "x", "num_frames": 50}
            )
        )
        results.append(
            _rejected(
                client, "5", "width not multiple of 32", {"prompt": "x", "width": 300}
            )
        )
        results.append(
            _rejected(
                client,
                "6",
                "audio without image or video",
                {"prompt": "x", "audios": [song]},
            )
        )

    print(f"\n{sum(results)}/{len(results)} passed; artifacts in {verify_dir}")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
