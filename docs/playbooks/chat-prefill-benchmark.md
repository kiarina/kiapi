# Measuring chat prefill chunks

Use `scripts/capabilities/measure_chat_prefill.py` to compare Qwen3.8 chunk
sizes without changing the server's generation defaults. It runs the actual
kiapi handler with the pinned image-prefix APC engine and temporarily overrides
only `prefill_step_size` inside the measurement process.

## Conditions

- Use an isolated checkout and environment. Keep the model, engine revision,
  quantization, APC settings, and input identical between chunk sizes.
- Stop the kiapi service after confirming its queue is empty. Do not run other
  GPU workloads during measurement. Restart the service when finished, including
  after a failed measurement.
- The script loads the model once and runs a short warmup. Before each cold
  request it clears APC and MLX's allocation cache and resets peak-memory stats.
  Model loading is excluded; request preprocessing and cache checkpoint work are
  included in `first_token_s`.
- `first_token_s` measures the first engine token, not the first nonempty SSE
  content. Text cases generate one token; image checks generate up to 16 tokens
  to verify colors. Do not compare their total elapsed times as prefill times.
- Each text case uses a deterministic repeated-text input. Its requested token
  count excludes the appended question and chat template; use `usage` for the
  actual count. This is a controlled benchmark, not a quality evaluation or a
  guarantee for every conversation.
- Repeat each case at least twice. Text repeats reverse chunk-size order to
  expose drift. Use separate tables for different inputs and APC budgets.

```sh
uv run python scripts/capabilities/measure_chat_prefill.py \
  --steps 512 1024 2048 4096 8192 --tokens 4096 16384 --repeats 2 \
  --output .verify/prefill/sweep.json

uv run python scripts/capabilities/measure_chat_prefill.py \
  --steps 512 2048 --image-checks --repeats 2 \
  --output .verify/prefill/images.json
```

`KIAPI_CHAT_APC_MEMORY_MAX_GB` controls the benchmark's APC budget. The script
uses capability settings directly and does not load the service's YAML config.

The JSON records first-token time, engine-reported prompt throughput, total
MLX peak bytes (including model weights), cache resident bytes, cached tokens,
and the actual prefill chunk-length histogram. APC checkpoint boundaries can
shorten a chunk even when a larger step is requested. The checkpoint interval
is deliberately not changed.

Image checks cover a long text prefix plus an image, exact replay, a second
image appended to history, and replacement of the first image. They require
prefix hits and verify ordered colors against a cold request. Replacement may
reuse an earlier text-only checkpoint, so `cached_tokens > 0` alone does not
mean stale image state was used.

## Initial sweep (2026-09-19, incomplete)

[Raw measurements](chat-prefill-benchmark/2026-09-19-initial-sweep.json) were
collected on a Mac Studio M4 Max with 128 GB, macOS 26.6.2, MLX 0.32.2,
kiapi `5b5ab85`, and mlx-vlm fork `3c5bd17`. The APC budget was 4 GiB.
The 4,114-token cases completed twice. The 16,402-token sweep was interrupted
when another GPU application started; its second 2048-token-step result is
contaminated. No production default was changed. See the active
[task](../../tasks/chat-prefill-chunk-tuning.md) for remaining validation.
