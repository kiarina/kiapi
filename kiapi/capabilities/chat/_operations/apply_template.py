"""Shared chat-template application + ``tool_choice`` normalization.

The Qwen chat_template emits a ``<tools>`` system block and asks the model to
reply with tool calls. There is **no native ``tool_choice``**, so each model
implements it by *prefilling* the assistant turn (the prefill is format-specific
and lives in the model). What is shared — and lives here — is the chat-template
call itself plus the ``tool_choice`` normalization that decides the prefill
``kind``.
"""

from typing import Any

# apply_chat_template arguments we set ourselves; a caller's chat_template_kwargs
# must not collide with these (would raise "multiple values for keyword argument").
_RESERVED_TEMPLATE_KWARGS = (
    "conversation",
    "tools",
    "add_generation_prompt",
    "tokenize",
)


def apply_template(  # type: ignore
    processor,
    template_messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    tool_choice: Any,
    chat_template_kwargs: dict[str, Any] | None = None,
) -> tuple[str, str, str | None]:
    """Apply the chat template. Return (prompt_without_prefill, kind, name).

    Shared by every model; the format-specific prefill is added by the caller.
    ``kind`` ∈ auto|none|required|function. ``chat_template_kwargs`` is forwarded
    verbatim to ``apply_chat_template`` (e.g. ``{"enable_thinking": False}``), so
    model-specific template switches pass straight through from the request.
    """
    tok = getattr(processor, "tokenizer", processor)
    kind, name = _normalize_tool_choice(tool_choice)
    effective_tools = None if kind == "none" else (tools or None)
    extra = {
        k: v
        for k, v in (chat_template_kwargs or {}).items()
        if k not in _RESERVED_TEMPLATE_KWARGS
    }
    prompt = tok.apply_chat_template(
        template_messages,
        tools=effective_tools,
        add_generation_prompt=True,
        tokenize=False,
        **extra,
    )
    return prompt, kind, name


def _normalize_tool_choice(tool_choice: Any) -> tuple[str, str | None]:
    """Return (kind, name). kind ∈ auto|none|required|function."""
    if tool_choice is None or tool_choice == "auto":
        return "auto", None
    if tool_choice == "none":
        return "none", None
    if tool_choice in ("required", "any"):
        return "required", None
    if isinstance(tool_choice, str):  # bare tool name
        return "function", tool_choice
    if isinstance(tool_choice, dict):
        if tool_choice.get("type") == "function":
            fn = tool_choice.get("function") or {}
            name = fn.get("name") if isinstance(fn, dict) else None
            if name:
                return "function", name
        name = tool_choice.get("name")
        if name:
            return "function", name
    return "auto", None
