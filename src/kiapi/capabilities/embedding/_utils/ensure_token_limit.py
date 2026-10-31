from kiapi.capabilities import CapabilityError


def ensure_token_limit(token_count: int, max_length: int) -> None:
    if token_count > max_length:
        raise CapabilityError(
            f"input has {token_count} tokens; the maximum is {max_length}"
        )
