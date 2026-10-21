import re
import unicodedata

# Sentence ends: CJK and full-width marks anywhere, ASCII marks before a space.
_SENTENCE_END = re.compile(r"(?<=[。！？])|(?<=[.!?])\s+|\n+")  # noqa: RUF001


def segment_sentences(text: str, words: list[dict]) -> list[dict[str, float | str]]:
    """Group aligned words (``{word, start, end}``, in order) into sentences.

    The forced aligner drops punctuation, so each sentence takes as many words
    as it has letters and digits.
    """
    segments: list[dict[str, float | str]] = []
    index = 0
    for sentence in (s.strip() for s in _SENTENCE_END.split(text)):
        if not sentence:
            continue
        need = len(_kept(sentence))
        taken: list[dict] = []
        count = 0
        while index < len(words) and count < need:
            taken.append(words[index])
            count += len(_kept(words[index]["word"]))
            index += 1
        if taken:
            segments.append(
                {"start": taken[0]["start"], "end": taken[-1]["end"], "text": sentence}
            )
        elif segments:
            segments[-1]["text"] = f"{segments[-1]['text']}{sentence}"
    if index < len(words) and segments:
        segments[-1]["end"] = words[-1]["end"]
    return segments


def join_texts(texts: list[str], languages: list[str | None]) -> str:
    """Join chunk texts, with a space only between space-separated languages."""
    out = ""
    for text, language in zip(texts, languages, strict=True):
        if not text:
            continue
        if out and language not in _NO_SPACE:
            out += " "
        out += text
    return out


_NO_SPACE = frozenset({"Chinese", "Cantonese", "Japanese", "Thai"})


def _kept(text: str) -> str:
    # Same rule as the aligner: letters, numbers, and the apostrophe.
    return "".join(
        ch for ch in text if ch == "'" or unicodedata.category(ch)[0] in ("L", "N")
    )
