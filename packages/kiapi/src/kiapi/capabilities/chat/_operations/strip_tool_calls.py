"""Shared helper: the assistant preamble before any tool call.

Tool calls are emitted at the end of the turn, so everything before the first
``<tool_call>`` tag is the natural-language preamble (often empty). Close-tag
independent and format-independent — both the JSON (Qwen3-Omni) and Hermes/XML
(Qwen3.6) formats use the same ``<tool_call>`` opening tag — so it is shared.
"""

_TAG = "<tool_call>"


def strip_tool_calls(full_text: str) -> str:
    """Return the text before the first ``<tool_call>`` tag (stripped)."""
    tag = full_text.find(_TAG)
    return (full_text if tag == -1 else full_text[:tag]).strip()
