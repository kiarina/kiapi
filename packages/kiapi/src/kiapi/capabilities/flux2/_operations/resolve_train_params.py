"""Merge a train request with settings defaults into the complete TrainParams."""

from .._settings import Flux2Settings
from .._views.train_params import TrainParams
from .._views.train_request import TrainRequest


def resolve_train_params(
    settings: Flux2Settings,
    req: TrainRequest,
    *,
    variant: str,
) -> TrainParams:
    steps = (
        req.steps if req.steps is not None else settings.train_steps.get(variant, 40)
    )
    return TrainParams(
        training_mode=req.training_mode,
        seed=req.seed,
        steps=steps,
        guidance=req.guidance,
        quantize=(
            req.quantize
            if req.quantize is not None
            else settings.train_quantize.get(variant, 8)
        ),
        max_resolution=req.max_resolution,
        low_ram=req.low_ram,
        num_epochs=req.num_epochs,
        batch_size=req.batch_size,
        timestep_low=(
            req.timestep_low
            if req.timestep_low is not None
            else settings.train_timestep_low.get(variant, 25)
        ),
        timestep_high=req.timestep_high if req.timestep_high is not None else steps,
        learning_rate=req.learning_rate,
        save_frequency=req.save_frequency if req.save_frequency is not None else 10**9,
        lora_rank=req.lora_rank,
        lora_include_ff=req.lora_include_ff,
        lora_layers=req.lora_layers,
    )
