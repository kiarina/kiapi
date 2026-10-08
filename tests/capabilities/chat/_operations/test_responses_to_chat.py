import pytest

from kiapi.capabilities import ValidationError
from kiapi.capabilities.chat import ResponsesRequest, responses_to_chat


def _convert(**fields):  # type: ignore
    return responses_to_chat(
        ResponsesRequest.model_validate({"model": "vlm", **fields}), stream=False
    )


def test_string_input_becomes_a_user_message_after_instructions() -> None:
    chat = _convert(instructions="Be brief.", input="Hello")

    assert chat.messages == [
        {"role": "system", "content": "Be brief."},
        {"role": "user", "content": "Hello"},
    ]


def test_leading_developer_messages_merge_into_the_system_message() -> None:
    chat = _convert(
        instructions="Base.",
        input=[
            {
                "type": "message",
                "role": "developer",
                "content": [
                    {"type": "input_text", "text": "Skills."},
                    {"type": "input_text", "text": " Permissions."},
                ],
            },
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Hi"}],
            },
            {"type": "message", "role": "developer", "content": "Later note."},
        ],
    )

    assert chat.messages == [
        {"role": "system", "content": "Base.\n\nSkills. Permissions."},
        {"role": "user", "content": "Hi"},
        {"role": "user", "content": "Later note."},
    ]


def test_function_calls_and_outputs_become_tool_calls_and_tool_messages() -> None:
    chat = _convert(
        input=[
            {"type": "message", "role": "user", "content": "Run it"},
            {"type": "reasoning", "summary": []},
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Running."}],
            },
            {
                "type": "function_call",
                "id": "fc_1",
                "call_id": "call_1",
                "name": "exec_command",
                "arguments": '{"cmd":"ls"}',
            },
            {
                "type": "function_call",
                "id": "fc_2",
                "call_id": "call_2",
                "name": "exec_command",
                "arguments": '{"cmd":"pwd"}',
            },
            {"type": "function_call_output", "call_id": "call_1", "output": "a.txt"},
            {
                "type": "function_call_output",
                "call_id": "call_2",
                "output": [{"type": "input_text", "text": "/tmp"}],
            },
        ],
    )

    assert chat.messages[1] == {
        "role": "assistant",
        "content": "Running.",
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "exec_command", "arguments": '{"cmd":"ls"}'},
            },
            {
                "id": "call_2",
                "type": "function",
                "function": {"name": "exec_command", "arguments": '{"cmd":"pwd"}'},
            },
        ],
    }
    assert chat.messages[2:] == [
        {"role": "tool", "tool_call_id": "call_1", "content": "a.txt"},
        {"role": "tool", "tool_call_id": "call_2", "content": "/tmp"},
    ]


def test_function_call_without_a_preceding_assistant_message_starts_one() -> None:
    chat = _convert(
        input=[
            {"type": "message", "role": "user", "content": "Run it"},
            {
                "type": "function_call",
                "call_id": "call_1",
                "name": "f",
                "arguments": "{}",
            },
        ],
    )

    assert chat.messages[1]["role"] == "assistant"
    assert chat.messages[1]["content"] is None


def test_image_parts_become_image_url_parts() -> None:
    chat = _convert(
        input=[
            {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "What is this?"},
                    {"type": "input_image", "image_url": "data:image/png;base64,AAAA"},
                ],
            }
        ],
    )

    assert chat.messages[0]["content"] == [
        {"type": "text", "text": "What is this?"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
    ]


def test_tools_tool_choice_and_limits_map_to_chat_fields() -> None:
    chat = _convert(
        input="x",
        tools=[
            {
                "type": "function",
                "name": "f",
                "description": "d",
                "parameters": {"type": "object"},
                "strict": False,
            }
        ],
        tool_choice={"type": "function", "name": "f"},
        parallel_tool_calls=False,
        max_output_tokens=64,
        temperature=0.2,
        reasoning={"effort": "medium"},
        store=False,
        include=["reasoning.encrypted_content"],
    )

    assert chat.tools == [
        {
            "type": "function",
            "function": {
                "name": "f",
                "description": "d",
                "parameters": {"type": "object"},
            },
        }
    ]
    assert chat.tool_choice == {"type": "function", "function": {"name": "f"}}
    assert chat.parallel_tool_calls is False
    assert chat.max_completion_tokens == 64
    assert chat.temperature == 0.2


@pytest.mark.parametrize(
    "fields",
    [
        {"input": "x", "tools": [{"type": "web_search"}]},
        {"input": [{"type": "item_reference", "id": "x"}]},
        {"input": "x", "previous_response_id": "resp_1"},
        {"input": [{"type": "message", "role": "developer", "content": "only system"}]},
    ],
)
def test_unsupported_requests_are_rejected(fields: dict) -> None:
    with pytest.raises(ValidationError):
        _convert(**fields)


def test_namespace_tools_flatten_and_namespaced_calls_rejoin() -> None:
    chat = _convert(
        tools=[
            {
                "type": "namespace",
                "name": "mcp__docs",
                "description": "Docs tools.",
                "tools": [
                    {
                        "type": "function",
                        "name": "search",
                        "parameters": {"type": "object"},
                    }
                ],
            }
        ],
        input=[
            {"type": "message", "role": "user", "content": "Find it"},
            {
                "type": "function_call",
                "call_id": "call_1",
                "namespace": "mcp__docs",
                "name": "search",
                "arguments": "{}",
            },
            {
                "type": "function_call_output",
                "call_id": "call_1",
                "output": [
                    {"type": "input_text", "text": "a"},
                    {"type": "input_image", "image_url": "x"},
                ],
            },
        ],
    )

    assert chat.tools == [
        {
            "type": "function",
            "function": {"name": "mcp__docs__search", "parameters": {"type": "object"}},
        }
    ]
    assert chat.messages[1]["tool_calls"][0]["function"]["name"] == "mcp__docs__search"
    assert chat.messages[2]["content"] == "a\n[input_image omitted]"
