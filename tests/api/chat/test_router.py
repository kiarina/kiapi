from kiapi.api.chat.router import _BASE64_PLACEHOLDER, _redacted_chat_request_dump
from kiapi.capabilities.chat import ChatRequest


def test_parallel_tool_calls_defaults_to_true():  # type: ignore
    req = ChatRequest(
        messages=[{"role": "user", "content": "hi"}],
    )

    assert req.parallel_tool_calls is True


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
