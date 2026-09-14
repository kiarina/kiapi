_FUNCTION_CLOSE_TAG = "</function>"


def completed_hermes_tool_call_text(full_text: str) -> str:
    """Return text through the last closed Hermes function call."""
    close = full_text.rfind(_FUNCTION_CLOSE_TAG)
    if close < 0:
        return ""
    return full_text[: close + len(_FUNCTION_CLOSE_TAG)]
