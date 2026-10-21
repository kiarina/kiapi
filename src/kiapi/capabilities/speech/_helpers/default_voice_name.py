from pathlib import Path

# Characters of the transcript kept when it names a voice.
TRANSCRIPT_NAME_CHARS = 20


def default_voice_name(filename: str | None, transcript: str | None) -> str | None:
    """Name an unnamed voice by its file name, or else by the start of its transcript."""
    if filename and (stem := Path(filename).stem.strip()):
        return stem[:200]
    text = " ".join((transcript or "").split())
    if not text:
        return None
    if len(text) <= TRANSCRIPT_NAME_CHARS:
        return text
    return text[:TRANSCRIPT_NAME_CHARS] + "…"
