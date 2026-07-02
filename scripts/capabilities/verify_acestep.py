"""End-to-end verification for kiapi's acestep family (ACE-Step 1.5).

Exercises all four endpoints (generate / cover / repaint / extract) plus sync &
async modes and the error paths, against a running kiapi server. Uses the
``turbo`` preset throughout for speed.

Usage:
    # start the server first, e.g.:
    #   KIAPI_PORT=8000 KIAPI_MEMORY_LIMIT_GB=110 uv run kiapi
    uv run python scripts/capabilities/verify_acestep.py

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

BASE = os.environ.get("KIAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
M = "turbo"


def _file_ref(file_id: str) -> dict[str, str]:
    return {"type": "file_id", "file_id": file_id}


def _poll(
    client: httpx.Client,
    job_id: str,
    timeout: float = 600.0,
    progress_seen: list | None = None,
) -> Any:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        j = client.get(f"{BASE}/v1/jobs/{job_id}").json()
        if progress_seen is not None:
            p = j.get("progress")
            if isinstance(p, (int, float)) and 0.0 < p < 1.0:
                progress_seen.append(p)

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
    return {"status": "timeout"}


def _save(
    client: httpx.Client, verify_dir: Path, fid: Any, filename: str
) -> Path | None:
    if not fid:
        return None
    r = client.get(f"{BASE}/v1/files/{fid}/download", timeout=60)
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
        f"{BASE}/v1/audio/acestep/generate",
        json={
            "model": M,
            "mode": "sync",
            "prompt": "upbeat synthwave, bright arps",
            "lyrics": "[Instrumental]",
            "duration": 10,
            "seed": 7,
        },
    )
    ok = r.status_code == 200 and r.json().get("status") == "succeeded"
    src = r.json().get("result", {}).get("file_id") if ok else None
    if src:
        ctx["src"] = src

    print(
        f"[1] {'ok' if ok and bool(src) else 'ng'} generate sync "
        f"({time.time() - t0:.1f}s) -> file_id={src}"
    )
    results.append(("1", bool(ok and bool(src))))
    if ok and src:
        if p := _save(client, verify_dir, src, f"1_sync_{src}.wav"):
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
    src = ctx.get("src")
    if not src:
        print("[2] ng cover sync -> skipped (missing src)")
        results.append(("2", False))
        return

    t0 = time.time()
    r = client.post(
        f"{BASE}/v1/audio/acestep/cover",
        json={
            "model": M,
            "mode": "sync",
            "source": _file_ref(src),
            "prompt": "lo-fi chillhop, warm tape",
            "strength": 0.7,
        },
    )
    ok = r.status_code == 200 and r.json().get("status") == "succeeded"
    msg2 = r.json().get("artifacts") if ok else r.text[:120]
    print(f"[2] {'ok' if ok else 'ng'} cover sync ({time.time() - t0:.1f}s) -> {msg2}")
    results.append(("2", bool(ok)))
    if ok:
        fid2 = r.json().get("artifacts", [None])[0]
        if p := _save(client, verify_dir, fid2, f"2_cover_{fid2}.wav"):
            saved_files.setdefault("2", []).append(p)


def test_3(
    client: httpx.Client,
    verify_dir: Path,
    saved_files: dict[str, list[Path]],
    results: list[tuple[str, bool]],
    ctx: dict[str, Any],
) -> None:
    src = ctx.get("src")
    if not src:
        print("[3] ng repaint sync -> skipped (missing src)")
        results.append(("3", False))
        return

    t0 = time.time()
    r = client.post(
        f"{BASE}/v1/audio/acestep/repaint",
        json={
            "model": M,
            "mode": "sync",
            "source": _file_ref(src),
            "prompt": "add a soaring lead",
            "start": 2.0,
            "end": 6.0,
            "strength": 0.5,
        },
    )
    ok = r.status_code == 200 and r.json().get("status") == "succeeded"
    msg3 = r.json().get("artifacts") if ok else r.text[:120]
    print(
        f"[3] {'ok' if ok else 'ng'} repaint sync ({time.time() - t0:.1f}s) -> {msg3}"
    )
    results.append(("3", bool(ok)))
    if ok:
        fid3 = r.json().get("artifacts", [None])[0]
        if p := _save(client, verify_dir, fid3, f"3_repaint_{fid3}.wav"):
            saved_files.setdefault("3", []).append(p)


def test_4(
    client: httpx.Client,
    verify_dir: Path,
    saved_files: dict[str, list[Path]],
    results: list[tuple[str, bool]],
    ctx: dict[str, Any],
) -> None:
    src = ctx.get("src")
    if not src:
        print("[4] ng extract sync -> skipped (missing src)")
        results.append(("4", False))
        return

    t0 = time.time()
    r = client.post(
        f"{BASE}/v1/audio/acestep/extract",
        json={
            "model": M,
            "mode": "sync",
            "source": _file_ref(src),
            "targets": ["vocals", "drums"],
        },
    )
    j = r.json()
    ok = (
        r.status_code == 200
        and j.get("status") == "succeeded"
        and len(j.get("artifacts") or []) == 2
    )
    arts = len(j.get("artifacts") or [])
    print(
        f"[4] {'ok' if ok else 'ng'} extract sync ({time.time() - t0:.1f}s) -> {arts} artifacts"
    )
    results.append(("4", bool(ok)))
    if ok:
        for i, fid4 in enumerate(j.get("artifacts") or []):
            if p := _save(client, verify_dir, fid4, f"4_extract_{i}_{fid4}.wav"):
                saved_files.setdefault("4", []).append(p)


def test_5(
    client: httpx.Client,
    verify_dir: Path,
    saved_files: dict[str, list[Path]],
    results: list[tuple[str, bool]],
    ctx: dict[str, Any],
) -> None:
    r = client.post(
        f"{BASE}/v1/audio/acestep/generate",
        json={
            "model": M,
            "mode": "async",
            "prompt": "calm ambient pad",
            "lyrics": "[Instrumental]",
            "duration": 8,
            "seed": 1,
        },
    )
    jid = r.json().get("job_id")
    ok = r.status_code == 202 and bool(jid)
    progress_seen: list[float] = []
    final = {}
    if ok:
        final = _poll(client, jid, progress_seen=progress_seen)
        ok = final.get("status") == "succeeded" and bool(final.get("artifacts"))
        ctx["progress_seen"] = progress_seen

    print(
        f"[5] {'ok' if ok else 'ng'} generate async -> job {jid} {('done' if ok else 'FAILED')}"
    )
    results.append(("5", bool(ok)))
    if ok:
        fid5 = final.get("artifacts", [None])[0]
        if p := _save(client, verify_dir, fid5, f"5_async_{fid5}.wav"):
            saved_files.setdefault("5", []).append(p)


def test_5b(
    client: httpx.Client,
    verify_dir: Path,
    saved_files: dict[str, list[Path]],
    results: list[tuple[str, bool]],
    ctx: dict[str, Any],
) -> None:
    # 5b depends on 5 running.
    progress_seen = ctx.get("progress_seen", [])
    ok = bool(progress_seen)
    mx = max(progress_seen) if progress_seen else 0
    print(
        f"[5b] {'ok' if ok else 'ng'} progress reported mid-flight -> "
        f"{len(progress_seen)} samples, max={mx:.2f}"
    )
    results.append(("5b", ok))


def test_6(
    client: httpx.Client,
    verify_dir: Path,
    saved_files: dict[str, list[Path]],
    results: list[tuple[str, bool]],
    ctx: dict[str, Any],
) -> None:
    r = client.post(
        f"{BASE}/v1/audio/acestep/generate",
        json={"model": "gpt-9", "prompt": "x", "duration": 5},
    )
    ok = r.status_code == 422
    print(f"[6] {'ok' if ok else 'ng'} unknown preset -> {r.status_code} (want 422)")
    results.append(("6", ok))


def test_7(
    client: httpx.Client,
    verify_dir: Path,
    saved_files: dict[str, list[Path]],
    results: list[tuple[str, bool]],
    ctx: dict[str, Any],
) -> None:
    r = client.post(
        f"{BASE}/v1/audio/acestep/cover",
        json={"model": M, "source": _file_ref("file_does_not_exist"), "prompt": "x"},
    )
    ok = r.status_code == 400
    print(f"[7] {'ok' if ok else 'ng'} missing src -> {r.status_code} (want 400)")
    results.append(("7", ok))


def main() -> None:
    target_id = None
    for i, arg in enumerate(sys.argv):
        if arg == "--id" and i + 1 < len(sys.argv):
            target_id = sys.argv[i + 1]
        elif arg.startswith("--id="):
            target_id = arg.split("=", 1)[1]
        elif (
            arg in ["1", "2", "3", "4", "5", "5b", "6", "7"]
            and sys.argv[i - 1] != "--id"
        ):
            target_id = arg

    verify_dir = Path(os.environ.get("KIAPI_VERIFY_DIR", ".verify")) / "acestep"
    if verify_dir.exists() and not target_id:
        shutil.rmtree(verify_dir)
    verify_dir.mkdir(parents=True, exist_ok=True)

    saved_files: dict[str, list[Path]] = {}
    results: list[tuple[str, bool]] = []
    ctx: dict[str, Any] = {}

    print(f"{'=' * 70}\n## kiapi acestep verify  ({BASE})\n{'=' * 70}")
    with httpx.Client(timeout=1200.0, headers={"Accept": "application/json"}) as client:
        tests = [
            ("1", lambda: test_1(client, verify_dir, saved_files, results, ctx)),
            ("2", lambda: test_2(client, verify_dir, saved_files, results, ctx)),
            ("3", lambda: test_3(client, verify_dir, saved_files, results, ctx)),
            ("4", lambda: test_4(client, verify_dir, saved_files, results, ctx)),
            ("5", lambda: test_5(client, verify_dir, saved_files, results, ctx)),
            ("5b", lambda: test_5b(client, verify_dir, saved_files, results, ctx)),
            ("6", lambda: test_6(client, verify_dir, saved_files, results, ctx)),
            ("7", lambda: test_7(client, verify_dir, saved_files, results, ctx)),
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
