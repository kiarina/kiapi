"""Shared helper: emit OpenAI-style streaming chunks while accumulating text.

Each model's ``run()`` calls this in the streaming branch, passing its own
format-specific ``parse_tool_calls``. Plain text emits as mlx-vlm yields chunks.
For automatic tool selection, content before the first ``<tool_call>`` tag also
streams immediately; once a tool call starts, the helper buffers raw tool markup.
Tool names stream as soon as they are visible, then completed arguments stream
as OpenAI ``delta.tool_calls`` immediately.
"""

import json
import re
import time
import uuid
from collections.abc import Callable, Iterable
from typing import Any

from .strip_tool_calls import strip_tool_calls

_TOOL_CALL_TAG = "<tool_call>"
_TOOL_CALL_CLOSE_TAG = "</tool_call>"
_HERMES_FUNCTION_OPEN = re.compile(r"<function\s*=\s*([^>\s]+)\s*>", re.S)
_JSON_NAME = re.compile(r'"name"\s*:\s*"((?:\\.|[^"\\])*)"', re.S)


def emit_streaming_response(
    *,
    model_name: str,
    prefill: str,
    chunks: Iterable,
    emit: Callable[[dict], None],
    parse_tool_calls: Callable[[str], list[dict[str, Any]]],
    buffer_for_tools: bool,
    completed_tool_call_text: Callable[[str], str] | None = None,
) -> tuple[str, float, object | None, list[dict[str, Any]]]:
    """Stream chunks to ``emit`` and return (full_text, elapsed, last_chunk, tool_calls)."""
    stream_id, created = _new_stream_state()
    full = prefill
    last = None
    pending_content = ""
    emitted_content_chars = 0
    tool_call_ids: list[str] = []
    streamed_tool_call_name_count = 0
    streamed_tool_call_count = 0
    buffering_tool_call = bool(prefill)
    stream_until_tool_call = buffer_for_tools and not prefill
    completed_tool_call_text = completed_tool_call_text or _completed_tool_call_text

    t0 = time.time()
    emit(
        _format_stream_chunk(
            model_name=model_name,
            delta={"role": "assistant"},
            chunk_id=stream_id,
            created=created,
        )
    )

    def emit_content(text: str) -> None:
        nonlocal emitted_content_chars
        if not text:
            return
        emitted_content_chars += len(text)
        emit(
            _format_stream_chunk(
                model_name=model_name,
                delta={"content": text},
                chunk_id=stream_id,
                created=created,
            )
        )

    def tool_call_id(index: int) -> str:
        while len(tool_call_ids) <= index:
            tool_call_ids.append(f"call_{uuid.uuid4().hex[:24]}")
        return tool_call_ids[index]

    def emit_tool_call_names(names: list[str]) -> None:
        nonlocal streamed_tool_call_name_count
        for name in names[streamed_tool_call_name_count:]:
            index = streamed_tool_call_name_count
            emit(
                _format_stream_chunk(
                    model_name=model_name,
                    delta={
                        "tool_calls": [
                            _format_stream_tool_call_name(
                                index=index,
                                call_id=tool_call_id(index),
                                name=name,
                            )
                        ]
                    },
                    chunk_id=stream_id,
                    created=created,
                )
            )
            streamed_tool_call_name_count += 1

    def emit_tool_calls(tool_calls: list[dict[str, Any]]) -> None:
        nonlocal streamed_tool_call_count, streamed_tool_call_name_count
        for tool_call in tool_calls:
            index = streamed_tool_call_count
            include_name = index >= streamed_tool_call_name_count
            emit(
                _format_stream_chunk(
                    model_name=model_name,
                    delta={
                        "tool_calls": [
                            _format_stream_tool_call(
                                index=index,
                                call_id=tool_call_id(index),
                                call=tool_call,
                                include_name=include_name,
                            )
                        ]
                    },
                    chunk_id=stream_id,
                    created=created,
                )
            )
            streamed_tool_call_count = index + 1
            if include_name:
                streamed_tool_call_name_count = index + 1

    def emit_completed_tool_calls() -> None:
        completed = completed_tool_call_text(full)
        if not completed:
            return
        completed_calls = parse_tool_calls(completed)
        new_calls = completed_calls[streamed_tool_call_count:]
        emit_tool_calls(new_calls)

    for chunk in chunks:
        last = chunk
        text = str(getattr(chunk, "text", "") or "")
        if not text:
            continue
        full += text
        if not buffer_for_tools:
            emit_content(text)
        elif stream_until_tool_call and not buffering_tool_call:
            pending_content += text
            tag_index = pending_content.find(_TOOL_CALL_TAG)
            if tag_index >= 0:
                emit_content(pending_content[:tag_index])
                pending_content = ""
                buffering_tool_call = True
            else:
                keep = len(_TOOL_CALL_TAG) - 1
                if len(pending_content) > keep:
                    emit_content(pending_content[:-keep])
                    pending_content = pending_content[-keep:]
        if buffer_for_tools and buffering_tool_call:
            emit_tool_call_names(_partial_tool_call_names(full))
            emit_completed_tool_calls()

    elapsed = time.time() - t0
    tool_calls = parse_tool_calls(full)
    if tool_calls:
        preamble = strip_tool_calls(full)
        if buffer_for_tools and preamble and emitted_content_chars == 0:
            emit(
                _format_stream_chunk(
                    model_name=model_name,
                    delta={"content": preamble},
                    chunk_id=stream_id,
                    created=created,
                )
            )
        emit_tool_calls(tool_calls[streamed_tool_call_count:])
        emit(
            _format_stream_chunk(
                model_name=model_name,
                delta={},
                finish_reason="tool_calls",
                chunk_id=stream_id,
                created=created,
            )
        )
    else:
        if buffer_for_tools and full:
            emit_content(full[emitted_content_chars:])
        emit(
            _format_stream_chunk(
                model_name=model_name,
                delta={},
                finish_reason="stop",
                chunk_id=stream_id,
                created=created,
            )
        )

    return full, elapsed, last, tool_calls


