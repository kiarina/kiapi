import time
from collections.abc import Callable, Generator
from typing import Any

from ._fork_reference import fork_reference
from ._generate_prepared import generate_prepared
from ._prepared_reference import PreparedReference
from ._segment_boundary import segment_boundary
from ._text_source import TextSource


def generate_segments(
    model: Any,
    prepared: PreparedReference,
    source: TextSource,
    *,
    language: str = "auto",
    cancel_requested: Callable[[], bool] = lambda: False,
    trace: dict[str, Any] | None = None,
    max_frames: int = 1000,
) -> Generator[Any, None, None]:
    trace = trace if trace is not None else {}
    trace.update(segments=[], codes=[], stop=None)
    started = time.perf_counter()
    cursor = 0
    frames = 0

    def check_cancel() -> None:
        if source.is_cancelled() or cancel_requested():
            raise InterruptedError("Generation canceled")

    while True:
        check_cancel()
        with source.condition:
            available, closed, version = (
                source.text[cursor:],
                source.closed,
                source.version,
            )
        length = segment_boundary(available, language, closed)
        if length:
            piece = available[:length]
            cursor += length
            if not piece.strip():
                continue
            check_cancel()
            span = TextSource(max_chars=source.max_chars)
            span.bind(model.tokenizer)
            span.push(piece)
            span.close()
            session = fork_reference(model, prepared)
            part: dict[str, Any] = {}
            begin = time.perf_counter() - started
            chunks = generate_prepared(
                model,
                prepared.prompt,
                span,
                session,
                trace=part,
                max_frames=min(500, max_frames - frames),
                cancel_requested=lambda: source.is_cancelled() or cancel_requested(),
            )
            try:
                yield from chunks
            finally:
                chunks.close()
            frames += len(part["codes"])
            trace["codes"].extend(part["codes"])
            trace["segments"].append(
                {
                    "chars": length,
                    "through_chars": cursor,
                    "start": begin,
                    "end": time.perf_counter() - started,
                    "frames": len(part["codes"]),
                    "stop": part.get("stop"),
                }
            )
        elif closed:
            trace["stop"] = "eos"
            return
        else:
            source.wait(version, cancel_requested=cancel_requested)
