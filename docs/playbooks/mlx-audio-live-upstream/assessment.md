# Upstream value assessment

Assessment date: 2026-10-22. The current patch remains unchanged and unsubmitted. The active decision is to compare against existing APIs before deciding whether to submit any model changes.

## Conclusion

Reusable model preparation has potential upstream value, but its necessity for the target call experience is not established. First compare ordinary short-text API calls with the current method. If the existing API is sufficient, no new generation API is needed. Narrowing to a prepared-clone primitive is an option only if the comparison demonstrates a meaningful gap.

## What is valuable

- Preparing the full reference before target text arrives, then reusing talker and decoder state for subsequent short utterances, serves voice assistants and conversational applications beyond this downstream integration.
- Cancellation and repeatable state cleanup enable interruption without rebuilding the voice reference.
- This work belongs near the model internals: applications should not have to copy private decoder buffers and caches.
- Existing generation is opt-in unaffected in the tested fixed-seed actual-model case, and cancellation/reuse are tested.

## What the evidence does not establish

- The actual-call improvement combined short-span completion with a one-second playback buffer. It does not isolate the benefit of the upstream model changes.
- Audio before text close is achievable with ordinary application-side segmentation and repeated existing streaming generate calls. That alone does not demonstrate why a new library input protocol is necessary.
- Existing upstream ICL already caches reference codec tokens and reference text IDs. The additional contribution is reusable prepared model/decoder state and the changed conditioning layout, not the invention of all reference caching.
- The reported preparation and first-PCM timings are single runs. There is no controlled comparison against warmed existing generate with identical segments, arrival schedule, reference, sampling controls and playback buffer, including memory and interruption recovery.
- One private reference, one model and one seed do not establish robust clone similarity, prosody, boundary behavior, or absence of reference leakage. CPU tests and ASR do not replace listening comparisons.

## Costs of the present patch

The seven-file patch adds 1,156 lines including tests/docs. Line count is not itself the concern: a new generation loop, snapshot ownership contract and input-source API all become maintenance obligations.

The implementation snapshots private decoder fields (`_buffer`, `_overflow`, `_transformer_cache`) and clones cache objects. Changes in decoder/cache implementations need corresponding review. The experimental reference EOS/fresh-prefix conditioning is a behavioral change that needs broader evidence even though existing entry points remain unchanged.

Hard-coded CJK/Latin boundaries, timeouts and character limits represent one application's latency/quality tradeoff. Different applications and languages need different policies. Exposing them through a generic `generate_live` name can suggest continuous target context, which this implementation does not provide. A worker is also occupied while waiting for input.

## Conditional upstream options

1. Retain the adopted downstream implementation while assessing upstream changes independently.
2. First propose explicit reference preparation and generation of an already committed short text span using that prepared state, with cancellation and cleanup. Let applications choose boundaries and queue work. API names here are conceptual, not a final contract.
3. Distinguish conventional reference preprocessing reuse from experimental talker-prefix/decoder-state reuse. If the experimental layout lacks a clear quality/performance advantage, upstream only the conventional reusable pieces and retain the experiment downstream.
4. Compare warmed existing generate and the prepared path under identical segments and buffers. Measure first PCM, sustained production, peak/retained memory and cancel-to-next-utterance delay. Include several shareable references, multiple seeds and Japanese/English listening samples with reference-leakage and prosody checks.
5. Use those results to discuss scope with maintainers before asking them to adopt the entire producer/session API. No external message has been sent.

## Upstream context

[#961](https://github.com/Blaizzy/mlx-audio/issues/961) is open and asks for first-token input and shared context/prosody across utterances. It demonstrates interest in the problem, not maintainer endorsement of this design; this proposal only addresses part of it.

[#1036](https://github.com/Blaizzy/mlx-audio/pull/1036) documents full-text conditioning for CustomVoice/VoiceDesign. It does not establish the correct Base-cloning layout, but is a reminder that conditioning changes can alter speaking behavior and need model-specific evidence.

See [validation](validation.json) for completed checks and [the current draft](pull-request.md) for the unchanged proposal. A prepared patch is not evidence that its full scope should be merged.

## Fair comparison criteria

Fix the transcript arrival schedule, committed spans, full reference, model, sampling controls, warm state and playback policy before comparing implementations. Compare ordinary generation with the prepared experimental path. The decoupling lab's cached/uncached span comparison uses experimental conditioning on both sides; it is not this standard-API control.

Waiting one second for text before synthesis and holding playback after the first PCM are separate controls. A persistent WebSocket can wrap ordinary short-text generation; HTTP can also reuse model preparation. Transport, model changes and concurrency must not be treated as one intervention.

Do not make the baseline lose solely because kiapi accepts only one active inference job. Use an isolated harness with equal hardware/resource budgets, testing serial and small bounded parallel configurations. Concurrent request acceptance is not necessarily concurrent GPU execution. Include worker/model duplication, contention, ordering and discarded work on cancellation in the measurements.

Measure onset, early/whole-response queue starvation, production speed, retained/peak memory and interrupt-to-next-response delay. Supplement fixed-condition comparisons with separately tuned practical configurations. Existing API sufficiency, rather than a predetermined PR design, is the first decision.
