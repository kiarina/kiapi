import re

_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")
_LATIN = re.compile(r"[A-Za-z]")
_PUNCTUATION = re.compile(r"[、。\uff01\uff1f!?.,;:]\s*")


def segment_boundary(text: str, language: str, closed: bool) -> int:
    japanese = bool(_CJK.search(text)) or (
        not _LATIN.search(text) and language in {"ja", "japanese", "auto"}
    )
    minimum = 8 if japanese else 14
    for match in _PUNCTUATION.finditer(text):
        pos = match.start()
        if text[pos] in ".,:" and pos and text[pos - 1].isdigit():
            if pos + 1 < len(text) and text[pos + 1].isdigit():
                continue
            if pos + 1 == len(text) and not closed:
                continue
        if match.end() >= minimum:
            return match.end()
    if japanese:
        if len(text) >= 24:
            return 24
    else:
        words = list(re.finditer(r"\S+\s+", text))
        if len(words) >= 6:
            return words[5].end()
    return len(text) if closed else 0
