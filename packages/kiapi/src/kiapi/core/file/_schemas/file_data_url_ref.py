from typing import Literal

from pydantic import BaseModel, Field


class FileDataURLRef(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "data_url",
                    "data_url": "data:image/png;base64,iVBORw0KGgo...",
                },
            ],
        },
    }

    type: Literal["data_url"] = "data_url"
    data_url: str = Field(..., min_length=1)
