"""End-to-end verification for kiapi's video capability (LTX-2 distilled).

Exercises T2V (sync), I2V (sync, with an image input), async + poll, artifact
download, and the validation error paths. Video generation is slow; this uses
small sizes to keep it quick.

Usage:
    # start the server first, e.g.:
    #   KIAPI_PORT=8000 KIAPI_MEMORY_LIMIT_GB=110 uv run kiapi
    uv run python scripts/capabilities/verify_ltx2.py

Env:
    KIAPI_BASE_URL   server base URL (default http://127.0.0.1:8000)
    KIAPI_IMAGE      image for the I2V case (default: kiapi/tests/assets/miineko.png)
"""

import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import httpx

BASE_URL = os.environ.get("KIAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
VIDEO_URL = f"{BASE_URL}/v1/video/ltx2/generate"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE = os.environ.get(
    "KIAPI_IMAGE", os.path.join(HERE, "tests", "assets", "miineko.png")
)


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
        time.sleep(2.0)
    raise TimeoutError(f"job {job_id} did not finish in {timeout}s")


def _save(
    client: httpx.Client, verify_dir: Path, fid: Any, filename: str
) -> Path | None:
    if not fid:
        return None
    r = client.get(f"{BASE_URL}/v1/files/{fid}/download")
    if r.status_code == 200:
        path = verify_dir / filename
        path.write_bytes(r.content)
        return path
    return None


def _upload_file(client: httpx.Client, path: str, content_type: str) -> str:
    with open(path, "rb") as f:
        r = client.post(
            f"{BASE_URL}/v1/files",
            files={"file": (Path(path).name, f, content_type)},
        )
    if r.status_code != 200:
        raise RuntimeError(f"upload failed: {r.status_code} {r.text[:200]}")
    return r.json()["file_id"]  # type: ignore


def test_1(
    client: httpx.Client,
    verify_dir: Path,
    saved_files: dict[str, list[Path]],
    results: list[tuple[str, bool]],
) -> None:
    t0 = time.time()
    p = {
        "mode": "sync",
        "prompt": "a calm ocean wave at sunset",
        "width": 256,
        "height": 256,
        "num_frames": 25,
        "fps": 24,
        "seed": 1,
    }
    r = client.post(VIDEO_URL, json=p)
    ok = (
        r.status_code == 200
        and r.json().get("status") == "succeeded"
        and (r.json().get("result") or {}).get("mode") == "T2V"
        and r.json().get("artifacts")
    )
    print(
        f"[1] {'✓' if ok else '✗'} ({time.time() - t0:5.1f}s) sync T2V -> succeeded + artifact"
    )
    results.append(("1", bool(ok)))
    if ok:
        fid1 = r.json().get("artifacts", [None])[0]
        if saved_p := _save(client, verify_dir, fid1, f"1_sync_t2v_{fid1}.mp4"):
            saved_files.setdefault("1", []).append(saved_p)
    if "--fast" in sys.argv:
        print("\n[FAST MODE] Exiting early.")
        sys.exit(0 if results[-1][1] else 1)


def test_2(
    client: httpx.Client,
    verify_dir: Path,
    saved_files: dict[str, list[Path]],
    results: list[tuple[str, bool]],
) -> None:
    t0 = time.time()
    p = {
        "mode": "sync",
        "prompt": "gentle zoom",
        "width": 256,
        "height": 256,
        "num_frames": 17,
        "fps": 24,
        "seed": 2,
    }
    image_id = _upload_file(client, IMAGE, "image/png")
    p["image"] = {"type": "file_id", "file_id": image_id}
    r = client.post(VIDEO_URL, json=p)
    ok2 = r.status_code == 200 and (r.json().get("result") or {}).get("mode") == "I2V"
    print(f"[2] {'✓' if ok2 else '✗'} ({time.time() - t0:5.1f}s) sync I2V -> mode I2V")
    results.append(("2", bool(ok2)))
    if ok2:
        fid2 = r.json().get("artifacts", [None])[0]
        if saved_p := _save(client, verify_dir, fid2, f"2_sync_i2v_{fid2}.mp4"):
            saved_files.setdefault("2", []).append(saved_p)


def test_3(
    client: httpx.Client,
    verify_dir: Path,
    saved_files: dict[str, list[Path]],
    results: list[tuple[str, bool]],
) -> None:
    t0 = time.time()
    p = {
        "mode": "async",
        "prompt": "clouds drifting",
        "width": 256,
        "height": 256,
        "num_frames": 17,
        "seed": 3,
    }
    sub = client.post(VIDEO_URL, json=p)
    ok3 = sub.status_code == 202 and "job_id" in sub.json()
    fid = None
    if ok3:
        job = _poll(client, sub.json()["job_id"])
        ok3 = job["status"] == "succeeded" and bool(job["artifacts"])
        fid = job["artifacts"][0] if ok3 else None
    if fid:
        d = client.get(f"{BASE_URL}/v1/files/{fid}/download")
        ok3 = ok3 and d.status_code == 200 and len(d.content) > 1000
        if ok3:
            path = verify_dir / f"3_async_t2v_{fid}.mp4"
            path.write_bytes(d.content)
            saved_files.setdefault("3", []).append(path)
    print(
        f"[3] {'✓' if ok3 else '✗'} ({time.time() - t0:5.1f}s) async T2V -> poll + download mp4"
    )
    results.append(("3", bool(ok3)))


def test_validation(
    client: httpx.Client,
    cid: str,
    desc: str,
    p: dict,
    audio: str | None,
    results: list[tuple[str, bool]],
) -> None:
    if audio:
        audio_id = _upload_file(client, audio, "audio/wav")
        p["audio"] = {"type": "file_id", "file_id": audio_id}
    r = client.post(VIDEO_URL, json=p)
    ok = r.status_code == 422
    print(f"[{cid}] {'✓' if ok else '✗'} {desc} -> 422 (got {r.status_code})")
    results.append((cid, ok))


def main() -> None:
    target_id = None
    for i, arg in enumerate(sys.argv):
        if arg == "--id" and i + 1 < len(sys.argv):
            target_id = sys.argv[i + 1]
        elif arg.startswith("--id="):
            target_id = arg.split("=", 1)[1]
        elif arg in ["1", "2", "3", "4", "5", "6"] and sys.argv[i - 1] != "--id":
            target_id = arg

    verify_dir = Path(".verify/ltx2")
    if verify_dir.exists() and not target_id:
        shutil.rmtree(verify_dir)
    verify_dir.mkdir(parents=True, exist_ok=True)
    saved_files: dict[str, list[Path]] = {}

    results: list[tuple[str, bool]] = []
    print(f"{'=' * 70}\n## kiapi video verify  ({BASE_URL})\n{'=' * 70}")
    with httpx.Client(timeout=1200.0, headers={"Accept": "application/json"}) as client:
        tests = [
            ("1", lambda: test_1(client, verify_dir, saved_files, results)),
            ("2", lambda: test_2(client, verify_dir, saved_files, results)),
            ("3", lambda: test_3(client, verify_dir, saved_files, results)),
            (
                "4",
                lambda: test_validation(
                    client,
                    "4",
                    "num_frames not 1+8k",
                    {"prompt": "x", "num_frames": 50},
                    None,
                    results,
                ),
            ),
            (
                "5",
                lambda: test_validation(
                    client,
                    "5",
                    "width not multiple of 64",
                    {"prompt": "x", "width": 300},
                    None,
                    results,
                ),
            ),
            (
                "6",
                lambda: test_validation(
                    client,
                    "6",
                    "audio file + generate_audio",
                    {"prompt": "x", "generate_audio": True},
                    IMAGE,
                    results,
                ),
            ),
        ]

        for cid, test_fn in tests:
            if target_id and target_id != cid:
                continue
            test_fn()

    print(f"\n{'=' * 70}\n## SUMMARY\n{'=' * 70}")
    if not results:
        print(f"\n0/0 passed (Test ID '{target_id}' not found or executed)")
        sys.exit(1)

    passed = sum(1 for _, ok in results if ok)
    for cid, ok in results:
        if not ok:
            print(f"  FAIL: {cid}")
        else:
            s_files = saved_files.get(cid)
            if s_files:
                file_list = ", ".join(str(f) for f in s_files)
                print(f"  PASS: {cid} (Saved: {file_list})")
            else:
                print(f"  PASS: {cid}")
    print(f"\n{passed}/{len(results)} passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
