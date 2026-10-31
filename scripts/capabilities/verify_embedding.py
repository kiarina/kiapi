"""End-to-end verification for kiapi's embedding capability against a running server.

Ported from mlx-embedding-server's scripts/verify.py. Exercises both default
embedding models through real embeddings and checks each expected outcome: text
on the text model, text/image/both on the VL model, batches, `dimensions`, base64,
plus the error paths (unsupported modality, unknown model, empty input, oversized
input).

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
import struct
import sys
import time

import httpx

BASE_URL = os.environ.get("KIAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
URL = f"{BASE_URL}/v1/embeddings"
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
# expect: ("ok", vector_count, dimension) | ("status", code)
def cases(img_b64: str):  # type: ignore
    return [
        (
            "1",
            "text => embedding (default model)",
            {"input": "今日はいい天気ですね"},
            ("ok", 1, 4096),
        ),
        (
            "2",
            "text on the VL model",
            {"model": "vl", "input": "a photo of a cat"},
            ("ok", 1, 2048),
        ),
        (
            "3",
            "image on the VL model",
            {"model": "vl", "input": [{"image": img_b64}]},
            ("ok", 1, 2048),
        ),
        (
            "4",
            "text + image on the VL model",
            {"model": "vl", "input": [{"text": "猫", "image": img_b64}]},
            ("ok", 1, 2048),
        ),
        (
            "5",
            "array input",
            {"input": ["一つ目", "二つ目", "三つ目"]},
            ("ok", 3, 4096),
        ),
        ("6", "dimensions", {"input": "短くする", "dimensions": 256}, ("ok", 1, 256)),
        (
            "7",
            "image to the text-only model => 400",
            {"model": "qwen3-embedding-8b", "input": [{"image": img_b64}]},
            ("status", 400),
        ),
        (
            "8",
            "unknown model => 400",
            {"model": "gpt-9", "input": "hi"},
            ("status", 400),
        ),
        (
            "9",
            "empty input => 400",
            {"model": "qwen3-embedding-8b", "input": ""},
            ("status", 400),
        ),
        (
            "10",
            "dimensions out of range => 400",
            {"input": "hi", "dimensions": 8},
            ("status", 400),
        ),
        (
            "11",
            "over the token limit => 400",
            {"input": "word " * 40000},
            ("status", 400),
        ),
    ]


def check(expect, r: httpx.Response):  # type: ignore
    kind = expect[0]
    if kind == "status":
        return r.status_code == expect[1], f"status={r.status_code}"
    # expect ok
    if r.status_code != 200:
        return False, f"status={r.status_code} {r.text[:150]}"
    body = r.json()
    vectors = [item["embedding"] for item in body["data"]]
    norms = [_l2(vector) for vector in vectors]
    ok = (
        body["object"] == "list"
        and len(vectors) == expect[1]
        and all(len(vector) == expect[2] for vector in vectors)
        and all(abs(norm - 1.0) < 1e-3 for norm in norms)
    )
    return ok, (
        f"n={len(vectors)} dim={len(vectors[0])} ‖v‖={norms[0]:.3f} usage={body['usage']}"
    )


def check_batch_and_base64() -> tuple[bool, str]:
    texts = ["今日はいい天気ですね", "明日は雨です"]
    batch = post({"input": texts}).json()
    encoded = post({"input": texts[1], "encoding_format": "base64"}).json()
    raw = base64.b64decode(encoded["data"][0]["embedding"])
    single = struct.unpack(f"<{len(raw) // 4}f", raw)
    diff = max(
        abs(a - b) for a, b in zip(batch["data"][1]["embedding"], single, strict=True)
    )
    return diff < 1e-3, f"dim={len(single)} batch_vs_base64={diff:.6f}"


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

    if "--fast" not in sys.argv:
        t0 = time.time()
        ok, detail = check_batch_and_base64()
        print(
            f"[batch] {'✓' if ok else '✗'} ({time.time() - t0:5.1f}s) batch and base64\n     {detail}"
        )
        results.append(("batch", ok))

    print(f"\n{'=' * 70}\n## SUMMARY\n{'=' * 70}")
    passed = sum(1 for _, ok in results if ok)
    for cid, ok in results:
        if not ok:
            print(f"  FAIL: {cid}")
    print(f"\n{passed}/{len(results)} passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
