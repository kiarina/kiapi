"""Measure Qwen3.8 prefill chunks with an idle GPU and the kiapi service stopped."""

import argparse
import base64
import functools
import gc
import hashlib
import importlib.metadata
import inspect
import io
import json
import platform
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import Any

from kiapi.capabilities.chat._models import qwen3_5
from kiapi.capabilities.chat._views.chat_params import ChatParams
from kiapi.core.model import ModelSpec


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--steps", nargs="+", type=int, default=[512, 1024, 2048, 4096, 8192]
    )
    parser.add_argument("--tokens", nargs="+", type=int, default=[4096, 16384])
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--image-checks", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if min(*args.steps, *args.tokens, args.repeats) < 1:
        parser.error("steps, tokens, and repeats must be positive")

    import mlx.core as mx
    import mlx_vlm

    spec = ModelSpec(
        name="qwen3.8-27b",
        family="chat",
        domain="chat",
        repo="mlx-community/Qwen3.8-27B-4bit",
        module=qwen3_5,
        weight_gb=15,
        peak_headroom_gb=20,
        framework="mlx",
    )
    payload = qwen3_5.load(spec)
    manager = payload.apc_manager
    assert manager is not None
    tokenizer = payload.processor.tokenizer
    original_stream = mlx_vlm.stream_generate
    assert "apc_image_prefix" in inspect.signature(original_stream).parameters, (
        "Use the pinned engine with image prefix support"
    )
    language_type = type(payload.model.language_model)
    original_call = language_type.__call__
    chunks: list[int] = []
    metrics: dict[str, Any] = {}
    step = 2048
    started = 0.0

    @functools.wraps(original_call)
    def observed_call(self: Any, *a: Any, **kw: Any) -> Any:
        if "n_to_process" in kw:
            chunks.append(int(kw["n_to_process"]))
        return original_call(self, *a, **kw)

    @functools.wraps(original_stream)
    def measured_stream(*a: Any, **kw: Any) -> Any:
        kw["prefill_step_size"] = step
        metrics["image_prefix_enabled"] = kw.get("apc_image_prefix", False)
        for result in original_stream(*a, **kw):
            metrics.setdefault("first_token_s", time.perf_counter() - started)
            metrics["prompt_tps"] = result.prompt_tps
            yield result

    language_type.__call__ = observed_call
    mlx_vlm.stream_generate = measured_stream
    output: dict[str, Any] = {
        "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "macos": platform.mac_ver()[0],
        "device": mx.device_info(),
        "versions": {p: importlib.metadata.version(p) for p in ("mlx", "mlx-vlm")},
        "engine_source": json.loads(
            importlib.metadata.distribution("mlx-vlm").read_text("direct_url.json")
            or "null"
        ),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "arguments": {
            k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()
        },
        "apc_checkpoint_interval_tokens": manager.checkpoint_interval_tokens,
        "apc_memory_max_bytes": manager.memory_max_bytes,
        "rows": [],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def request(
        text: str | list[dict[str, Any]],
        label: str,
        repeat: int,
        *,
        cold: bool = True,
        max_tokens: int = 1,
    ) -> dict[str, Any]:
        nonlocal started
        if cold:
            manager.clear()
        gc.collect()
        mx.clear_cache()
        mx.reset_peak_memory()
        chunks.clear()
        metrics.clear()
        params = ChatParams(
            model=spec.name,
            messages=[{"role": "user", "content": text}]
            if isinstance(text, str)
            else text,
            temperature=0,
            max_tokens=max_tokens,
            seed=42,
            tools=None,
            tool_choice=None,
            parallel_tool_calls=True,
            top_p=1,
            fps=1,
            use_audio_in_video=False,
            chat_template_kwargs=None,
            stream=True,
        )
        started = time.perf_counter()
        response = qwen3_5.run(payload, params)
        row = {
            "case": label,
            "repeat": repeat,
            "step": step,
            "cold": cold,
            **metrics,
            "elapsed_s": time.perf_counter() - started,
            "usage": response["usage"],
            "peak_bytes": mx.get_peak_memory(),
            "resident_bytes": manager.resident_bytes(),
            "chunk_histogram": dict(Counter(chunks)),
            "text": response["choices"][0]["message"]["content"],
        }
        if cold:
            assert row["usage"]["prompt_tokens_details"]["cached_tokens"] == 0
        output["rows"].append(row)
        args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps(row, ensure_ascii=False), flush=True)
        return row

    try:
        request("Say hello.", "warmup", 0)
        for count in [] if args.image_checks else args.tokens:
            filler = tokenizer.encode("A river flows through the valley. " * count)
            prompt = tokenizer.decode(filler[:count]) + "\nReply with OK only."
            for repeat in range(args.repeats):
                for chunk_size in (
                    args.steps if repeat % 2 == 0 else reversed(args.steps)
                ):
                    step = chunk_size
                    request(prompt, f"text_{count}", repeat + 1)
        if args.image_checks:
            from PIL import Image

            def image_part(color: str) -> dict[str, Any]:
                buffer = io.BytesIO()
                Image.new("RGB", (320, 240), color).save(buffer, format="PNG")
                data = base64.b64encode(buffer.getvalue()).decode()
                return {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{data}"},
                }

            filler = tokenizer.decode(
                tokenizer.encode("Background context. " * 4096)[:4096]
            )
            question = {
                "type": "text",
                "text": "List the solid colors of all images in order. Reply only with English color names, separated by commas.",
            }
            base: list[dict[str, Any]] = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": filler},
                        image_part("red"),
                        question,
                    ],
                }
            ]
            extended: list[dict[str, Any]] = [
                *base,
                {"role": "assistant", "content": "Image received."},
                {"role": "user", "content": [image_part("blue"), question]},
            ]
            changed: list[dict[str, Any]] = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": filler},
                        image_part("green"),
                        question,
                    ],
                },
                *extended[1:],
            ]
            for chunk_size in args.steps:
                step = chunk_size
                for repeat in range(args.repeats):
                    request(base, "image_base", repeat + 1, max_tokens=16)
                    warm = request(
                        base, "image_warm", repeat + 1, cold=False, max_tokens=16
                    )
                    assert warm["usage"]["prompt_tokens_details"]["cached_tokens"] > 0
                    assert (
                        "red" in warm["text"].lower()
                        and "blue" not in warm["text"].lower()
                    ), warm
                    hit = request(
                        extended,
                        "image_append_hit",
                        repeat + 1,
                        cold=False,
                        max_tokens=16,
                    )
                    assert hit["usage"]["prompt_tokens_details"]["cached_tokens"] > 0
                    altered = request(
                        changed, "image_changed", repeat + 1, cold=False, max_tokens=16
                    )
                    cold = request(
                        extended, "image_append_cold", repeat + 1, max_tokens=16
                    )
                    for row in (hit, cold):
                        answer = row["text"].lower()
                        assert (
                            "red" in answer
                            and "blue" in answer
                            and answer.index("red") < answer.index("blue")
                        ), row
                    assert (
                        "green" in altered["text"].lower()
                        and "blue" in altered["text"].lower()
                        and "red" not in altered["text"].lower()
                        and altered["text"].lower().index("green")
                        < altered["text"].lower().index("blue")
                    ), altered
    finally:
        mlx_vlm.stream_generate = original_stream
        language_type.__call__ = original_call
        qwen3_5.release(payload)


if __name__ == "__main__":
    main()
