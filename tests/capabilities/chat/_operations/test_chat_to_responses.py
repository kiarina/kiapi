from kiapi.capabilities.chat import (
    ResponsesRequest,
    ResponsesStream,
    completion_to_response,
)

REQ = ResponsesRequest.model_validate({"model": "vlm", "input": "x"})
USAGE = {
    "prompt_tokens": 100,
    "completion_tokens": 7,
    "total_tokens": 107,
    "prompt_tokens_details": {"cached_tokens": 64},
}


def _chunk(delta: dict, finish_reason: str | None = None) -> dict:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion.chunk",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }


def test_completion_with_text_and_tool_calls_becomes_output_items() -> None:
    response = completion_to_response(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Checking.",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "f", "arguments": "{}"},
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": USAGE,
        },
        REQ,
    )

    assert response["object"] == "response"
    assert response["status"] == "completed"
    assert [item["type"] for item in response["output"]] == ["message", "function_call"]
    assert response["output"][0]["content"][0]["text"] == "Checking."
    assert response["output"][1]["call_id"] == "call_1"
    assert response["usage"] == {
        "input_tokens": 100,
        "input_tokens_details": {"cached_tokens": 64},
        "output_tokens": 7,
        "output_tokens_details": {"reasoning_tokens": 0},
        "total_tokens": 107,
    }


def test_length_finish_is_incomplete() -> None:
    response = completion_to_response(
        {
            "choices": [
                {
                    "message": {"role": "assistant", "content": "cut"},
                    "finish_reason": "length",
                }
            ],
            "usage": USAGE,
        },
        REQ,
    )

    assert response["status"] == "incomplete"
    assert response["incomplete_details"] == {"reason": "max_output_tokens"}


def test_stream_text_then_tool_call() -> None:
    stream = ResponsesStream(REQ)
    events = []
    events += stream.feed(_chunk({"role": "assistant"}))
    events += stream.feed(_chunk({"content": "Let me "}))
    events += stream.feed(_chunk({"content": "check."}))
    events += stream.feed(
        _chunk(
            {
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "f"},
                    }
                ]
            }
        )
    )
    events += stream.feed(
        _chunk(
            {
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "call_1",
                        "type": "function",
                        "function": {"arguments": '{"a":1}'},
                    }
                ]
            }
        )
    )
    events += stream.feed(_chunk({}, finish_reason="tool_calls"))
    events += stream.complete(USAGE)

    assert [e["type"] for e in events] == [
        "response.created",
        "response.in_progress",
        "response.output_item.added",
        "response.content_part.added",
        "response.output_text.delta",
        "response.output_text.delta",
        "response.output_text.done",
        "response.content_part.done",
        "response.output_item.done",
        "response.output_item.added",
        "response.function_call_arguments.delta",
        "response.function_call_arguments.done",
        "response.output_item.done",
        "response.completed",
    ]
    assert [e["sequence_number"] for e in events] == list(range(1, len(events) + 1))
    done = events[-1]["response"]
    assert done["status"] == "completed"
    assert done["output"][0]["content"][0]["text"] == "Let me check."
    assert done["output"][1] == {
        "type": "function_call",
        "id": done["output"][1]["id"],
        "call_id": "call_1",
        "name": "f",
        "arguments": '{"a":1}',
        "status": "completed",
    }
    assert done["usage"]["input_tokens_details"]["cached_tokens"] == 64


def test_stream_failure_emits_response_failed() -> None:
    stream = ResponsesStream(REQ)

    events = stream.fail(RuntimeError("boom"))

    assert events[-1]["type"] == "response.failed"
    assert events[-1]["response"]["error"]["message"] == "boom"


def test_flattened_namespaced_calls_split_back() -> None:
    req = ResponsesRequest.model_validate(
        {
            "model": "vlm",
            "input": "x",
            "tools": [
                {
                    "type": "namespace",
                    "name": "mcp__docs",
                    "tools": [{"type": "function", "name": "search"}],
                }
            ],
        }
    )
    completion = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "mcp__docs__search",
                                "arguments": "{}",
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": USAGE,
    }

    item = completion_to_response(completion, req)["output"][0]
    assert (item["namespace"], item["name"]) == ("mcp__docs", "search")

    stream = ResponsesStream(req)
    stream.feed(
        _chunk(
            {
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "call_1",
                        "function": {"name": "mcp__docs__search"},
                    }
                ]
            }
        )
    )
    stream.feed(
        _chunk(
            {
                "tool_calls": [
                    {"index": 0, "id": "call_1", "function": {"arguments": "{}"}}
                ]
            }
        )
    )
    done = stream.complete(USAGE)[-1]["response"]["output"][0]
    assert (done["namespace"], done["name"]) == ("mcp__docs", "search")
