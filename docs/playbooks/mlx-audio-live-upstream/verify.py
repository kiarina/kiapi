"""Opt-in actual-model checks of the proposal checkout; no playback or service use."""

import argparse
import hashlib
import importlib.metadata
import json
import sys
import threading
import time
import wave
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--transcript-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--legacy-only", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(args.checkout.resolve()))
    import mlx.core as mx
    import numpy as np
    from huggingface_hub import snapshot_download
    from mlx_audio.tts.utils import load_model
    from mlx_audio.utils import load_audio

    model_id = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16"
    revision = "a6eb4f68e4b056f1215157bb696209bc82a6db48"
    model = load_model(snapshot_download(model_id, revision=revision))
    reference = load_audio(str(args.reference), sample_rate=24000)
    transcript = args.transcript_file.read_text().strip()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {
        "model": model_id,
        "revision": revision,
        "reference_sha256": hashlib.sha256(args.reference.read_bytes()).hexdigest(),
        "reference_samples": int(reference.size),
        "versions": {
            n: importlib.metadata.version(n) for n in ["mlx", "transformers", "numpy"]
        },
        "cases": [],
    }
    target = "こんにちは。今日は日本語の声で通話を試しています。"

    def save(name, chunks, started, final_required=False):
        audio, final, frames, first = [], [], 0, None
        for chunk in chunks:
            data = np.asarray(chunk.audio.astype(mx.float32))
            assert len(data) == chunk.samples and np.isfinite(data).all()
            if chunk.is_final_chunk:
                final.append(chunk)
            if len(data):
                first = first or time.perf_counter() - started
                audio.append(data)
            frames += chunk.token_count
        pcm = np.concatenate(audio) if audio else np.zeros(0, dtype=np.float32)
        if final_required:
            assert (
                len(final) == 1 and final[0].samples == 0 and final[0].token_count == 0
            )
            assert final[0].audio_samples["samples"] == len(pcm)
            assert final[0].audio_samples["tokens"] == frames
        pcm16 = (np.clip(pcm, -1, 1) * 32767).astype("<i2")
        with wave.open(str(args.output / (name + ".wav")), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(24000)
            f.writeframes(pcm16.tobytes())
        row = {
            "name": name,
            "samples": len(pcm),
            "frames": frames,
            "first_pcm_s": first,
            "total_s": time.perf_counter() - started,
            "float_pcm_sha256": hashlib.sha256(pcm.tobytes()).hexdigest(),
            "pcm16_sha256": hashlib.sha256(pcm16.tobytes()).hexdigest(),
            "final_count": len(final),
        }
        report["cases"].append(row)
        return row

    def legacy(name):
        mx.random.seed(42)
        return save(
            name,
            model.generate(
                target,
                ref_audio=reference,
                ref_text=transcript,
                lang_code="japanese",
                stream=True,
                streaming_interval=0.32,
                temperature=0.9,
                top_k=50,
                top_p=1.0,
                repetition_penalty=1.05,
                max_tokens=500,
                verbose=False,
            ),
            time.perf_counter(),
        )

    baseline = legacy("legacy-before")
    if not args.legacy_only:
        from mlx_audio.tts.models.qwen3_tts import TextSource

        began = time.perf_counter()
        prepared = model.prepare_live_clone(reference, transcript, lang_code="japanese")
        report["preparation_s"] = time.perf_counter() - began
        original, _, _, codes = model._prepare_icl_generation_inputs(
            "", reference, transcript, "japanese"
        )
        ids = model.tokenizer.encode(
            f"<|im_start|>assistant\n{transcript}<|im_end|>\n"
        )[3:-2]
        prefix = original[:, : original.shape[1] - (len(ids) + 1 + codes.shape[2] + 1)]
        delta = np.asarray((prefix - prepared._snapshot["prefix"]).astype(mx.float32))
        report["prefix_max_abs_difference"] = float(np.max(np.abs(delta)))
        report["reference_codes_equal"] = bool(
            mx.array_equal(codes, prepared._snapshot["reference_codes"])
        )
        assert (
            report["prefix_max_abs_difference"] == 0 and report["reference_codes_equal"]
        )

        def full(name):
            source = TextSource()
            source.push(target)
            source.close()
            return save(
                name,
                model.generate_live(source, prepared, seed=42),
                time.perf_counter(),
                True,
            )

        first = full("live-full")
        source = TextSource()
        source.push(target)
        source.close()
        generator = model.generate_live(source, prepared, seed=42)
        assert next(generator).samples > 0
        source.cancel()
        try:
            next(generator)
            raise AssertionError("cancel did not stop generation")
        except InterruptedError:
            report["cancel_after_pcm"] = True
        finally:
            generator.close()
        after = full("live-after-cancel")
        assert first["float_pcm_sha256"] == after["float_pcm_sha256"]

        source = TextSource()
        source.push(target)
        source.close()
        generator = model.generate_live(source, prepared, seed=42)
        next(generator)
        generator.close()
        repeated = full("live-after-generator-close")
        assert first["float_pcm_sha256"] == repeated["float_pcm_sha256"]

        source = TextSource()
        stopper = threading.Timer(0.05, source.cancel)
        stopper.start()
        began = time.perf_counter()
        try:
            list(model.generate_live(source, prepared))
            raise AssertionError("empty input cancellation failed")
        except InterruptedError:
            report["cancel_wait_s"] = time.perf_counter() - began
        finally:
            stopper.join()
        assert report["cancel_wait_s"] < 1

        for label, text, delay in [
            (
                "ja",
                "うん、今日はいい天気ですね。少し散歩してから、駅前のカフェでコーヒーを飲みませんか？",
                0.13,
            ),
            (
                "en",
                "Tokyo is a busy city with quiet gardens and many small cafes. We can take a short walk and have some tea later.",
                0.06,
            ),
        ]:
            source = TextSource()
            events = []
            errors = []
            began = time.perf_counter()

            def feed():
                try:
                    for ch in text:
                        source.push(ch)
                        events.append(
                            {"event": "text", "t": time.perf_counter() - began}
                        )
                        time.sleep(delay)
                    events.append(
                        {"event": "text.done", "t": time.perf_counter() - began}
                    )
                    source.close()
                except Exception as exc:
                    errors.append(type(exc).__name__)
                    source.cancel()

            producer = threading.Thread(target=feed)
            producer.start()
            try:
                row = save(
                    "live-stream-" + label,
                    model.generate_live(source, prepared, seed=42),
                    began,
                    True,
                )
            finally:
                source.cancel()
                producer.join(timeout=5)
            assert not errors and not producer.is_alive()
            row["text_done_s"] = next(
                e["t"] for e in events if e["event"] == "text.done"
            )
            assert row["first_pcm_s"] < row["text_done_s"]
        prepared.release()
        final_legacy = legacy("legacy-after")
        assert baseline["float_pcm_sha256"] == final_legacy["float_pcm_sha256"]
        report["prepared_reuse_equal"] = True
        report["legacy_unchanged_within_checkout"] = True
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
