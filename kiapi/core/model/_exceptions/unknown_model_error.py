class UnknownModelError(ValueError):
    """Requested ``model`` doesn't match any registry entry → HTTP 400."""
