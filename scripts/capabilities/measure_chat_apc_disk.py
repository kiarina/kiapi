"""Evaluate upstream APC disk storage using synthetic text and temporary files."""

import json
import tempfile
import time
from pathlib import Path
from typing import Any

from kiapi.capabilities.chat._models import qwen3_5
from kiapi.capabilities.chat._views.chat_params import ChatParams
from kiapi.core.model import ModelSpec


def main() -> None:
    from mlx_vlm.apc import APCManager, DiskBlockStore, apc_disk_namespace

    repo = "mlx-community/Qwen3.8-27B-4bit"
    spec = ModelSpec(
        name="qwen3.8-27b",
        family="chat",
        domain="chat",
        repo=repo,
        module=qwen3_5,
        weight_gb=16,
        peak_headroom_gb=8,
        framework="mlx",
    )
    payload = qwen3_5.load(spec)
    params = ChatParams(
        model=spec.name,
        messages=[
            {
                "role": "user",
                "content": "The secret word is ORCHID. "
                + "Background context. " * 1000
                + " Reply with the secret word only.",
            }
        ],
        temperature=0,
        max_tokens=16,
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
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="kiapi-apc-disk-") as tmp:
        root = Path(tmp)
        namespace = apc_disk_namespace(repo)

        def manager(cap: int = 1024**3) -> Any:
            return APCManager(
                disk=DiskBlockStore(root, namespace, max_bytes=cap),
                overrides={"memory_max_gb": 4},
            )

        def run(label: str) -> None:
            first: list[float] = []
            start = time.monotonic()

            def emit(chunk: dict[str, Any]) -> None:
                if not first and chunk.get("choices", [{}])[0].get("delta", {}).get(
                    "content"
                ):
                    first.append(time.monotonic() - start)

            response = qwen3_5.run(payload, params, emit=emit)
            row = {
                "case": label,
                "ttft_s": first[0],
                "seconds": time.monotonic() - start,
                "response": response,
                "stats": payload.apc_manager.stats_snapshot(),
            }
            rows.append(row)
            print(json.dumps(row), flush=True)
            assert "ORCHID" in response["choices"][0]["message"]["content"]

        # Warm up model kernels with memory-only APC first.
        run("kernel_warmup")
        payload.apc_manager.clear()
        run("memory_cold")
        run("memory_warm")
        qwen3_5.release(payload)
        payload.apc_manager = manager()
        run("disk_enabled_cold")
        run("disk_enabled_memory_warm")
        qwen3_5.release(payload)  # flush writer and drop RAM snapshots
        files = sorted(root.rglob("*.safetensors"))
        size = sum(p.stat().st_size for p in files)
        headers = []
        for path in files:
            with path.open("rb") as source:
                n = int.from_bytes(source.read(8), "little")
                headers.append(json.loads(source.read(n)).get("__metadata__", {}))
        print(
            json.dumps(
                {
                    "disk_bytes": size,
                    "metadata_keys": [list(h) for h in headers],
                    "plaintext_tokens": any("token" in k for h in headers for k in h),
                }
            ),
            flush=True,
        )
        payload.apc_manager = manager()
        run("disk_reopen")
        assert (
            rows[-1]["response"]["usage"]["prompt_tokens_details"]["cached_tokens"] > 0
        )
        qwen3_5.release(payload)
        for path in root.rglob("*.safetensors"):
            path.write_bytes(b"broken")
        payload.apc_manager = manager()
        run("corrupt_disk_fallback")
        assert (
            rows[-1]["response"]["usage"]["prompt_tokens_details"]["cached_tokens"] == 0
        )
        qwen3_5.release(payload)
        for path in root.rglob("*.safetensors"):
            path.unlink()
        payload.apc_manager = manager(cap=1024)
        run("tiny_disk_cap")
        qwen3_5.release(payload)
        final_size = sum(p.stat().st_size for p in root.rglob("*.safetensors"))
        print(
            json.dumps({"tiny_cap": 1024, "final_disk_bytes": final_size}), flush=True
        )
        assert final_size <= 1024

        malformed = (
            root / "malformed" / "exact_00000000000000000000000000000000.safetensors"
        )
        malformed.parent.mkdir()
        header = b"[]"
        malformed.write_bytes(len(header).to_bytes(8, "little") + header)
        try:
            bad_store = DiskBlockStore(root, "malformed", max_bytes=1024)
        except (TypeError, AttributeError) as exc:
            print(
                json.dumps({"wrong_type_header_fallback": False, "error": str(exc)}),
                flush=True,
            )
        else:
            bad_store.close()
            print(json.dumps({"wrong_type_header_fallback": True}), flush=True)


if __name__ == "__main__":
    main()
