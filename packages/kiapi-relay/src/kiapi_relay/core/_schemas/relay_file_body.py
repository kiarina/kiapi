from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class RelayFileBody(BaseModel):
    type: Literal["file"] = "file"
    path: Path
    content_type: str
    size: int
