from kiapi.capabilities import ValidationError

# Qwen3-TTS language names, by ISO 639-1 code.
LANGUAGES = {
    "zh": "chinese",
    "en": "english",
    "ja": "japanese",
    "ko": "korean",
    "de": "german",
    "fr": "french",
    "ru": "russian",
    "pt": "portuguese",
    "es": "spanish",
    "it": "italian",
}


def resolve_language(language: str | None) -> str:
    """Map a BCP 47 tag (`ja-JP`) or language name (`japanese`) to Qwen3-TTS's name."""
    if language is None or not language.strip() or language.strip().lower() == "auto":
        return "auto"
    value = language.strip().lower()
    if value in LANGUAGES.values():
        return value
    code = value.replace("_", "-").split("-")[0]
    if code in LANGUAGES:
        return LANGUAGES[code]
    raise ValidationError(
        f"language {language!r} is not supported; use one of "
        + ", ".join(sorted(LANGUAGES))
        + " (or omit it)"
    )
