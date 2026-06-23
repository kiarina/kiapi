from io import BytesIO

from PIL import Image, ImageDraw

from kiapi.core.app import AppContext


def create_sample_image(ctx: AppContext, *, size: int = 256) -> str:
    image = Image.new("RGB", (size, size), (245, 245, 238))
    draw = ImageDraw.Draw(image)
    margin = max(size // 8, 8)
    stroke = max(size // 32, 2)
    draw.rectangle(
        (margin, margin, size - margin, size - margin),
        outline=(40, 80, 160),
        width=stroke,
    )
    draw.ellipse(
        (
            int(size * 0.3),
            int(size * 0.28),
            int(size * 0.7),
            int(size * 0.66),
        ),
        fill=(240, 196, 76),
    )
    draw.line(
        (
            int(size * 0.2),
            int(size * 0.75),
            int(size * 0.8),
            int(size * 0.75),
        ),
        fill=(36, 120, 88),
        width=stroke,
    )

    out = BytesIO()
    image.save(out, format="PNG")
    rec = ctx.file_store.put_bytes(
        out.getvalue(),
        filename="kiapi_check_input.png",
        content_type="image/png",
        meta={"kind": "check_input"},
    )
    return rec.file_id
