# Qwen3-TTS live-clone upstream proposal

This directory owns a reviewable upstream patch proposal, not runtime code used by kiapi. The adopted application remains on its current implementation while this proposal is reviewed. No upstream PR has been submitted.

## Review recommendation

The [value assessment](assessment.md) recommends narrowing the proposal to reusable preparation and generation of committed spans, and comparing against warmed existing generation before submission. The current patch and draft are retained for review; this recommendation has not yet changed their scope.

## Scope

| Belongs in the model library | Remains in the application |
| --- | --- |
| Base-only reference preparation before target text | Voice registration, IDs, storage, authorization |
| Independent forks of prepared talker/decoder state | Model-worker scheduling, eviction, bounded LRU |
| Transport-neutral text input and segmented PCM generation | WebSocket framing, utterance IDs, HTTP endpoints |
| Cooperative cancellation and generator cleanup | Playback queue, one-second startup buffer, AEC |
| Model/thread ownership checks, tests and example | GPT transcript routing, call UI and telemetry |

The proposed reference boundary is experimental, opt-in conditioning. Each short span starts an independent generation with the same reference; it does not preserve one evolving target context or promise continuous prosody. Do not present this as a complete implementation of [#961](https://github.com/Blaizzy/mlx-audio/issues/961).

## Upstream inspection

Base: `7cc680b2bea1e8ef34b1a78ee4ff389953aebe40`, inspected 2026-10-22, reported version 0.6.1.

- [#1036](https://github.com/Blaizzy/mlx-audio/pull/1036) is merged. Its CustomVoice/VoiceDesign full-text conditioning stays unchanged.
- [#946](https://github.com/Blaizzy/mlx-audio/pull/946) is closed without merge. It proposed reference priming for existing ICL streaming; this proposal must not silently bundle a fix to that existing generation path.
- [#961](https://github.com/Blaizzy/mlx-audio/issues/961) describes live input with continuous context. This segmented Base clone proposal has narrower semantics and should use Related, not Closes.
- Upstream runs Black 26.3.1/isort 5.13.2, tests on macOS/Python 3.10, and asks contributors to sign commits. A future submission should verify signatures on GitHub; local syntax/tests are not hosted CI.

## Artifacts

- [Complete patch](live-clone.patch), with base commit and SHA-256 in [base.json](base.json).
- [PR body](pull-request.md), following the upstream template. Suggested title: `feat(tts): add experimental prepared live cloning for Qwen3 Base`.
- [Validation](validation.json): actual-model checks and sanitized diagnostics. Raw private audio and ASR hypotheses are excluded.
- [Actual-model verifier](verify.py): takes your reference and transcript, writes WAVs without playback, and checks reuse/cancellation/legacy behavior.

### Apply and review

From a clean upstream checkout, create a proposal branch at the pinned base and apply the patch:

```sh
git switch -c codex/prepared-live-clone 7cc680b2bea1e8ef34b1a78ee4ff389953aebe40
git apply --check /path/to/live-clone.patch
git apply /path/to/live-clone.patch
python -c 'import mlx.core as mx; import pytest; mx.set_default_device(mx.cpu); raise SystemExit(pytest.main(["mlx_audio/tts/tests/test_qwen3_tts_live.py", "mlx_audio/tts/tests/test_qwen3_tts.py", "-q"]))'
```

Use an environment with upstream dependencies plus pytest/pytest-subtests. The proposal was checked on Python 3.12.10; upstream CI's Python 3.10 and the full suite remain unverified. Run Black 26.3.1 and isort 5.13.2 (`--profile black`) on the six changed Python files.

For actual-model checks, run the verifier with that environment's Python:

```sh
python /path/to/verify.py --checkout /path/to/patched-checkout \
  --reference /path/to/reference.wav --transcript-file /path/to/transcript.txt \
  --output /path/to/private-output
```

Use `--legacy-only` with a clean base checkout in a separate process; compare its `legacy-before.float_pcm_sha256` with the patched report. The pinned model is downloaded if absent. Generated files and the reference digest remain in the chosen output directory; do not commit private inputs or raw outputs.

Quality diagnostics use the pinned models and normalization in the [lab evaluator](https://github.com/kiarina/labs/blob/e8e270c/2026/10/22/qwen3-tts-live-audio-decoupling/evaluate.py). The three inputs are the verifier's full target and two character-fed targets; evaluation is a diagnostic, not a listening assessment.

### Validation limits

Focused tests passed (60 + 9 subtests), as did 36 additional Qwen3TTS tests excluding the legacy GenerateICL class. The aggregate selection including that class crashed natively in `mx.eval` on both clean base and patched code (exit 139); the cause is unresolved. The complete suite and whole-repository pre-commit were not run. See [validation.json](validation.json) and the [PR body](pull-request.md) for actual-model and quality results, including the short Japanese ASR mismatch.

### Submission boundary

This bundle is ready for review, not submitted. Before submission: agree the experimental segmented scope, recheck upstream changes, create/update the approved fork, make signed commits and confirm GitHub marks them Verified, then run hosted CI and attach its result. Keep the existing application deployment independent of upstream review. Patch preparation does not authorize posting a PR or comments.

## Evidence boundary

Production integration and the [public decoupling lab](https://github.com/kiarina/labs/tree/main/2026/10/22/qwen3-tts-live-audio-decoupling) explain the design choice. Their latency and speaker measurements must not be relabeled as tests of this upstream patch. The proposal's own focused and actual-model checks are recorded separately.
