"""Shared helper: parse the Hermes/XML ``<function=...>`` tool-call format.

This is Qwen3.6's native tool-call format — a reasoning model that emits:

    <tool_call>
    <function=get_weather>
    <parameter=location>
    大阪
    </parameter>
    </function>
    </tool_call>

Only Qwen3.6 emits it, but the parse is a self-contained text→structured decode
of the same nature as :func:`parse_json_tool_calls`, so both formats live here
side by side. The prefill that *requests* a Hermes call is model-specific and
stays in ``qwen3_5``. If no XML call is present, this falls back to the JSON
parser so a variant that emits JSON still works.
"""

import json
import re
from typing import Any

from .parse_json_tool_calls import parse_json_tool_calls

_FUNC = re.compile(r"<function\s*=\s*([^>\s]+)\s*>(.*?)</function>", re.S)
_FUNC_OPEN = re.compile(r"<function\s*=\s*([^>\s]+)\s*>(.*)$", re.S)
_PARAM = re.compile(r"<parameter\s*=\s*([^>\s]+)\s*>(.*?)</parameter>", re.S)


def parse_hermes_tool_calls(full_text: str) -> list[dict[str, Any]]:
    """Extract ``[{"name", "arguments"}]`` from Hermes ``<function=...>`` blocks.

    ``arguments`` is returned as a JSON string (OpenAI shape). Supports multiple
    (parallel) calls. Falls back to :func:`parse_json_tool_calls` when no XML call
    is present.
    """
    calls: list[dict[str, Any]] = []
    for name, body in _spans(full_text):
        args = {p.group(1).strip(): _coerce(p.group(2)) for p in _PARAM.finditer(body)}
        calls.append({"name": name, "arguments": json.dumps(args, ensure_ascii=False)})

    if not calls:
        return parse_json_tool_calls(full_text)
    return calls


def _spans(full_text: str) -> list[tuple[str, str]]:
    matches = _FUNC.findall(full_text)
    if matches:
        return [(name.strip(), body) for name, body in matches]
    # Lenient: a <function=...> that wasn't closed (truncated / prefilled tail).
    m = _FUNC_OPEN.search(full_text)
    return [(m.group(1).strip(), m.group(2))] if m else []


def _coerce(value: str) -> Any:
    """Best-effort: parse a parameter value as JSON (int/float/bool/null/obj), else str."""
    s = value.strip()
    try:
        return json.loads(s)
    except (json.JSONDecodeError, ValueError):
        return s
