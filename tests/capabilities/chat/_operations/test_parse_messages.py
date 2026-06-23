import tempfile
from pathlib import Path
from typing import Any

from kiapi.capabilities.chat._operations.parse_messages import parse_messages


def test_parse_messages_converts_openai_tool_arguments_for_templates():  # type: ignore
    messages: list[dict[str, Any]] = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "run",
                        "arguments": '{"action":"run_shell","command":"ls"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_123",
            "content": [{"type": "text", "text": "Command execution completed."}],
        },
    ]

    with tempfile.TemporaryDirectory() as d:
        template_messages, images, audios, videos = parse_messages(
            messages,
            Path(d),
            allow={"text", "image", "tools"},
        )

    assert images == []
    assert audios == []
    assert videos == []
    assert messages[0]["content"] is None
    assert isinstance(messages[0]["tool_calls"][0]["function"]["arguments"], str)
    assert template_messages[0]["content"] == ""
    assert template_messages[0]["tool_calls"][0]["function"]["arguments"] == {
        "action": "run_shell",
        "command": "ls",
    }
    assert template_messages[1]["content"] == messages[1]["content"]


def test_parse_messages_uses_fallback_mapping_for_non_object_tool_arguments():  # type: ignore
    messages: list[dict[str, Any]] = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "type": "function",
                    "function": {"name": "echo", "arguments": '"hello"'},
                },
                {
                    "type": "function",
                    "function": {"name": "bad", "arguments": "{oops"},
                },
            ],
        }
    ]

    with tempfile.TemporaryDirectory() as d:
        template_messages, *_ = parse_messages(messages, Path(d))

    calls = template_messages[0]["tool_calls"]
    assert calls[0]["function"]["arguments"] == {"value": "hello"}
    assert calls[1]["function"]["arguments"] == {"_raw": "{oops"}
