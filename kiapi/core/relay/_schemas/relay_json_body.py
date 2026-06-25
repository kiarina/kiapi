from typing import Any, Literal

from pydantic import BaseModel


class RelayJsonBody(BaseModel):
    type: Literal["json"] = "json"
    value: Any
