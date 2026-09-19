"""Verify appended Omni media through the HTTP API using the normal test assets."""

import base64
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

BASE_URL = os.environ.get("KIAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ASSETS = Path(
    os.environ.get(
        "KIAPI_ASSETS_DIR", str(Path(__file__).resolve().parents[2] / "tests/assets")
    )
)


def part(kind: str, file: str, mime: str) -> dict[str, Any]:
    encoded = base64.b64encode((ASSETS / file).read_bytes()).decode()
    return {
        "type": f"{kind}_url",
        f"{kind}_url": {"url": f"data:{mime};base64,{encoded}"},
    }


def request(messages: list[dict[str, Any]], *, audio_in_video: bool) -> dict[str, Any]:
    response = httpx.post(
        BASE_URL + "/v1/chat/completions",
        json={
            "model": "qwen3-omni",
            "messages": messages,
            "max_completion_tokens": 64,
            "temperature": 0,
            "fps": 0.5,
            "use_audio_in_video": audio_in_video,
        },
        timeout=1200,
    )
    response.raise_for_status()
    result: dict[str, Any] = response.json()
    assert result["choices"][0]["message"]["content"], result
    return result


def main() -> None:
    image = part("image", "miineko.png", "image/png")
    audio = part("audio", "song.wav", "audio/wav")
    video = part("video", "pv.mp4", "video/mp4")
    cases = [
        ("image", [image], False),
        ("audio", [audio], False),
        ("video", [video], False),
        ("audiovisual", [video], True),
        ("mixed", [image, video], True),
    ]
    if "--fast" in sys.argv:
        cases = cases[:1]
    questions = {
        "image": "Describe the appearance of the character in the last image in one sentence.",
        "audio": "Describe the music and voice heard in the last audio clip in one sentence.",
        "video": "Describe the scene and character shown in the last video in one sentence.",
        "audiovisual": "Describe both the visible scene and audible music in the last video in one sentence.",
        "mixed": "Describe the pictured character and the video scene and music in one sentence.",
    }
    for name, media, audio_in_video in cases:
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": f"You are inspecting the {name} prefix regression case. Answer briefly.",
            },
            {
                "role": "user",
                "content": [
                    *media,
                    {"type": "text", "text": questions[name]},
                ],
            },
        ]
        first = request(messages, audio_in_video=audio_in_video)
        continued = [
            *messages,
            {"role": "assistant", "content": first["choices"][0]["message"]["content"]},
            {
                "role": "user",
                "content": [
                    *media,
                    {
                        "type": "text",
                        "text": questions[name],
                    },
                ],
            },
        ]
        second = request(continued, audio_in_video=audio_in_video)
        cached = second["usage"]["prompt_tokens_details"]["cached_tokens"]
        assert 0 < cached < second["usage"]["prompt_tokens"], second
        assert cached >= first["usage"]["prompt_tokens"] - 16, second
        content = (
            second["choices"][0]["message"]["content"].lower().strip().rstrip(".!")
        )
        assert content not in {"understood", "ok", "okay", "got it"}, second
        expected = (
            ("music", "song", "sing", "vocal", "guitar", "rock", "japanese")
            if name == "audio"
            else (
                "pink",
                "pixel",
                "bear",
                "cat",
                "character",
                "bow",
                "village",
                "river",
                "animation",
                "landscape",
            )
        )
        assert any(word in content for word in expected), second
        print(
            json.dumps(
                {
                    "case": name,
                    "past_tokens": first["usage"]["prompt_tokens"],
                    "usage": second["usage"],
                    "text": second["choices"][0]["message"]["content"],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        health = httpx.get(BASE_URL + "/health", timeout=10).json()
        assert health["status"] == "ok" and health["queue_len"] == 0
    print("All Omni media prefix API checks completed.")


if __name__ == "__main__":
    main()
