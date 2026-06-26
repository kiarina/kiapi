from typing import Annotated

from fastapi import Header


def get_accept(
    accept: Annotated[
        str | None,
        Header(
            alias="Accept",
            description=(
                "Response media type preference. application/json returns the Job "
                "JSON; otherwise sync requests with one artifact return raw bytes "
                "when possible."
            ),
            examples=["application/json", "image/png", "audio/wav", "video/mp4"],
        ),
    ] = None,
) -> str | None:
    return accept
