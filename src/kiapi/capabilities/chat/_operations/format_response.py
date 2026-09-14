"""Shared helper: shape a model's raw output into an OpenAI chat.completion.

Identical across models, so it lives here and each model's ``run()`` calls it
after generating. **Tool-call parsing is the model's job** (it's format-specific:
JSON for Qwen3-Omni, Hermes/XML for Qwen3.6) — the model passes the already-parsed
``tool_calls`` in. The natural-language preamble is derived from the shared
``<tool_call>`` opening tag (``strip_tool_calls``).
"""

import time
import uuid
from typing import Any

from .strip_tool_calls import strip_tool_calls


def format_response(  # type: ignore
    *,
    model_name: str,
    full_text: str,
    elapsed: float,
    result,
    tool_calls: list[dict[str, Any]],
) -> dict:
    """Build an OpenAI ``chat.completion`` dict.

    ``full_text`` is the assistant text including any prefill (so a prefilled tool
    call is reconstructed). ``tool_calls`` is the model's parsed list of
    ``{"name", "arguments"}`` (``arguments`` already a JSON string). ``result`` is
    whatever ``generate`` returned (used only for token counts).
    """
    message: dict = {"role": "assistant"}
    if tool_calls:
        preamble = strip_tool_calls(full_text)
        message["content"] = preamble or None
        message["tool_calls"] = [
            {
                "id": f"call_{uuid.uuid4().hex[:24]}",
                "type": "function",
                "function": {"name": c["name"], "arguments": c["arguments"]},
            }
            for c in tool_calls
        ]
        finish_reason = "tool_calls"
    else:
        message["content"] = full_text
        finish_reason = "stop"

    prompt_tokens = _int_attr(result, "prompt_tokens", "prompt_token_count")
    completion_tokens = _int_attr(result, "generation_tokens", "completion_token_count")

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_name,
        "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "timings": {"total_s": round(elapsed, 2)},
    }


def _int_attr(obj, *names: str) -> int:  # type: ignore
    for n in names:
        v = getattr(obj, n, None)
        if isinstance(v, (int, float)):
            return int(v)
    return 0
