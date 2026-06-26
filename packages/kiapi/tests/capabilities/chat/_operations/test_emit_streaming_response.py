from types import SimpleNamespace
from typing import Any

from kiapi.capabilities.chat._operations.completed_hermes_tool_call_text import (
    completed_hermes_tool_call_text,
)
from kiapi.capabilities.chat._operations.emit_streaming_response import (
    emit_streaming_response,
)
from kiapi.capabilities.chat._operations.parse_hermes_tool_calls import (
    parse_hermes_tool_calls,
)
from kiapi.capabilities.chat._operations.parse_json_tool_calls import (
    parse_json_tool_calls,
)


def _contents(events: list[dict[str, Any]]) -> list[str]:
    out = []
    for event in events:
        delta = event["choices"][0]["delta"]
        if "content" in delta:
            out.append(delta["content"])
    return out


def _tool_call_deltas(events: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    return [
        event["choices"][0]["delta"]["tool_calls"]
        for event in events
        if "tool_calls" in event["choices"][0]["delta"]
    ]


def test_auto_tool_streams_text_until_tool_call_tag_split_across_chunks() -> None:
    events: list[dict[str, Any]] = []

    full, _elapsed, _last, tool_calls = emit_streaming_response(
        model_name="test-model",
        prefill="",
        chunks=[
            SimpleNamespace(text="先に説明します。<tool"),
            SimpleNamespace(
                text='_call>{"name":"get_weather","arguments":{"location":"東京"}}'
            ),
        ],
        emit=events.append,
        parse_tool_calls=lambda text: (
            [{"name": "get_weather", "arguments": '{"location":"東京"}'}]
            if "<tool_call>" in text
            else []
        ),
        buffer_for_tools=True,
    )

    assert (
        full
        == '先に説明します。<tool_call>{"name":"get_weather","arguments":{"location":"東京"}}'
    )
    assert tool_calls == [{"name": "get_weather", "arguments": '{"location":"東京"}'}]
    assert "".join(_contents(events)) == "先に説明します。"

    tool_call_deltas = _tool_call_deltas(events)
    assert len(tool_call_deltas) == 2
    assert tool_call_deltas[0][0]["function"]["name"] == "get_weather"
    assert tool_call_deltas[0][0]["function"].get("arguments") is None
    assert tool_call_deltas[1][0]["function"] == {"arguments": '{"location":"東京"}'}
    assert tool_call_deltas[1][0]["index"] == tool_call_deltas[0][0]["index"]
    assert all("<tool_call>" not in content for content in _contents(events))


def test_auto_tool_streaming_flushes_all_text_when_no_tool_call_is_generated() -> None:
    events: list[dict[str, Any]] = []

    full, _elapsed, _last, tool_calls = emit_streaming_response(
        model_name="test-model",
        prefill="",
        chunks=[
            SimpleNamespace(text="これは"),
            SimpleNamespace(text="通常の"),
            SimpleNamespace(text="回答です。"),
        ],
        emit=events.append,
        parse_tool_calls=lambda _text: [],
        buffer_for_tools=True,
    )

    assert full == "これは通常の回答です。"
    assert tool_calls == []
    assert "".join(_contents(events)) == "これは通常の回答です。"
    assert events[-1]["choices"][0]["finish_reason"] == "stop"


def test_forced_tool_choice_still_buffers_until_final_parse() -> None:
    events: list[dict[str, Any]] = []

    emit_streaming_response(
        model_name="test-model",
        prefill="<tool_call>\n",
        chunks=[SimpleNamespace(text='{"name":"get_weather","arguments":{}}')],
        emit=events.append,
        parse_tool_calls=lambda _text: [{"name": "get_weather", "arguments": "{}"}],
        buffer_for_tools=True,
    )

    assert _contents(events) == []
    assert any("tool_calls" in event["choices"][0]["delta"] for event in events)


def test_streams_each_completed_tool_call_once() -> None:
    events: list[dict[str, Any]] = []

    full, _elapsed, _last, tool_calls = emit_streaming_response(
        model_name="test-model",
        prefill="<tool_call>\n",
        chunks=[
            SimpleNamespace(
                text='{"name":"get_weather","arguments":{"location":"東京"}}</tool_call>'
            ),
            SimpleNamespace(text='<tool_call>{"name":"set_timer","arguments":'),
            SimpleNamespace(text='{"seconds":30}}</tool_call>'),
        ],
        emit=events.append,
        parse_tool_calls=parse_json_tool_calls,
        buffer_for_tools=True,
    )

    assert tool_calls == [
        {"name": "get_weather", "arguments": '{"location": "東京"}'},
        {"name": "set_timer", "arguments": '{"seconds": 30}'},
    ]
    assert full == (
        '<tool_call>\n{"name":"get_weather","arguments":{"location":"東京"}}</tool_call>'
        '<tool_call>{"name":"set_timer","arguments":{"seconds":30}}</tool_call>'
    )

    tool_call_deltas = _tool_call_deltas(events)

    assert len(tool_call_deltas) == 4
    assert tool_call_deltas[0][0]["index"] == 0
    assert tool_call_deltas[0][0]["function"]["name"] == "get_weather"
    assert tool_call_deltas[1][0]["index"] == 0
    assert tool_call_deltas[1][0]["id"] == tool_call_deltas[0][0]["id"]
    assert tool_call_deltas[1][0]["function"] == {"arguments": '{"location": "東京"}'}
    assert tool_call_deltas[2][0]["index"] == 1
    assert tool_call_deltas[2][0]["function"]["name"] == "set_timer"
    assert tool_call_deltas[3][0]["index"] == 1
    assert tool_call_deltas[3][0]["id"] == tool_call_deltas[2][0]["id"]
    assert tool_call_deltas[3][0]["function"] == {"arguments": '{"seconds": 30}'}
    assert events[-1]["choices"][0]["finish_reason"] == "tool_calls"


def test_streams_each_completed_hermes_function_once() -> None:
    events: list[dict[str, Any]] = []

    full, _elapsed, _last, tool_calls = emit_streaming_response(
        model_name="test-model",
        prefill="<tool_call>\n",
        chunks=[
            SimpleNamespace(
                text=(
                    "<function=get_weather>\n"
                    "<parameter=location>東京</parameter>\n"
                    "</function>\n"
                )
            ),
            SimpleNamespace(
                text=("<function=get_weather>\n<parameter=location>大阪</parameter>\n")
            ),
            SimpleNamespace(text="</function>\n</tool_call>"),
        ],
        emit=events.append,
        parse_tool_calls=parse_hermes_tool_calls,
        buffer_for_tools=True,
        completed_tool_call_text=completed_hermes_tool_call_text,
    )

    assert tool_calls == [
        {"name": "get_weather", "arguments": '{"location": "東京"}'},
        {"name": "get_weather", "arguments": '{"location": "大阪"}'},
    ]
    assert full == (
        "<tool_call>\n"
        "<function=get_weather>\n"
        "<parameter=location>東京</parameter>\n"
        "</function>\n"
        "<function=get_weather>\n"
        "<parameter=location>大阪</parameter>\n"
        "</function>\n"
        "</tool_call>"
    )

    tool_call_deltas = _tool_call_deltas(events)

    assert len(tool_call_deltas) == 4
    assert tool_call_deltas[0][0]["index"] == 0
    assert tool_call_deltas[0][0]["function"] == {"name": "get_weather"}
    assert tool_call_deltas[1][0]["index"] == 0
    assert tool_call_deltas[1][0]["id"] == tool_call_deltas[0][0]["id"]
    assert tool_call_deltas[1][0]["function"] == {"arguments": '{"location": "東京"}'}
    assert tool_call_deltas[2][0]["index"] == 1
    assert tool_call_deltas[2][0]["function"] == {"name": "get_weather"}
    assert tool_call_deltas[3][0]["index"] == 1
    assert tool_call_deltas[3][0]["id"] == tool_call_deltas[2][0]["id"]
    assert tool_call_deltas[3][0]["function"] == {"arguments": '{"location": "大阪"}'}
    assert events[-1]["choices"][0]["finish_reason"] == "tool_calls"


def test_streams_tool_call_name_before_arguments_are_complete() -> None:
    events: list[dict[str, Any]] = []

    emit_streaming_response(
        model_name="test-model",
        prefill="<tool_call>\n",
        chunks=[
            SimpleNamespace(text="<function=get_weather>\n"),
            SimpleNamespace(text="<parameter=location>東京</parameter>\n</function>"),
        ],
        emit=events.append,
        parse_tool_calls=parse_hermes_tool_calls,
        buffer_for_tools=True,
        completed_tool_call_text=completed_hermes_tool_call_text,
    )

    tool_call_deltas = _tool_call_deltas(events)

    assert tool_call_deltas[0][0]["index"] == 0
    assert tool_call_deltas[0][0]["type"] == "function"
    assert tool_call_deltas[0][0]["function"] == {"name": "get_weather"}
    assert tool_call_deltas[1][0]["index"] == 0
    assert tool_call_deltas[1][0]["id"] == tool_call_deltas[0][0]["id"]
    assert tool_call_deltas[1][0]["function"] == {"arguments": '{"location": "東京"}'}
