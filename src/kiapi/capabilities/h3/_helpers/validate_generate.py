"""Pure validation for MiniMax H3 generate requests."""

from kiapi.capabilities import ValidationError

from .._settings import settings_manager
from .._views.generate_request import GenerateRequest

MAX_REFERENCES = 12


def validate_generate(req: GenerateRequest) -> None:
    settings = settings_manager.get_settings()

    width = req.width if req.width is not None else settings.default_width
    height = req.height if req.height is not None else settings.default_height
    num_frames = (
        req.num_frames if req.num_frames is not None else settings.default_num_frames
    )

    if width <= 0 or width % 32 != 0:
        raise ValidationError(f"width must be a positive multiple of 32 (got {width})")
    if height <= 0 or height % 32 != 0:
        raise ValidationError(
            f"height must be a positive multiple of 32 (got {height})"
        )
    if width * height > settings.max_pixels:
        raise ValidationError(
            f"width * height {width * height} exceeds max {settings.max_pixels}"
        )
    if num_frames < 22 or (num_frames - 5) % 17 != 0:
        raise ValidationError(
            f"num_frames must be 5 + 17*k and at least 22 (e.g. 56, 124, 243); "
            f"got {num_frames}"
        )
    if num_frames > settings.max_num_frames:
        raise ValidationError(
            f"num_frames {num_frames} exceeds max {settings.max_num_frames}"
        )

    total = len(req.images) + len(req.videos) + len(req.audios)
    if total > MAX_REFERENCES:
        raise ValidationError(
            f"at most {MAX_REFERENCES} references in total (got {total})"
        )
    if req.audios and not (req.images or req.videos):
        raise ValidationError("audio references need an image or video reference")
    if req.use_video_audio and not req.videos:
        raise ValidationError("use_video_audio needs at least one video reference")
