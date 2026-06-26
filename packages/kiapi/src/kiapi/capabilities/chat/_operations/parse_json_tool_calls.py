"""Shared helper: parse the JSON ``<tool_call>`` tool-call format.

This is Qwen3-Omni's native tool-call format
(``<tool_call>{"name":...,"arguments":{...}}``). It is *shared* because Qwen3.6's
Hermes/XML parser falls back to it when no XML call is present (a variant that
emits JSON still works), so both models reach it. The prefill that *requests* a
JSON call is still model-specific and lives in each model.
"""

import json
from typing import Any

_TAG = "<tool_call>"
_DECODER = json.JSONDecoder()


def parse_json_tool_calls(full_text: str) -> list[dict[str, Any]]:
    """Extract ``[{"name", "arguments"}]`` from JSON ``<tool_call>`` blocks.

    For each ``<tool_call>`` tag we JSON-decode the first object that follows it
    (via ``raw_decode``), so this is robust to a missing ``</tool_call>`` close
    tag and to trailing text after the object. ``arguments`` is a JSON string
    (OpenAI shape). Supports multiple (parallel) calls.
    """
    calls: list[dict[str, Any]] = []
    pos = 0
    while True:
        tag = full_text.find(_TAG, pos)
        if tag == -1:
            break
        brace = full_text.find("{", tag + len(_TAG))
        if brace == -1:
            break
        try:
            obj, end = _DECODER.raw_decode(full_text, brace)
        except json.JSONDecodeError:
            # Lenient fallback: if the JSON is truncated (e.g. hit max_tokens or stopped),
            # try to close the object with common missing suffixes.
            tail = full_text[brace:].strip()
            obj = None
            for suffix in ["", "}", "}}", "}}}", '"}', '"}}', '"}}}', '"]}', '"]}}']:
                try:
                    obj = json.loads(tail + suffix)
                    break
                except json.JSONDecodeError:
                    continue

            if isinstance(obj, dict):
                calls.append(_to_call(obj))
            break  # Truncated, so no more calls can follow

        if isinstance(obj, dict):
            calls.append(_to_call(obj))
        pos = end
    return calls


def _to_call(obj: dict) -> dict[str, Any]:
    """Normalize a {name, arguments} dict to OpenAI shape (arguments as JSON str)."""
    args = obj.get("arguments", {})
    return {
        "name": obj.get("name", ""),
        "arguments": args
        if isinstance(args, str)
        else json.dumps(args, ensure_ascii=False),
    }
