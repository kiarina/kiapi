from typing import Annotated

from fastapi import File, UploadFile


def _get_file(
    file: Annotated[
        UploadFile,
        File(
            description="File bytes to store and reference from inference requests.",
        ),
    ],
) -> UploadFile:
    return file
