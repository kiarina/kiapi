"""End-to-end verification for kiapi's sound-effect (se) capability.

Exercises sync + async generation, artifact download, and the error paths
(duration over the cap). Ported in spirit from mlx-audiocraft-server's tests.

Usage:
    # start the server first, e.g.:
    #   KIAPI_PORT=8000 KIAPI_MEMORY_LIMIT_GB=110 uv run kiapi
    uv run python scripts/capabilities/verify_audiogen.py

Env:
    KIAPI_BASE_URL   server base URL (default http://127.0.0.1:8000)
"""

import itertools
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import httpx

BASE_URL = os.environ.get("KIAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
SE_URL = f"{BASE_URL}/v1/audio/audiogen/generate"


def _poll(client: httpx.Client, job_id: str, timeout: float = 300.0) -> Any:
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


def test_1(
    client: httpx.Client,
    verify_dir: Path,
    saved_files: dict[str, list[Path]],
    results: list[tuple[str, bool]],
    ctx: dict[str, Any],
) -> None:
    t0 = time.time()
    r = client.post(
        SE_URL,
        json={"mode": "sync", "prompt": "dog barking", "duration": 2.0, "seed": 1},
    )
    ok = (
        r.status_code == 200
        and r.json().get("status") == "succeeded"
        and r.json().get("artifacts")
    )
    fid_sync = r.json().get("artifacts", [None])[0] if r.status_code == 200 else None
    if fid_sync:
        ctx["fid_sync"] = fid_sync
    print(
        f"[1] {'✓' if ok else '✗'} ({time.time() - t0:5.1f}s) sync generate -> succeeded + artifact"
        f"\n     {str(r.json())[:120]}"
    )
    results.append(("1", bool(ok)))
    if ok:
        if p := _save(client, verify_dir, fid_sync, f"1_sync_{fid_sync}.wav"):
            saved_files.setdefault("1", []).append(p)
    if "--fast" in sys.argv:
        print("\n[FAST MODE] Exiting early.")
        sys.exit(0 if results[-1][1] else 1)


def test_2(
    client: httpx.Client,
    verify_dir: Path,
    saved_files: dict[str, list[Path]],
    results: list[tuple[str, bool]],
    ctx: dict[str, Any],
) -> None:
    t0 = time.time()
    sub = client.post(
        SE_URL,
        json={"mode": "async", "prompt": "glass breaking", "duration": 1.5, "seed": 2},
    )
    ok2 = sub.status_code == 202 and "job_id" in sub.json()
    fid = None
    if ok2:
        job = _poll(client, sub.json()["job_id"])
        ok2 = job["status"] == "succeeded" and bool(job["artifacts"])
        fid = job["artifacts"][0] if ok2 else None
    if fid:
        ctx["fid_async"] = fid
    print(
        f"[2] {'✓' if ok2 else '✗'} ({time.time() - t0:5.1f}s)"
        " async generate -> 202 + poll to succeeded"
    )
    results.append(("2", bool(ok2)))


def test_3(
    client: httpx.Client,
    verify_dir: Path,
    saved_files: dict[str, list[Path]],
    results: list[tuple[str, bool]],
    ctx: dict[str, Any],
) -> None:
    fid = ctx.get("fid_async")
    ok3 = False
    if fid:
        d = client.get(f"{BASE_URL}/v1/files/{fid}/download")
        ok3 = (
            d.status_code == 200 and d.content[:4] == b"RIFF" and len(d.content) > 1000
        )
        if ok3:
            path = verify_dir / f"3_async_{fid}.wav"
            path.write_bytes(d.content)
            saved_files.setdefault("3", []).append(path)
    print(f"[3] {'✓' if ok3 else '✗'} download artifact -> valid WAV ({fid})")
    results.append(("3", bool(ok3)))


def test_4(
    client: httpx.Client,
    verify_dir: Path,
    saved_files: dict[str, list[Path]],
    results: list[tuple[str, bool]],
    ctx: dict[str, Any],
) -> None:
    r = client.post(SE_URL, json={"prompt": "x", "duration": 99})
    ok4 = r.status_code == 422
    print(f"[4] {'✓' if ok4 else '✗'} duration over cap -> 422 (got {r.status_code})")
    results.append(("4", ok4))


def test_5(
    client: httpx.Client,
    verify_dir: Path,
    saved_files: dict[str, list[Path]],
    results: list[tuple[str, bool]],
    ctx: dict[str, Any],
) -> None:
    fid_sync = ctx.get("fid_sync")
    ok5 = False
    if fid_sync:
        m = client.get(f"{BASE_URL}/v1/files/{fid_sync}")
        ok5 = m.status_code == 200 and m.json().get("file_id") == fid_sync
    print(f"[5] {'✓' if ok5 else '✗'} file metadata reachable")
    results.append(("5", bool(ok5)))


def test_6(
    client: httpx.Client,
    verify_dir: Path,
    saved_files: dict[str, list[Path]],
    results: list[tuple[str, bool]],
    ctx: dict[str, Any],
) -> None:
    # Submit a longer async job and sample its progress while it runs. AudioGen
    # reports real per-token progress (set_custom_progress_callback), so the job's
    # fraction must climb above 0 before the terminal 1.0 from mark_succeeded.
    t0 = time.time()
    sub = client.post(
        SE_URL,
        json={
            "mode": "async",
            "prompt": "rain on a tin roof",
            "duration": 8.0,
            "seed": 6,
        },
    )
    samples: list[float] = []
    okp = False
    if sub.status_code == 202 and "job_id" in sub.json():
        job_id = sub.json()["job_id"]
        deadline = time.time() + 300.0
        while time.time() < deadline:
            j = client.get(f"{BASE_URL}/v1/jobs/{job_id}").json()
            p = j.get("progress")
            if isinstance(p, (int, float)):
                samples.append(float(p))
            if j["status"] not in ("queued", "running"):
                break
            time.sleep(0.5)
        mid = [p for p in samples if 0.0 < p < 1.0]
        monotonic = all(b >= a for a, b in itertools.pairwise(samples))
        okp = bool(mid) and monotonic and j["status"] == "succeeded"
    print(
        f"[6] {'✓' if okp else '✗'} ({time.time() - t0:5.1f}s) async progress advances"
        f" (mid-samples={[round(p, 2) for p in samples if 0.0 < p < 1.0][:6]})"
    )
    results.append(("6", okp))


def main() -> None:
    target_id = None
    for i, arg in enumerate(sys.argv):
        if arg == "--id" and i + 1 < len(sys.argv):
            target_id = sys.argv[i + 1]
        elif arg.startswith("--id="):
            target_id = arg.split("=", 1)[1]
        elif arg in ["1", "2", "3", "4", "5", "6"] and sys.argv[i - 1] != "--id":
            target_id = arg

    verify_dir = Path(os.environ.get("KIAPI_VERIFY_DIR", ".verify")) / "audiogen"
    if verify_dir.exists() and not target_id:
        shutil.rmtree(verify_dir)
    verify_dir.mkdir(parents=True, exist_ok=True)
    saved_files: dict[str, list[Path]] = {}

    results: list[tuple[str, bool]] = []
    ctx: dict[str, Any] = {}
    print(f"{'=' * 70}\n## kiapi se verify  ({BASE_URL})\n{'=' * 70}")
    with httpx.Client(timeout=600.0, headers={"Accept": "application/json"}) as client:
        tests = [
            ("1", lambda: test_1(client, verify_dir, saved_files, results, ctx)),
            ("2", lambda: test_2(client, verify_dir, saved_files, results, ctx)),
            ("3", lambda: test_3(client, verify_dir, saved_files, results, ctx)),
            ("4", lambda: test_4(client, verify_dir, saved_files, results, ctx)),
            ("5", lambda: test_5(client, verify_dir, saved_files, results, ctx)),
            ("6", lambda: test_6(client, verify_dir, saved_files, results, ctx)),
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
