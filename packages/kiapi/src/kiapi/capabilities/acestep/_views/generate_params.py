"""The complete contract for one ACE-Step generate/text2music run."""

from typing import Literal

from pydantic import BaseModel


class GenerateParams(BaseModel):
    task: Literal["text2music"] = "text2music"
    model: str

    prompt: str
    lyrics: str
    duration: int
    lang: str
    seed: int
    inference_steps: int | None
    guidance_scale: float | None
    shift: float | None

    def engine_params(self) -> dict:
        return self.model_dump(exclude={"task", "model"})

    def meta_extra(self) -> dict:
        return {"model": self.model}
