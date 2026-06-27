"""End-to-end verification for kiapi's embedding capability against a running server.

Ported from mlx-embedding-server's scripts/verify.py. Exercises both default
embedding models through real embeddings and checks each expected outcome: text
on the text model, text/image/both on the VL model, plus the error paths
(unsupported modality, unknown model, empty request).

Usage:
    # start the server first, e.g.:
    #   KIAPI_PORT=8000 KIAPI_MEMORY_LIMIT_GB=110 uv run kiapi
    uv run python scripts/capabilities/verify_embedding.py

Env:
    KIAPI_BASE_URL   server base URL (default http://127.0.0.1:8000)
    KIAPI_IMAGE      image to embed (default: kiapi/tests/assets/miineko.png)
"""

import base64
import math
import os
import sys
import time

import httpx

BASE_URL = os.environ.get("KIAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
URL = f"{BASE_URL}/v1/embedding"
HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IMAGE_PATH = os.environ.get(
    "KIAPI_IMAGE", os.path.join(HERE, "tests", "assets", "miineko.png")
)


def _image_b64() -> str:
    with open(IMAGE_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode()


def post(body: dict) -> httpx.Response:
    return httpx.post(URL, json=body, timeout=600.0)


def _l2(vec) -> float:  # type: ignore
    return math.sqrt(sum(x * x for x in vec))


# --- cases: (id, desc, body, expect) ---
# expect: ("ok", min_dim) | ("status", code)
def cases(img_b64: str):  # type: ignore
    return [
        (
            "1",
            "text => embedding (default model)",
            {"text": "今日はいい天気ですね"},
            ("ok", 1),
        ),
        (
            "2",
            "text on the VL model",
            {"model": "vl", "text": "a photo of a cat"},
            ("ok", 1),
        ),
        ("3", "image on the VL model", {"model": "vl", "image": img_b64}, ("ok", 1)),
        (
            "4",
            "text + image on the VL model",
            {"model": "vl", "text": "猫", "image": img_b64},
            ("ok", 1),
        ),
        (
            "5",
            "image to the text-only model => 400",
            {"model": "qwen3-embedding-8b", "image": img_b64},
            ("status", 400),
        ),
        (
            "6",
            "unknown model => 400",
            {"model": "gpt-9", "text": "hi"},
            ("status", 400),
        ),
        ("7", "empty request => 400", {"model": "qwen3-embedding-8b"}, ("status", 400)),
    ]


def check(expect, r: httpx.Response):  # type: ignore
    kind = expect[0]
    if kind == "status":
        return r.status_code == expect[1], f"status={r.status_code}"
    # expect ok
    if r.status_code != 200:
        return False, f"status={r.status_code} {r.text[:150]}"
    body = r.json()
    dim = body.get("dimension", 0)
    vec = body.get("embedding") or []
    norm = _l2(vec)
    ok = dim >= expect[1] and len(vec) == dim
    return ok, f"dim={dim} ‖v‖={norm:.3f}"


def main():  # type: ignore
    img_b64 = _image_b64()
    results = []
    print(f"{'=' * 70}\n## kiapi embedding verify  ({BASE_URL})\n{'=' * 70}")
    for cid, desc, body, expect in cases(img_b64):
        t0 = time.time()
        try:
            r = post(body)
        except Exception as e:
            print(f"[{cid}] ✗ ERROR  {desc}\n     EXC {type(e).__name__}: {e}")
            results.append((cid, False))
            continue
        dt = time.time() - t0
        ok, detail = check(expect, r)
        print(f"[{cid}] {'✓' if ok else '✗'} ({dt:5.1f}s) {desc}\n     {detail}")
        results.append((cid, ok))
        if "--fast" in sys.argv:
            print("\n[FAST MODE] Exiting early.")
            break

    print(f"\n{'=' * 70}\n## SUMMARY\n{'=' * 70}")
    passed = sum(1 for _, ok in results if ok)
    for cid, ok in results:
        if not ok:
            print(f"  FAIL: {cid}")
    print(f"\n{passed}/{len(results)} passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
