"""Pure validation for LTX-2 generate requests."""

from kiapi.capabilities import ValidationError

from .._constants.variants import LTX25_VARIANT
from .._settings import settings_manager
from .._views.generate_request import GenerateRequest


def validate_generate(req: GenerateRequest, *, variant: str, has_audio: bool) -> None:
    settings = settings_manager.get_settings()

    width = req.width if req.width is not None else settings.default_width
    height = req.height if req.height is not None else settings.default_height
    fps = req.fps if req.fps is not None else settings.default_fps

    if width <= 0 or width % 64 != 0:
        raise ValidationError(f"width must be a positive multiple of 64 (got {width})")
    if height <= 0 or height % 64 != 0:
        raise ValidationError(
            f"height must be a positive multiple of 64 (got {height})"
        )
    if width > settings.max_width:
        raise ValidationError(f"width {width} exceeds max {settings.max_width}")
    if height > settings.max_height:
        raise ValidationError(f"height {height} exceeds max {settings.max_height}")
    if fps <= 0:
        raise ValidationError(f"fps must be positive (got {fps})")
    if has_audio and req.generate_audio:
        raise ValidationError(
            "cannot combine an audio file (A2V) with generate_audio; choose one"
        )

    _validate_ltx25_options(req, variant=variant, has_audio=has_audio)

    if req.auto_duration:
        if req.num_frames is not None:
            raise ValidationError("omit num_frames when auto_duration is true")
        return

    num_frames = (
        req.num_frames if req.num_frames is not None else settings.default_num_frames
    )
    if num_frames < 1 or (num_frames - 1) % 8 != 0:
        raise ValidationError(
            f"num_frames must be 1 + 8*k (e.g. 33, 97, 241, 481, 721); got {num_frames}"
        )
    if num_frames > settings.max_num_frames:
        raise ValidationError(
            f"num_frames {num_frames} exceeds max {settings.max_num_frames}"
        )


def _validate_ltx25_options(
    req: GenerateRequest, *, variant: str, has_audio: bool
) -> None:
    options = [
        name
        for name, used in (
            ("auto_duration", req.auto_duration),
            ("enhance_prompt", req.enhance_prompt),
            ("pipeline=dfr", req.pipeline == "dfr"),
            ("video_decoder=diffusion", req.video_decoder == "diffusion"),
        )
        if used
    ]
    if options and variant != LTX25_VARIANT:
        raise ValidationError(
            f"{', '.join(options)} requires model {LTX25_VARIANT!r} (got {variant!r})"
        )

    has_image = req.image is not None or req.end_image is not None
    if req.pipeline == "dfr" and (has_image or has_audio):
        raise ValidationError(
            "pipeline=dfr supports T2V only; remove image, end_image, and audio"
        )
