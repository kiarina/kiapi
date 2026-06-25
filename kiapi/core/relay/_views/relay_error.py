from pydantic import BaseModel


class RelayError(BaseModel):
    code: str
    message: str
    retryable: bool
