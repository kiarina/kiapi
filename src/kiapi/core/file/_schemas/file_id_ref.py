from typing import Literal

from pydantic import BaseModel, Field


class FileIDRef(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"type": "file_id", "file_id": "file_0123456789abcdef"},
            ],
        },
    }

    type: Literal["file_id"] = "file_id"
    file_id: str = Field(..., min_length=1)
