from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image

from ..utils.time import now_compact


@dataclass(frozen=True)
class ImageFile:
    path: Path
    media_type: str


def _png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _jpeg_bytes(image: Image.Image, quality: int) -> bytes:
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def save_image(image: Image.Image, output_dir: Path, *, prefix: str, max_bytes: int) -> ImageFile:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{prefix}_{now_compact()}_{uuid4().hex[:8]}"
    png = _png_bytes(image)
    if len(png) <= max_bytes:
        path = output_dir / f"{stem}.png"
        path.write_bytes(png)
        return ImageFile(path=path, media_type="image/png")
    for quality in (92, 86, 80, 74, 68):
        jpeg = _jpeg_bytes(image, quality)
        if len(jpeg) <= max_bytes:
            path = output_dir / f"{stem}.jpg"
            path.write_bytes(jpeg)
            return ImageFile(path=path, media_type="image/jpeg")
    path = output_dir / f"{stem}.jpg"
    path.write_bytes(_jpeg_bytes(image, 62))
    return ImageFile(path=path, media_type="image/jpeg")


def cleanup_render_dir(output_dir: Path, *, max_files: int) -> int:
    if max_files <= 0 or not output_dir.exists():
        return 0
    max_files = max(20, int(max_files))
    files = [
        path
        for path in output_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}
    ]
    if len(files) <= max_files:
        return 0
    files.sort(key=lambda path: path.stat().st_mtime)
    removed = 0
    for path in files[: len(files) - max_files]:
        try:
            path.unlink()
            removed += 1
        except OSError:
            continue
    return removed
