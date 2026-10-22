# Live Qwen3-TTS voice cloning

This package is the extraction boundary for an upstream mlx-audio proposal. It
imports no kiapi API, voice store, jobs, model registry, or settings. Importing
`TextSource` does not import MLX. Import and execute generation on the model's
worker thread.

```python
source = TextSource(max_chars=4096, idle_timeout=30)
# A producer may call push/close/cancel before the model is loaded.
source.push("こんにちは。")
source.close()
# On the model worker:
source.bind(model.tokenizer)
prompt = prepare_clone(model, reference_audio, reference_transcript, "japanese")
for audio in generate_live(model, prompt, source):
    consume(audio)  # float PCM; transport/encoding belongs to the caller
```

The tokenizer's last regex pre-token remains uncommitted until more input or
explicit close. No spaces are inserted into Japanese. A committed prefix must
never change. Causal ICL starts after enough target tokens cover the reference
codec prefix (`prompt.required_prefix_tokens`), or after close. EOS and padding
are introduced only after close. Input waits preserve talker, code predictor,
and decoder state; cancel wakes a waiting consumer. Repetition penalty is 1.05
across all generated tokens. The decoder is primed with reference codes.

`prepare_clone` accepts upstream mlx-audio's original prompt builder. The kiapi
compatibility patch preserves that method as `_prepare_live_clone`; full-input
HTTP synthesis continues using its existing patched method. This hook belongs
to kiapi integration and can be removed when integrated upstream.

Prepared prompts are immutable and reusable on the same worker and model.
kiapi owns a four-entry LRU keyed by voice ID, reference audio SHA-256,
reference transcript and language. Model eviction releases that cache.

Long references increase the amount of target text required before first audio.
Cancellation is cooperative between model steps; a currently running model
prefill/load cannot be interrupted inside MLX.

## Prepared explicit reference boundary

`prepare_reference(model, prompt)` prefills reference text plus text EOS over
all reference codes, appends codec EOS and a fresh copy of the
role/language/speaker prefix, then primes the decoder. It returns a
`PreparedReference` snapshot. `fork_reference` copies talker KV arrays and the
decoder's transformer/conv/overlap state for one independent generation.
`generate_prepared` streams target text, delaying codec EOS until input is
closed and the target text EOS row has been consumed. No target text or sampled
audio is invented during preparation. All preparation/fork/generation and
snapshot release belong on the model worker; snapshots must never pin an
evicted model from a transport thread.
