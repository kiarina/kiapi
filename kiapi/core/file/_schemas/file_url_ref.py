from typing import Literal

from pydantic import BaseModel, Field


class FileURLRef(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"type": "url", "url": "https://example.com/input.png"},
            ],
        },
    }

    type: Literal["url"] = "url"
    url: str = Field(..., min_length=1)
