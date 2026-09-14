from kiapi.capabilities.chat._utils.apply_parallel_tool_call_policy import (
    apply_parallel_tool_call_policy,
)


def test_parallel_tool_call_policy_truncates_when_disabled():  # type: ignore
    calls = [{"name": "a", "arguments": "{}"}, {"name": "b", "arguments": "{}"}]

    assert apply_parallel_tool_call_policy(calls, False) == calls[:1]


def test_parallel_tool_call_policy_keeps_multiple_when_enabled():  # type: ignore
    calls = [{"name": "a", "arguments": "{}"}, {"name": "b", "arguments": "{}"}]

    assert apply_parallel_tool_call_policy(calls, True) == calls
