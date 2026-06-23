from typing import Annotated

from pydantic import Field

from .._schemas.file_data_url_ref import FileDataURLRef
from .._schemas.file_id_ref import FileIDRef
from .._schemas.file_url_ref import FileURLRef

type FileRef = Annotated[
    FileIDRef | FileURLRef | FileDataURLRef,
    Field(discriminator="type"),
]
