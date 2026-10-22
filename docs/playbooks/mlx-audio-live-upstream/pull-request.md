## Context

Incremental text can arrive more slowly than a voice-cloning model consumes it. Pausing an ongoing autoregressive generation for each missing token can leave gaps in streaming audio. Applications also need to prepare the full voice reference before the first target text arrives and reuse that work after an interruption.

Related to #961. This proposes a narrower, **experimental segmented Base-cloning API**: it completes short received spans and starts each from the same prepared reference. It does not implement one continuously evolving context across an entire conversation.

## Description

Add `Model.prepare_live_clone(reference, transcript, lang_code)` and `Model.generate_live(source, prepared)`, with a transport-neutral `TextSource` supporting `push`/`feed`, `close`, and `cancel`.

Preparation retains the full reference audio, adds explicit reference-text/codec endings and a fresh role/language/speaker prefix, prefills the talker, and primes the streaming decoder. This conditioning layout is experimental and opt-in, not an official Qwen live-input protocol. Each short span forks the prepared state; it does not condition on preceding generated target speech.

Producers append text without MLX operations. One model worker handles preparation, inference and snapshot release. Generation yields existing `GenerationResult` chunks immediately and one empty terminal result after successful input close and all spans finish. Cancellation, timeout and errors do not produce a success marker. Reusing the snapshot with a new source supports subsequent utterances.

## Changes in the codebase

- Isolated `live.py` and `live_text.py`: reference snapshots, model/thread ownership, bounded text input, CJK/Latin span boundaries, cooperative cancellation and cleanup.
- Additive Base model methods and exports. One optional cancellation callback in the existing code-predictor helper defaults to no behavior change.
- CPU tests for ownership, input boundaries, cancellation, cleanup, limits and chunk accounting.
- Document the experimental scope, threading contract and limitations; add a terminal-to-WAV example without playback.

Existing `generate()`, CustomVoice and VoiceDesign behavior stays unchanged. WebSockets, playback queues, voice registration, application workers and cache eviction remain outside the library.

## Changes outside the codebase

None required. No reference recordings, private transcripts, model weights or generated audio are added.

## Additional information

Validation is against `7cc680b2bea1e8ef34b1a78ee4ff389953aebe40` on a MacBook Pro M1 Max 64GB, Python 3.12.10, MLX 0.32.4, using `mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16` revision `a6eb4f68e4b056f1215157bb696209bc82a6db48` and one full 10.678-second private reference.

- Focused live and existing `test_qwen3_tts.py` tests: 60 passed, including 9 passing subtests. Black 26.3.1 and isort 5.13.2 checks pass for changed Python files.
- Additional `test_models.py -k "Qwen3TTS and not GenerateICL"`: 36 passed. Including the existing `GenerateICL` class crashes natively in `mx.eval` (exit 139) on both the patch and clean base; the cause is not established and unrelated fixtures were not changed. These runs are not a full passing upstream suite.
- Actual model: exact reference-code and original-prefix equality, cancellation while waiting/after PCM, generator-close cleanup, repeated snapshot output equality, and correct terminal/sample accounting passed.
- Existing `generate()` output is byte-identical with a fixed seed on clean base, patched checkout, and after live generation.
- Character-fed Japanese: first PCM 2.091s, text close 5.781s. English: first PCM 1.992s, text close 7.455s. These are single controlled runs, not call latency benchmarks; preparation (0.566s) and application playout buffering are excluded.
- Fixed Whisper diagnostics matched streamed Japanese and English targets after normalization (CER/WER 0). A separate short Japanese example had CER 0.087; ASR and synthesis errors have not been separated. ECAPA cosine against the reference was 0.731–0.770 across the three examples, a diagnostic rather than a perceptual similarity score.

Limitations: one reference/seed/model; no listening evaluation of this patch, 0.6B/quantized coverage or broad quality claim. Span-local prosody can change with input batching, mixed CJK caps can split Latin words, and long input starvation can still exhaust an application buffer. All model operations must remain serialized on one worker; ordinary inference must not be interleaved with live inference. Full upstream CI remains to be run. The existing aggregate GenerateICL crash above remains a validation limitation.

The [downstream experiment](https://github.com/kiarina/labs/tree/main/2026/10/22/qwen3-tts-live-audio-decoupling) motivated the design; its results are separate from the checks above.

## Checklist

- [x] Tests added/updated
- [x] Documentation updated
- [x] Issue referenced (Related to #961; not closing its broader request)
