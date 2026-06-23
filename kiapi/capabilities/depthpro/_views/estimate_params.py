"""The complete contract for one Depth Pro image → depth map run.

Built from settings + request by ``resolve_estimate_params``; the model needs
nothing else to produce the depth map and its metadata. ``image_path`` is the
locally resolved input file, kept out of the recorded metadata in favour of
``image_file_id``.
"""

from typing import Literal

from pydantic import BaseModel


class EstimateParams(BaseModel):
    kind: Literal["estimate"] = "estimate"
    model: str

    image_file_id: str
    image_path: str
    quantize: int | None
    include_depth_data: bool
