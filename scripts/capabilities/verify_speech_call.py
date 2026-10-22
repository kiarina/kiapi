"""GPU verification of prepared, independent utterances on one WebSocket."""

import argparse
import asyncio
import hashlib
import json
import os
import struct
import time
import wave
from pathlib import Path

import httpx
from websockets.asyncio.client import connect


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8500")
    parser.add_argument("--voice", required=True)
    parser.add_argument(
        "--output", type=Path, default=Path(".verify/kiapi/speech-call")
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("KIAPI_AUTH_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = (
        args.base_url.replace("http://", "ws://").replace("https://", "wss://")
        + "/v1/audio/speech/stream"
    )
    report: dict = {"turns": []}
    async with connect(url, additional_headers=headers) as ws:
        start = time.perf_counter()
        await ws.send(
            json.dumps(
                {
                    "type": "start",
                    "protocol": 2,
                    "voice": args.voice,
                    "language": "ja",
                    "seed": 42,
                }
            )
        )
        assert json.loads(await ws.recv())["protocol"] == 2
        ready = json.loads(await ws.recv())
        assert ready["type"] == "ready"
        report["ready_s"] = time.perf_counter() - start
        async with httpx.AsyncClient() as client:
            response = await client.get(args.base_url + "/health", headers=headers)
            response.raise_for_status()
            report["idle_health"] = response.json()

        async def turn(identifier: int) -> bytes:
            begin = time.perf_counter()
            first = None
            pcm = bytearray()
            await ws.send(
                json.dumps({"type": "utterance.start", "utterance_id": identifier})
            )
            for text in ["こんにちは。", "今日は日本語の声で通話を試しています。"]:
                await ws.send(
                    json.dumps(
                        {
                            "type": "text.append",
                            "utterance_id": identifier,
                            "text": text,
                        }
                    )
                )
                await asyncio.sleep(0.1)
            await ws.send(json.dumps({"type": "text.done", "utterance_id": identifier}))
            while True:
                item = await ws.recv()
                if isinstance(item, bytes):
                    assert struct.unpack("<I", item[:4])[0] == identifier
                    if first is None:
                        first = time.perf_counter() - begin
                    pcm.extend(item[4:])
                else:
                    event = json.loads(item)
                    assert event["type"] == "utterance.done", event
                    assert event["utterance_id"] == identifier
                    break
            assert pcm
            row = {
                "id": identifier,
                "first_pcm_s": first,
                "samples": len(pcm) // 2,
                "sha256": hashlib.sha256(pcm).hexdigest(),
            }
            report["turns"].append(row)
            with wave.open(str(args.output / f"turn-{identifier}.wav"), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(24000)
                output.writeframes(pcm)
            print(row, flush=True)
            return bytes(pcm)

        first = await turn(1)
        await ws.send(json.dumps({"type": "utterance.start", "utterance_id": 2}))
        await ws.send(
            json.dumps(
                {
                    "type": "text.append",
                    "utterance_id": 2,
                    "text": "これは途中で止めます。",
                }
            )
        )
        while True:
            item = await ws.recv()
            if isinstance(item, bytes):
                assert struct.unpack("<I", item[:4])[0] == 2
                break
            raise AssertionError(item)
        before = time.perf_counter()
        await ws.send(json.dumps({"type": "cancel", "utterance_id": 2}))
        while True:
            item = await ws.recv()
            if isinstance(item, str):
                event = json.loads(item)
                assert event == {"type": "utterance.canceled", "utterance_id": 2}, event
                break
        report["cancel_ack_s"] = time.perf_counter() - before
        await ws.send(
            json.dumps({"type": "text.append", "utterance_id": 2, "text": "古い文章"})
        )
        after_cancel = await turn(3)
        repeated = await turn(4)
        assert first == after_cancel == repeated, (
            "Prepared state contaminated by a preceding utterance"
        )
        await ws.send(json.dumps({"type": "utterance.start", "utterance_id": 5}))
        await ws.send(json.dumps({"type": "cancel", "utterance_id": 5}))
        assert json.loads(await ws.recv()) == {
            "type": "utterance.canceled",
            "utterance_id": 5,
        }
        await ws.send(json.dumps({"type": "session.close"}))
    report["independent_pcm_equal"] = True
    (args.output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)
    )
    print("Passed prepared multi-turn/cancel/next-turn", flush=True)


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), 600))
