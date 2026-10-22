import random
import time
from collections.abc import Callable
from typing import Any

from kiapi.capabilities.speech.live import TextSource
from kiapi.core.app import AppContext
from kiapi.core.job import Job, JobCanceledError

from .._helpers.patch_mlx_audio import clear_pending_prime
from .prepare_call import _acquire_prepared


def run_call_utterance(
    ctx: AppContext,
    state: dict[str, Any],
    source: TextSource,
    job: Job,
    emit: Callable[[bytes], None],
) -> tuple[dict[str, Any], list[str]]:
    import mlx.core as mx
    import numpy as np

    from kiapi.capabilities.speech.live import (
        fork_reference,
        generate_prepared,
        generate_segments,
    )

    if job.cancel_requested():
        raise JobCanceledError()
    payload, prepared = _acquire_prepared(ctx, state)
    source.bind(payload.model.tokenizer)
    mx.random.seed(
        state["seed"] if state["seed"] is not None else random.randint(0, 2**31 - 1)
    )
    started = time.perf_counter()
    samples = 0
    trace: dict[str, Any] = {}
    if state.get("generation") == "segments":
        chunks = generate_segments(
            payload.model,
            prepared,
            source,
            language=state["language"],
            cancel_requested=job.cancel_requested,
            trace=trace,
        )
    else:
        session = fork_reference(payload.model, prepared)
        chunks = generate_prepared(
            payload.model,
            prepared.prompt,
            source,
            session,
            cancel_requested=job.cancel_requested,
        )
    try:
        for audio in chunks:
            if job.cancel_requested():
                raise JobCanceledError()
            pcm = (np.clip(np.array(audio), -1, 1) * 32767).astype("<i2").tobytes()
            emit(pcm)
            samples += len(pcm) // 2
    except InterruptedError:
        raise JobCanceledError() from None
    finally:
        chunks.close()
        payload.model.speech_tokenizer.decoder.reset_streaming_state()
        clear_pending_prime()
    return {
        "generation": state.get("generation", "tokens"),
        "segments": len(trace.get("segments", [])),
        "sample_rate": 24000,
        "duration_s": samples / 24000,
        "total_s": time.perf_counter() - started,
    }, []
