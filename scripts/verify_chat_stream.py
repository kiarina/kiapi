import argparse
import json
import os
import sys
import time
from typing import Any

import httpx

BASE_URL = os.environ.get("KIAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
URL = f"{BASE_URL}/v1/chat/completions"
DEFAULT_MODEL = "qwen3.6-27b"
DEFAULT_MODELS = (DEFAULT_MODEL, "qwen3-omni")

TOOL_WEATHER = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "parameters": {
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        },
    },
}

TOOL_TIMER = {
    "type": "function",
    "function": {
        "name": "set_timer",
        "parameters": {
            "type": "object",
            "properties": {"seconds": {"type": "integer"}},
            "required": ["seconds"],
        },
    },
}


def stream_chat(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[float]]:
    chunks: list[dict[str, Any]] = []
    arrivals: list[float] = []
    started = time.time()

    try:
        with httpx.stream("POST", URL, json=payload, timeout=1200.0) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data = line.removeprefix("data: ").strip()
                if data == "[DONE]":
                    break
                chunks.append(json.loads(data))
                arrivals.append(time.time() - started)
    except httpx.HTTPError as exc:
        print(f"[HTTP ERROR] {exc}")
        if isinstance(exc, httpx.HTTPStatusError):
            print(exc.response.text)
        sys.exit(1)

    return chunks, arrivals


def fold_content(chunks: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for chunk in chunks:
        delta = chunk.get("choices", [{}])[0].get("delta") or {}
        content = delta.get("content")
        if content is not None:
            parts.append(content)
    return "".join(parts)


def content_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        chunk
        for chunk in chunks
        if (chunk.get("choices", [{}])[0].get("delta") or {}).get("content") is not None
    ]


def tool_call_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        chunk
        for chunk in chunks
        if "tool_calls" in (chunk.get("choices", [{}])[0].get("delta") or {})
    ]


def tool_call_entries(
    chunks: list[dict[str, Any]], arrivals: list[float]
) -> list[tuple[int, float, dict[str, Any]]]:
    entries: list[tuple[int, float, dict[str, Any]]] = []
    for chunk_index, chunk in enumerate(chunks):
        delta = chunk.get("choices", [{}])[0].get("delta") or {}
        for entry in delta.get("tool_calls") or []:
            entries.append((chunk_index, arrivals[chunk_index], entry))
    return entries


def finish_reason(chunks: list[dict[str, Any]]) -> str | None:
    reason = None
    for chunk in chunks:
        choice = chunk.get("choices", [{}])[0]
        reason = choice.get("finish_reason") or reason
    return reason


def verify_auto_text_streams(model: str) -> None:
    payload = {
        "model": model,
        "stream": True,
        "messages": [
            {
                "role": "user",
                "content": (
                    "ツールは使わずに、東京の好きなところを日本語で5文で説明してください。"
                    "各文は短めにしてください。"
                ),
            }
        ],
        "tools": [TOOL_WEATHER],
        "tool_choice": "auto",
        "max_completion_tokens": 220,
    }

    chunks, arrivals = stream_chat(payload)
    cchunks = content_chunks(chunks)
    tchunks = tool_call_chunks(chunks)
    text = fold_content(chunks)

    print("\n=== auto_text_streams ===")
    print(f"model: {model}")
    print(f"total_chunks: {len(chunks)}")
    print(f"content_chunks: {len(cchunks)}")
    print(f"tool_call_chunks: {len(tchunks)}")
    print(f"finish_reason: {finish_reason(chunks)}")
    if cchunks:
        first_content_index = chunks.index(cchunks[0])
        print(f"first_content_chunk_index: {first_content_index}")
        print(f"first_content_at_s: {arrivals[first_content_index]:.2f}")
    print("\n--- content ---")
    print(text.strip())

    if not cchunks:
        raise AssertionError("no content chunks were streamed")
    if len(cchunks) < 2:
        raise AssertionError(
            "expected multiple content chunks; tools+auto may still be buffered"
        )
    if "<tool_call>" in text:
        raise AssertionError("raw <tool_call> markup leaked into content stream")


def verify_auto_tool_does_not_leak_markup(model: str) -> None:
    payload = {
        "model": model,
        "stream": True,
        "messages": [{"role": "user", "content": "東京の天気を調べてください。"}],
        "tools": [TOOL_WEATHER],
        "tool_choice": "auto",
        "max_completion_tokens": 220,
    }

    chunks, _arrivals = stream_chat(payload)
    text = fold_content(chunks)

    print("\n=== auto_tool_does_not_leak_markup ===")
    print(f"model: {model}")
    print(f"total_chunks: {len(chunks)}")
    print(f"content_chunks: {len(content_chunks(chunks))}")
    print(f"tool_call_chunks: {len(tool_call_chunks(chunks))}")
    print(f"finish_reason: {finish_reason(chunks)}")
    print("\n--- content ---")
    print(text.strip())

    if "<tool_call>" in text:
        raise AssertionError("raw <tool_call> markup leaked into content stream")


