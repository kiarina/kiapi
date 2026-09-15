from types import SimpleNamespace

from kiapi.capabilities.chat._operations.format_response import format_response


def _finish_reason(result: object, tool_calls: list | None = None) -> str:
    response = format_response(
        model_name="m",
        full_text="text",
        elapsed=0.0,
        result=result,
        tool_calls=tool_calls or [],
    )
    return str(response["choices"][0]["finish_reason"])


def test_reports_length_when_generation_was_cut() -> None:
    assert _finish_reason(SimpleNamespace(finish_reason="length")) == "length"


def test_reports_stop_when_generation_ended_on_its_own() -> None:
    assert _finish_reason(SimpleNamespace(finish_reason="stop")) == "stop"
    assert _finish_reason(SimpleNamespace()) == "stop"


def test_tool_calls_take_precedence_over_length() -> None:
    tool_calls = [{"name": "f", "arguments": "{}"}]

    assert (
        _finish_reason(SimpleNamespace(finish_reason="length"), tool_calls)
        == "tool_calls"
    )