def _partial_tool_call_names(full_text: str) -> list[str]:
    """Return tool names that are visible before full arguments are parseable."""
    names = _partial_hermes_tool_call_names(full_text)
    if names:
        return names
    return _partial_json_tool_call_names(full_text)


def _partial_hermes_tool_call_names(full_text: str) -> list[str]:
    return [
        match.group(1).strip() for match in _HERMES_FUNCTION_OPEN.finditer(full_text)
    ]


def _partial_json_tool_call_names(full_text: str) -> list[str]:
    names: list[str] = []
    pos = 0
    while True:
        tag = full_text.find(_TOOL_CALL_TAG, pos)
        if tag == -1:
            break
        next_tag = full_text.find(_TOOL_CALL_TAG, tag + len(_TOOL_CALL_TAG))
        end = next_tag if next_tag != -1 else len(full_text)
        segment = full_text[tag:end]
        if match := _JSON_NAME.search(segment):
            names.append(_decode_json_string(match.group(1)))
        pos = tag + len(_TOOL_CALL_TAG)
    return names


def _decode_json_string(value: str) -> str:
    try:
        decoded = json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return value
    return decoded if isinstance(decoded, str) else value


def _new_stream_state() -> tuple[str, int]:
    """Create the id/timestamp shared by every chunk in one stream."""
    return f"chatcmpl-{uuid.uuid4().hex}", int(time.time())


def _completed_tool_call_text(full_text: str) -> str:
    """Return text through the last closed tool_call block, or empty if none."""
    close = full_text.rfind(_TOOL_CALL_CLOSE_TAG)
    if close < 0:
        return ""
    return full_text[: close + len(_TOOL_CALL_CLOSE_TAG)]


def _format_stream_chunk(
    *,
    model_name: str,
    delta: dict[str, Any],
    finish_reason: str | None = None,
    chunk_id: str,
    created: int,
) -> dict:
    """Build an OpenAI-compatible ``chat.completion.chunk`` dict."""
    return {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model_name,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }


def _format_stream_tool_call_name(
    *,
    index: int,
    call_id: str,
    name: str,
) -> dict[str, Any]:
    """Shape the first tool-call delta once the function name is known."""
    return {
        "index": index,
        "id": call_id,
        "type": "function",
        "function": {"name": name},
    }


def _format_stream_tool_call(
    *,
    index: int,
    call_id: str,
    call: dict[str, Any],
    include_name: bool,
) -> dict[str, Any]:
    """Shape a completed tool-call delta, avoiding duplicate streamed names."""
    function = {"arguments": call["arguments"]}
    if include_name:
        function["name"] = call["name"]
    return {
        "index": index,
        "id": call_id,
        "type": "function",
        "function": function,
    }
