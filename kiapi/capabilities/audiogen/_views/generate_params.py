"""Resolved AudioGen parameters passed to the model layer."""

from pydantic import BaseModel


class GenerateParams(BaseModel):
    model: str
    prompt: str
    duration: float
    seed: int
    top_k: int
    top_p: float
    temperature: float
    cfg_coef: float
