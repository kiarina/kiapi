"""Apply OpenAI's ``parallel_tool_calls`` response contract.

Qwen templates do not expose a native switch for this, so each model enforces it
after parsing the generated tool calls: when ``parallel_tool_calls`` is false, at
most one tool call is returned.
"""

from typing import Any


def apply_parallel_tool_call_policy(
    tool_calls: list[dict[str, Any]],
    parallel_tool_calls: bool,
) -> list[dict[str, Any]]:
    if parallel_tool_calls is False:
        return tool_calls[:1]
    return tool_calls
