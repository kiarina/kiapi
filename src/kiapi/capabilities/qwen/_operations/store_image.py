import time
from typing import Any

from kiapi.core.file import FileStore
from kiapi.core.workdir import create_work_dir


def store_image(
    image: Any,
    *,
    fmt: str,
    quality: int,
    files: FileStore,
    meta: dict[str, Any],
) -> dict[str, Any]:
    from PIL import Image

    pil = getattr(image, "image", image)
    ext = "jpg" if fmt == "jpeg" else fmt
    tmp_dir = create_work_dir("image/qwen")
    out_path = tmp_dir / f"image.{ext}"
    save_kwargs: dict[str, Any] = {}
    if fmt in ("jpeg", "webp"):
        save_kwargs["quality"] = quality
    if fmt == "jpeg":
        if pil.mode == "RGBA":
            # JPEG has no alpha; flatten transparent areas onto white.
            background = Image.new("RGB", pil.size, (255, 255, 255))
            background.paste(pil, mask=pil.getchannel("A"))
            pil = background
        else:
            pil = pil.convert("RGB")
    pil.save(out_path, format=fmt.upper(), **save_kwargs)
    if not out_path.exists():
        raise RuntimeError("generation finished but no image file was produced")
    rec = files.put_path(
        out_path,
        filename=f"qwen_{int(time.time())}.{ext}",
        content_type=f"image/{fmt}",
        meta=meta,
        move=True,
    )
    return {"file_id": rec.file_id, "image_bytes": rec.size, **meta}
