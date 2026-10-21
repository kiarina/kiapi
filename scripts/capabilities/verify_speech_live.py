"""Verify a running server: HTTP speech and live cloning (GPU, not a unit test)."""

import argparse
import asyncio
import json
import os
import wave
from pathlib import Path

import httpx
from websockets.asyncio.client import connect


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--voice", required=True)
    parser.add_argument(
        "--output", type=Path, default=Path(".verify/kiapi/speech-live")
    )
    args = parser.parse_args()
    token = os.environ.get("KIAPI_AUTH_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = (
        args.base_url.replace("http://", "ws://").replace("https://", "wss://")
        + "/v1/audio/speech/stream"
    )
    args.output.mkdir(parents=True, exist_ok=True)
    text = "こんにちは。今日は声のクローンで、日本語の通話を試しています。文章を少しずつ送りながら、音声を受け取ります。"
    async with httpx.AsyncClient(timeout=180) as client:
        result = await client.post(
            args.base_url + "/v1/audio/speech",
            headers=headers,
            json={
                "voice": args.voice,
                "input": text,
                "language": "ja",
                "response_format": "wav",
            },
        )
        result.raise_for_status()
        assert result.content[:4] == b"RIFF"
        (args.output / "http.wav").write_bytes(result.content)
    async with connect(url, additional_headers=headers, open_timeout=30) as socket:
        await socket.send(
            json.dumps(
                {"type": "start", "voice": args.voice, "language": "ja", "seed": 42}
            )
        )

        async def producer() -> None:
            for char in text:
                await socket.send(json.dumps({"type": "text.append", "text": char}))
                await asyncio.sleep(0.04)
            await socket.send(json.dumps({"type": "text.done"}))

        sending = asyncio.create_task(producer())
        pcm = bytearray()
        events = []
        async for item in socket:
            if isinstance(item, bytes):
                pcm.extend(item)
            else:
                event = json.loads(item)
                events.append(event)
                assert event["type"] != "error", event
        await sending
        assert pcm and events[-1]["type"] == "done", events
        with wave.open(str(args.output / "live.wav"), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24000)
            wav.writeframes(pcm)
        (args.output / "events.json").write_text(
            json.dumps(events, ensure_ascii=False, indent=2)
        )
    for mode in ("cancel", "disconnect"):
        async with connect(url, additional_headers=headers) as socket:
            await socket.send(
                json.dumps({"type": "start", "voice": args.voice, "language": "ja"})
            )
            while json.loads(await socket.recv())["type"] != "ready":
                pass
            await socket.send(json.dumps({"type": "text.append", "text": "あ"}))
            if mode == "cancel":
                await socket.send(json.dumps({"type": "cancel"}))
                assert json.loads(await socket.recv())["type"] == "canceled"
    # A following request proves cancellation released the worker/input wait.
    async with connect(url, additional_headers=headers) as socket:
        await socket.send(json.dumps({"type": "start", "voice": args.voice}))
        await socket.send(json.dumps({"type": "text.append", "text": "確認です。"}))
        await socket.send(json.dumps({"type": "text.done"}))
        terminal = None
        async for item in socket:
            if isinstance(item, str):
                terminal = json.loads(item)
                assert terminal["type"] != "error", terminal
        assert terminal and terminal["type"] == "done"
    print(f"Passed; listen to {args.output / 'live.wav'}")


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=600))
