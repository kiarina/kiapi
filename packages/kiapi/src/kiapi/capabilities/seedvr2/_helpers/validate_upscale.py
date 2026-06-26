from kiapi.capabilities import ValidationError

from .._settings import settings_manager
from .._views.upscale_request import UpscaleRequest


def _parse_scale(value: str) -> float | None:
    if not value.endswith("x"):
        return None
    raw = value[:-1]
    try:
        return float(raw)
    except ValueError:
        raise ValidationError("resolution scale must look like '2x' or '1.5x'")  # noqa: B904


def validate_upscale(req: UpscaleRequest) -> None:
    settings = settings_manager.get_settings()
    if req.quantize is not None and req.quantize not in (3, 4, 5, 6, 8):
        raise ValidationError("quantize must be one of 3, 4, 5, 6, 8")
    if not 0.0 <= req.softness <= 1.0:
        raise ValidationError("softness must be in 0..1")

    resolution = req.resolution
    if isinstance(resolution, int):
        if resolution < settings.min_resolution or resolution > settings.max_resolution:
            raise ValidationError(
                f"resolution must be in {settings.min_resolution}..{settings.max_resolution}"
            )
        return

    if not isinstance(resolution, str):
        raise ValidationError(
            "resolution must be an integer shortest-edge target or a scale like '2x'"
        )
    if resolution.endswith("x"):
        scale = _parse_scale(resolution)
        if scale is None or scale <= 0 or scale > settings.max_scale:
            raise ValidationError(
                f"resolution scale must be > 0 and <= {settings.max_scale}x"
            )
        return
    try:
        pixels = int(resolution)
    except ValueError:
        raise ValidationError(  # noqa: B904
            "resolution must be an integer shortest-edge target or a scale like '2x'"
        )
    if pixels < settings.min_resolution or pixels > settings.max_resolution:
        raise ValidationError(
            f"resolution must be in {settings.min_resolution}..{settings.max_resolution}"
        )
