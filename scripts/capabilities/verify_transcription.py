"""End-to-end verification for kiapi's transcription capability.

Transcribes Japanese speech made with macOS `say` (the Kyoko voice) through
``POST /v1/audio/transcriptions`` in each response format, checks the error
paths, and registers a speech voice without a transcript (kiapi fills it in).

Usage:
    # start the server first, e.g.:
    #   KIAPI_PORT=8000 uv run kiapi
    uv run python scripts/capabilities/verify_transcription.py [--fast] [--id N]

Env:
    KIAPI_BASE_URL   server base URL (default http://127.0.0.1:8000)
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import time
from itertools import pairwise
from pathlib import Path
from typing import Any

import httpx

BASE_URL = os.environ.get("KIAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
URL = f"{BASE_URL}/v1/audio/transcriptions"
TEXT = "もしもし、もう駅に着いた？今日は結構寒いね。マフラーを持ってきて正解だった。"  # noqa: RUF001
# Phrases a correct transcript contains, whatever its punctuation.
PHRASES = ["もしもし", "駅", "寒い", "マフラー", "正解"]


def _speech(verify_dir: Path) -> Path:
    path = verify_dir / "speech_ja.aiff"
    if not path.exists():
        subprocess.run(["say", "-v", "Kyoko", "-o", str(path), TEXT], check=True)
    return path


def _post(client: httpx.Client, audio: Path, **data: Any) -> httpx.Response:
    with audio.open("rb") as f:
        return client.post(
            URL, files={"file": (audio.name, f, "audio/aiff")}, data=data
        )


def _contains(text: str) -> bool:
    return all(p in text for p in PHRASES)


def _report(
    cid: str, ok: bool, t0: float, label: str, detail: str, results: list
) -> None:
    print(f"[{cid}] {'✓' if ok else '✗'} ({time.time() - t0:5.1f}s) {label}")
    print(f"     {detail[:300]}")
    results.append((cid, ok))


def test_1(client: httpx.Client, verify_dir: Path, results: list) -> None:
    t0 = time.time()
    r = _post(client, _speech(verify_dir))
    body = r.json() if r.status_code == 200 else {}
    ok = r.status_code == 200 and _contains(body.get("text", ""))
    ok = ok and body.get("usage", {}).get("type") == "duration"
    (verify_dir / "1_json.json").write_text(r.text)
    _report("1", ok, t0, "json -> text with the spoken phrases", r.text, results)
    if "--fast" in sys.argv:
        print("\n[FAST MODE] Exiting early.")
        sys.exit(0 if ok else 1)


def test_2(client: httpx.Client, verify_dir: Path, results: list) -> None:
    t0 = time.time()
    r = _post(client, _speech(verify_dir), response_format="text", language="ja")
    ok = (
        r.status_code == 200
        and r.headers["content-type"].startswith("text/plain")
        and _contains(r.text)
    )
    _report("2", ok, t0, "text with language=ja -> plain text", r.text, results)


def test_3(client: httpx.Client, verify_dir: Path, results: list) -> None:
    t0 = time.time()
    r = _post(
        client,
        _speech(verify_dir),
        response_format="verbose_json",
        **{"timestamp_granularities[]": ["segment", "word"]},
    )
    body = r.json() if r.status_code == 200 else {}
    (verify_dir / "3_verbose.json").write_text(
        json.dumps(body, ensure_ascii=False, indent=2)
    )
    segments, words = body.get("segments") or [], body.get("words") or []
    duration = body.get("duration", 0)
    ok = (
        r.status_code == 200
        and body.get("language") == "japanese"
        and _contains(body.get("text", ""))
        and len(segments) >= 3  # three sentences
        and len(words) >= len(PHRASES)
        and all(0 <= w["start"] <= w["end"] <= duration + 0.1 for w in words)
        and all(a["start"] <= b["start"] for a, b in pairwise(words))
    )
    detail = " | ".join(
        f"{s['start']:.2f}-{s['end']:.2f} {s['text']}" for s in segments
    )
    _report("3", ok, t0, "verbose_json -> sentences and words timed", detail, results)


def test_4(client: httpx.Client, verify_dir: Path, results: list) -> None:
    t0 = time.time()
    audio = _speech(verify_dir)
    cases = [
        (_post(client, audio, **{"timestamp_granularities[]": "word"}), 422),
        (_post(client, audio, model="whisper-1"), 400),
        (_post(client, audio, language="xx"), 422),
        (_post(client, audio, response_format="srt"), 422),
    ]
    ok = all(r.status_code == code for r, code in cases)
    detail = ", ".join(f"{r.status_code}" for r, _ in cases)
    _report("4", ok, t0, "error paths -> 422/400/422/422", detail, results)


def test_5(client: httpx.Client, verify_dir: Path, results: list) -> None:
    t0 = time.time()
    data = base64.b64encode(_speech(verify_dir).read_bytes()).decode()
    r = client.post(
        f"{BASE_URL}/v1/audio/voices",
        json={
            "audio": {"type": "data_url", "data_url": f"data:audio/aiff;base64,{data}"},
            "name": "kiapi verify transcription",
        },
    )
    voice = r.json() if r.status_code == 200 else {}
    if voice.get("id"):
        client.delete(f"{BASE_URL}/v1/audio/voices/{voice['id']}")
    ok = r.status_code == 200 and _contains(voice.get("transcript") or "")
    _report("5", ok, t0, "voice without transcript -> transcribed", r.text, results)


def main() -> None:
    target_id = None
    for i, arg in enumerate(sys.argv):
        if arg == "--id" and i + 1 < len(sys.argv):
            target_id = sys.argv[i + 1]
        elif arg.startswith("--id="):
            target_id = arg.split("=", 1)[1]

    verify_dir = Path(os.environ.get("KIAPI_VERIFY_DIR", ".verify")) / "transcription"
    if verify_dir.exists() and not target_id:
        shutil.rmtree(verify_dir)
    verify_dir.mkdir(parents=True, exist_ok=True)

    results: list[tuple[str, bool]] = []
    print(f"{'=' * 70}\n## kiapi transcription verify  ({BASE_URL})\n{'=' * 70}")
    with httpx.Client(timeout=600.0) as client:
        tests = [test_1, test_2, test_3, test_4, test_5]
        for i, test_fn in enumerate(tests, start=1):
            if target_id and target_id != str(i):
                continue
            test_fn(client, verify_dir, results)

    print(f"\n{'=' * 70}\n## SUMMARY\n{'=' * 70}")
    if not results:
        print(f"\n0/0 passed (Test ID '{target_id}' not found or executed)")
        sys.exit(1)
    passed = sum(1 for _, ok in results if ok)
    for cid, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}: {cid}")
    print(f"\n{passed}/{len(results)} passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
