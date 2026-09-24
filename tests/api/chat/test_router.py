import asyncio

import pytest
from pydantic import ValidationError

from kiapi.api.chat.router import (
    _BASE64_PLACEHOLDER,
    _cancel_on_disconnect,
    _redacted_chat_request_dump,
    _stream_usage_chunk,
)
from kiapi.capabilities.chat import ChatRequest
from kiapi.core.job import Job


def test_model_is_required():  # type: ignore
    with pytest.raises(ValidationError):
        ChatRequest(messages=[{"role": "user", "content": "hi"}])  # type: ignore[call-arg]


def test_parallel_tool_calls_defaults_to_true():  # type: ignore
    req = ChatRequest(
        model="vlm",
        messages=[{"role": "user", "content": "hi"}],
    )

    assert req.parallel_tool_calls is True


def test_stream_options_include_usage_defaults_to_false():  # type: ignore
    req = ChatRequest.model_validate(
        {
            "model": "vlm",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
            "stream_options": {},
        }
    )

    assert req.stream_options is not None
    assert req.stream_options.include_usage is False


async def test_disconnect_requests_job_cancel_and_cancels_future() -> None:
    class DisconnectedRequest:
        async def is_disconnected(self) -> bool:
            return True

    job = Job(type="chat")
    fut = asyncio.get_running_loop().create_future()

    await _cancel_on_disconnect(DisconnectedRequest(), job, fut)  # type: ignore[arg-type]

    assert job.cancel_requested()
    assert fut.cancelled()


def test_stream_usage_chunk_uses_stream_identity_and_final_usage():  # type: ignore
    usage = {
        "prompt_tokens": 25000,
        "completion_tokens": 1,
        "total_tokens": 25001,
        "prompt_tokens_details": {"cached_tokens": 24576},
    }

    chunk = _stream_usage_chunk(
        {"id": "different", "model": "qwen3.8-27b", "usage": usage},
        {
            "id": "chatcmpl-stream",
            "created": 123,
            "model": "qwen3.8-27b",
        },
    )

    assert chunk == {
        "id": "chatcmpl-stream",
        "object": "chat.completion.chunk",
        "created": 123,
        "model": "qwen3.8-27b",
        "choices": [],
        "usage": usage,
    }


def test_redacted_chat_request_dump_masks_message_base64_only():  # type: ignore
    audio_b64 = "a" * 128
    req = ChatRequest(
        model="qwen3-omni",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "keep this text"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg"
                        },
                    },
                    {
                        "type": "input_audio",
                        "input_audio": {"data": audio_b64, "format": "wav"},
                    },
                    {
                        "type": "video_url",
                        "video_url": {"url": "https://example.com/video.mp4"},
                    },
                ],
            }
        ],
    )

    dumped = _redacted_chat_request_dump(req)

    assert "keep this text" in dumped
    assert "https://example.com/video.mp4" in dumped
    assert f"data:image/png;base64,{_BASE64_PLACEHOLDER}" in dumped
    assert f'"data": "{_BASE64_PLACEHOLDER}"' in dumped
    assert "iVBORw0KGgoAAAANSUhEUg" not in dumped
    assert audio_b64 not in dumped


def test_redacted_chat_request_dump_masks_bare_base64_media_aliases():  # type: ignore
    image_b64 = "b" * 128
    req = ChatRequest(
        model="vlm",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image_b64},
                    {"type": "audio", "audio": "/tmp/audio.wav"},
                    {"type": "text", "text": "not base64"},
                ],
            }
        ],
    )

    dumped = _redacted_chat_request_dump(req)

    assert _BASE64_PLACEHOLDER in dumped
    assert "/tmp/audio.wav" in dumped
    assert "not base64" in dumped
    assert image_b64 not in dumped
