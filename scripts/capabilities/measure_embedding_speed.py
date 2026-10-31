"""Measure /v1/embeddings speed by input length against a running server.

Usage:
    uv run python scripts/capabilities/measure_embedding_speed.py

Env:
    KIAPI_BASE_URL   server base URL (default http://127.0.0.1:8000)
"""

import os
import statistics
from pathlib import Path
from typing import Any

import httpx

BASE_URL = os.environ.get("KIAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ROOT = Path(__file__).resolve().parents[2]
TEXT = (ROOT / "ARCHITECTURE.md").read_text() + (ROOT / "README.md").read_text()
TARGET_TOKENS = (128, 512, 2048, 4096, 8192, 16384, 28000)
SPLITS = (2, 4, 8, 16, 32)
LONG_REPEATS = 2
SHORT_REPEATS = 5
LONG_TOKENS = 8192


def embed(value: str | list[str]) -> dict[str, Any]:
    response = httpx.post(
        f"{BASE_URL}/v1/embeddings", json={"input": value}, timeout=600.0
    )
    response.raise_for_status()
    body: dict[str, Any] = response.json()
    return body


def sample(chars: int) -> str:
    return (TEXT * (chars // len(TEXT) + 1))[:chars]


def main() -> None:
    embed("warm up")
    tokens_per_char = embed(sample(2000))["usage"]["prompt_tokens"] / 2000

    print("tokens  seconds  s/1k tokens")
    for target in TARGET_TOKENS:
        text = sample(int(target / tokens_per_char))
        repeats = LONG_REPEATS if target > LONG_TOKENS else SHORT_REPEATS
        results = [embed(text) for _ in range(repeats)]
        tokens = results[0]["usage"]["prompt_tokens"]
        seconds = statistics.median(r["timings"]["total_s"] for r in results)
        print(f"{tokens:6d}  {seconds:7.2f}  {seconds / tokens * 1000:6.2f}")

    text = sample(int(TARGET_TOKENS[-1] / tokens_per_char))
    print("\nitems  seconds")
    for items in SPLITS:
        size = len(text) // items
        parts = [text[i : i + size] for i in range(0, size * items, size)]
        print(f"{items:5d}  {embed(parts)['timings']['total_s']:7.2f}")


if __name__ == "__main__":
    main()
