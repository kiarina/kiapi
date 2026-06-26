from typing import Annotated

from fastapi import Path

from kiapi.core.file import FileID


def _get_file_id(
    file_id: Annotated[
        str,
        Path(
            pattern=r"^file_[0-9a-f]+$",
            description="Persistent file id returned by the Files API.",
            examples=["file_0123456789abcdef"],
        ),
    ],
) -> FileID:
    return file_id
