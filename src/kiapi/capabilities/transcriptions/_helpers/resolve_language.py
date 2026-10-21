from kiapi.capabilities import ValidationError

# Qwen3-ASR language names, by ISO 639 code.
LANGUAGES = {
    "zh": "Chinese",
    "en": "English",
    "yue": "Cantonese",
    "ar": "Arabic",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "pt": "Portuguese",
    "id": "Indonesian",
    "it": "Italian",
    "ko": "Korean",
    "ru": "Russian",
    "th": "Thai",
    "vi": "Vietnamese",
    "ja": "Japanese",
    "tr": "Turkish",
    "hi": "Hindi",
    "ms": "Malay",
    "nl": "Dutch",
    "sv": "Swedish",
    "da": "Danish",
    "fi": "Finnish",
    "pl": "Polish",
    "cs": "Czech",
    "fil": "Filipino",
    "fa": "Persian",
    "el": "Greek",
    "ro": "Romanian",
    "hu": "Hungarian",
    "mk": "Macedonian",
}

# Languages Qwen3-ForcedAligner can time.
ALIGN_LANGUAGES = frozenset(
    {
        "Chinese",
        "Cantonese",
        "English",
        "German",
        "Spanish",
        "French",
        "Italian",
        "Portuguese",
        "Russian",
        "Korean",
        "Japanese",
    }
)


def resolve_language(language: str | None) -> str | None:
    """Map an ISO 639 code (`ja`, `ja-JP`) or name (`japanese`) to Qwen3-ASR's name.

    None means detect.
    """
    if language is None or not language.strip() or language.strip().lower() == "auto":
        return None
    value = language.strip().lower()
    by_name = {name.lower(): name for name in LANGUAGES.values()}
    if value in by_name:
        return by_name[value]
    code = value.replace("_", "-").split("-")[0]
    if code in LANGUAGES:
        return LANGUAGES[code]
    raise ValidationError(
        f"language {language!r} is not supported; use one of "
        + ", ".join(sorted(LANGUAGES))
        + " (or omit it)"
    )
