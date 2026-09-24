"""GPU APC checks. Run with the kiapi service stopped, one model at a time."""

import argparse
import base64
import gc
import inspect
import json
import time
from pathlib import Path
from typing import Any

from kiapi.capabilities.chat._models import qwen3_5, qwen3_omni, qwen4_exp
from kiapi.capabilities.chat._views.chat_params import ChatParams
from kiapi.core.model import ModelSpec


def media_part(kind: str, path: Path, mime: str) -> dict[str, Any]:
    data = base64.b64encode(path.read_bytes()).decode()
    return {"type": f"{kind}_url", f"{kind}_url": {"url": f"data:{mime};base64,{data}"}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "model",
        choices=["qwen3-omni", "qwen3.6-27b", "qwen3.8-27b", "qwen3.8-flash-next"],
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import mlx.core as mx
    from mlx_vlm import stream_generate

    image_prefix_enabled = (
        args.model in qwen3_5.IMAGE_PREFIX_MODELS
        and "apc_image_prefix" in inspect.signature(stream_generate).parameters
    )

    handler = {"qwen3-omni": qwen3_omni, "qwen3.8-flash-next": qwen4_exp}.get(
        args.model, qwen3_5
    )
    repos = {
        "qwen3-omni": "Qwen3-Omni-30B-A3B-Instruct-4bit",
        "qwen3.6-27b": "Qwen3.6-27B-4bit",
        "qwen3.8-27b": "Qwen3.8-27B-4bit",
        "qwen3.8-flash-next": "Qwen3.8-Flash-Next-4bit",
    }
    spec = ModelSpec(
        name=args.model,
        family="chat",
        domain="chat",
        repo="mlx-community/" + repos[args.model],
        module=handler,
        weight_gb=20.3,
        peak_headroom_gb=20,
        framework="mlx",
    )
    assets = Path(__file__).resolve().parents[2] / "tests/assets"
    image = media_part("image", assets / "miineko.png", "image/png")
    audio = media_part("audio", assets / "song.wav", "audio/wav")
    video = media_part("video", assets / "pv.mp4", "video/mp4")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    payload = handler.load(spec)
    manager = payload.apc_manager
    assert manager is not None and manager.disk is None

    def request(
        label: str,
        state: str,
        messages: list[dict[str, Any]],
        *,
        fps: float = 1,
        use_audio: bool = False,
    ) -> dict[str, Any]:
        params = ChatParams(
            model=args.model,
            messages=messages,
            temperature=0,
            max_tokens=64,
            seed=42,
            tools=None,
            tool_choice=None,
            parallel_tool_calls=True,
            top_p=1,
            fps=fps,
            use_audio_in_video=use_audio,
            chat_template_kwargs=None,
            stream=True,
        )
        first: list[float] = []
        start = time.monotonic()

        def emit(chunk: dict[str, Any]) -> None:
            if not first and chunk.get("choices", [{}])[0].get("delta", {}).get(
                "content"
            ):
                first.append(time.monotonic() - start)

        result = handler.run(payload, params, emit=emit)
        row = {
            "model": args.model,
            "case": label,
            "state": state,
            "ttft_s": first[0] if first else None,
            "elapsed_s": time.monotonic() - start,
            "text": result["choices"][0]["message"]["content"],
            "usage": result["usage"],
            "resident_bytes": manager.resident_bytes(),
            "active_bytes": mx.get_active_memory(),
            "peak_bytes": mx.get_peak_memory(),
            "stats": manager.stats_snapshot(),
        }
        rows.append(row)
        args.output.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps(row, ensure_ascii=False), flush=True)
        assert row["text"] and first
        assert row["resident_bytes"] <= manager.memory_max_bytes
        return row

    def cached(row: dict[str, Any]) -> int:
        return int(row["usage"]["prompt_tokens_details"]["cached_tokens"])

    def messages(parts: list[dict[str, Any]], question: str) -> list[dict[str, Any]]:
        return [
            {"role": "user", "content": [*parts, {"type": "text", "text": question}]}
        ]

    # Prime kernels before timing cold versus warm requests.
    request("warmup", "uncached", messages([], "Say hello."))
    cases = [
        (
            "text",
            [],
            "The secret word is ORCHID. "
            + "Background context. " * 700
            + " Reply with the secret word only.",
        ),
        ("image", [image], "Describe the image in one short sentence."),
        (
            "long_image",
            [image] * 45,
            "Describe the repeated images in one short sentence.",
        ),
    ]
    if args.model == "qwen3-omni":
        cases += [
            ("audio", [audio], "Describe the sound in one short sentence."),
            ("video", [video], "Describe the video in one short sentence."),
            (
                "image_video",
                [image, video],
                "Describe the image and video in one short sentence.",
            ),
        ]
    for label, parts, question in cases:
        manager.clear()
        msgs = messages(parts, question)
        cold = request(label, "cold", msgs)
        assert cached(cold) == 0
        if label in {"long_image", "video", "image_video"}:
            assert cold["usage"]["prompt_tokens"] > 2048
        for repeat in range(3):
            warm = request(label, f"warm_{repeat + 1}", msgs)
            assert cached(warm) > 0, (label, "no warm hit")
            if label == "text":
                assert "ORCHID" in warm["text"] and "ORCHID" in cold["text"]
        continuation = [
            *msgs,
            {"role": "assistant", "content": cold["text"]},
            {
                "role": "user",
                "content": "Reply with the secret word only."
                if label == "text"
                else question,
            },
        ]
        partial = request(label, "partial", continuation)
        # Qwen3.6 removes the empty <think> prefill from historical assistant
        # turns. A short hybrid checkpoint can therefore legitimately miss.
        if args.model != "qwen3.6-27b" or label == "text":
            assert cached(partial) > 0
        manager.clear()
        partial_cold = request(label, "partial_cold", continuation)
        assert cached(partial_cold) == 0
        if parts:
            # The pinned Qwen3.8 path reuses text before new suffix images.
            # Other engines/models retain whole-request media invalidation.
            base = messages(
                [], "Remember the word ORCHID. " + "Background context. " * 100
            )
            request(label, "text_prefix_before_media", base)
            extended = [
                *base,
                {"role": "assistant", "content": "Understood."},
                *messages(parts, question),
            ]
            new_media = request(label, "new_media_suffix", extended)
            assert (
                (cached(new_media) > 0)
                if image_prefix_enabled
                else (cached(new_media) == 0)
            )
        if label in {"video", "image_video"}:
            manager.clear()
            request(label, "option_baseline", msgs)
            assert cached(request(label, "changed_fps", msgs, fps=0.5)) == 0
            assert (
                cached(request(label, "changed_audio_option", msgs, use_audio=True))
                == 0
            )

            assert (
                cached(
                    request(label, "changed_audio_option_warm", msgs, use_audio=True)
                )
                > 0
            )

    # Same processor/token layout but different media bytes must miss.
    import io

    from PIL import Image

    manager.clear()
    for color in ("red", "green"):
        buffer = io.BytesIO()
        Image.new("RGB", (96, 96), color).save(buffer, format="PNG")
        part = {
            "type": "image_url",
            "image_url": {
                "url": "data:image/png;base64,"
                + base64.b64encode(buffer.getvalue()).decode()
            },
        }
        msgs = messages([part], "Name the dominant color. Reply with one color word.")
        changed = request("changed_image", color, msgs)
        assert cached(changed) == 0 and color in changed["text"].lower()
        assert cached(request("changed_image", color + "_warm", msgs)) > 0

    manager.clear()
    assert manager.resident_bytes() == 0
    handler.release(payload)
    del payload, manager
    gc.collect()
    mx.clear_cache()
    print(json.dumps({"released_active_bytes": mx.get_active_memory()}), flush=True)
    payload = handler.load(spec)
    manager = payload.apc_manager
    assert manager.resident_bytes() == 0
    assert cached(request("reload", "cold", messages([], "Say hello."))) == 0
    handler.release(payload)


if __name__ == "__main__":
    main()