def verify_tool_name_streams_before_arguments(model: str) -> None:
    payload = {
        "model": model,
        "stream": True,
        "messages": [{"role": "user", "content": "東京の天気を調べてください。"}],
        "tools": [TOOL_WEATHER],
        "tool_choice": "auto",
        "max_completion_tokens": 220,
    }

    chunks, arrivals = stream_chat(payload)
    entries = tool_call_entries(chunks, arrivals)
    name_entries = [
        item
        for item in entries
        if item[2].get("function", {}).get("name")
        and "arguments" not in item[2].get("function", {})
    ]
    argument_entries = [
        item for item in entries if "arguments" in item[2].get("function", {})
    ]

    print("\n=== tool_name_streams_before_arguments ===")
    print(f"model: {model}")
    print(f"total_chunks: {len(chunks)}")
    print(f"tool_call_chunks: {len(tool_call_chunks(chunks))}")
    print(f"finish_reason: {finish_reason(chunks)}")
    print("\n--- tool call entries ---")
    for _chunk_index, at_s, entry in entries:
        print(f"at_s={at_s:.2f}")
        print(json.dumps(entry, ensure_ascii=False))

    if not name_entries:
        raise AssertionError("no name-only tool_call delta was streamed")
    if not argument_entries:
        raise AssertionError("no arguments tool_call delta was streamed")

    first_name_index, _first_name_at, first_name = name_entries[0]
    first_args_index, _first_args_at, first_args = argument_entries[0]
    if first_name_index >= first_args_index:
        raise AssertionError("tool name did not stream before arguments")
    if first_name.get("index") != first_args.get("index"):
        raise AssertionError("name and arguments used different tool_call indexes")
    if first_name.get("id") != first_args.get("id"):
        raise AssertionError("name and arguments used different tool_call ids")


def verify_multi_tool_call_units(model: str) -> None:
    payload = {
        "model": model,
        "stream": True,
        "messages": [
            {
                "role": "user",
                "content": (
                    "東京と大阪の天気をそれぞれ調べてください。"
                    "そのあと30秒のタイマーもセットしてください。"
                ),
            }
        ],
        "tools": [TOOL_WEATHER, TOOL_TIMER],
        "tool_choice": "auto",
        "max_completion_tokens": 320,
    }

    chunks, arrivals = stream_chat(payload)
    tchunks = tool_call_chunks(chunks)
    text = fold_content(chunks)

    print("\n=== multi_tool_call_units ===")
    print(f"model: {model}")
    print(f"total_chunks: {len(chunks)}")
    print(f"content_chunks: {len(content_chunks(chunks))}")
    print(f"tool_call_chunks: {len(tchunks)}")
    print(f"finish_reason: {finish_reason(chunks)}")
    print("\n--- tool call chunks ---")
    for chunk in tchunks:
        chunk_index = chunks.index(chunk)
        print(f"at_s={arrivals[chunk_index]:.2f}")
        print(
            json.dumps(chunk["choices"][0]["delta"]["tool_calls"], ensure_ascii=False)
        )
    if text.strip():
        print("\n--- content ---")
        print(text.strip())

    if len(tchunks) < 2:
        raise AssertionError(
            "expected multiple tool_call chunks; completed calls may still be batched"
        )
    if "<tool_call>" in text:
        raise AssertionError("raw <tool_call> markup leaked into content stream")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify chat streaming behavior when tools are present."
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "case",
        nargs="*",
        choices=(
            "auto_text_streams",
            "auto_tool_does_not_leak_markup",
            "tool_name_streams_before_arguments",
            "multi_tool_call_units",
        ),
    )
    args = parser.parse_args()

    print("Starting chat stream verification...")
    print(f"BASE_URL: {BASE_URL}")

    cases = {
        "auto_text_streams": verify_auto_text_streams,
        "auto_tool_does_not_leak_markup": verify_auto_tool_does_not_leak_markup,
        "tool_name_streams_before_arguments": verify_tool_name_streams_before_arguments,
        "multi_tool_call_units": verify_multi_tool_call_units,
    }

    selected_models = DEFAULT_MODELS if len(sys.argv) == 1 else (args.model,)
    selected_cases = args.case or list(cases)
    for model in selected_models:
        for case in selected_cases:
            cases[case](model)

    print("\nAll chat stream checks completed.")


if __name__ == "__main__":
    main()
