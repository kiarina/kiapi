from dataclasses import dataclass

from kiapi.capabilities.chat._operations.limit_to_context import limit_to_context


@dataclass
class Chunk:
    text: str
    prompt_tokens: int
    generation_tokens: int
    finish_reason: str | None = None


def _chunks(prompt_tokens: int, count: int, finish_reason: str = "stop"):  # type: ignore
    for n in range(1, count + 1):
        yield Chunk(text=f"t{n}", prompt_tokens=prompt_tokens, generation_tokens=n)
    yield Chunk(
        text="",
        prompt_tokens=prompt_tokens,
        generation_tokens=count,
        finish_reason=finish_reason,
    )


def test_stops_when_prompt_and_generated_tokens_fill_the_context() -> None:
    source = _chunks(prompt_tokens=8, count=5)

    out = list(limit_to_context(source, context_window=10))

    assert [c.text for c in out] == ["t1", "t2", ""]
    assert out[-1].finish_reason == "length"
    assert out[-1].generation_tokens == 2
    assert source.gi_frame is None  # the upstream generator was closed


def test_passes_chunks_through_when_the_context_is_not_reached() -> None:
    out = list(limit_to_context(_chunks(prompt_tokens=8, count=2), context_window=100))

    assert [c.text for c in out] == ["t1", "t2", ""]
    assert out[-1].finish_reason == "stop"


def test_passes_chunks_through_without_a_known_context_window() -> None:
    out = list(limit_to_context(_chunks(prompt_tokens=8, count=5), context_window=None))

    assert len(out) == 6
    assert out[-1].finish_reason == "stop"
