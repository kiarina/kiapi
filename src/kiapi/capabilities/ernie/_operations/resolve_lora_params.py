from collections.abc import Iterable
from dataclasses import dataclass, field

from kiapi.capabilities import get_file_path
from kiapi.core.app import AppContext

from .._schemas.lora_ref import LoraRef


@dataclass
class LoraParams:
    paths: list[str] = field(default_factory=list)
    scales: list[float] = field(default_factory=list)


def resolve_lora_params(ctx: AppContext, loras: Iterable[LoraRef]) -> LoraParams:
    params = LoraParams()

    for lr in loras:
        params.paths.append(get_file_path(ctx.file_store, lr.file, kind="lora"))
        params.scales.append(lr.scale)

    return params
