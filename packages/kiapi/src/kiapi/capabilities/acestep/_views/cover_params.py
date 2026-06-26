"""The complete contract for one ACE-Step cover run."""

from typing import Literal

from pydantic import BaseModel


class CoverParams(BaseModel):
    task: Literal["cover"] = "cover"
    model: str

    src: str
    src_audio: str
    prompt: str
    strength: float
    duration: int | None
    seed: int
    inference_steps: int | None
    guidance_scale: float | None
    shift: float | None

    def engine_params(self) -> dict:
        return self.model_dump(exclude={"task", "model", "src"})

    def meta_extra(self) -> dict:
        return {"model": self.model, "src": self.src}
