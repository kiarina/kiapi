"""The complete contract for one ACE-Step source-separation stem run."""

from typing import Literal

from pydantic import BaseModel


class ExtractParams(BaseModel):
    task: Literal["extract"] = "extract"
    model: str

    src: str
    src_audio: str
    target: str
    seed: int
    inference_steps: int | None
    guidance_scale: float | None
    shift: float | None

    def engine_params(self) -> dict:
        return self.model_dump(exclude={"task", "model", "src"})

    def meta_extra(self) -> dict:
        return {"model": self.model, "src": self.src, "target": self.target}
