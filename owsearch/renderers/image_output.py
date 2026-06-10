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


MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".wav", ".mp3", ".ogg", ".m4a", ".amr", ".flac", ".webm"}


def _suffix_for_media_type(media_type: str, default: str = ".bin") -> tuple[str, str]:
    normalized = str(media_type or "").lower().split(";", 1)[0].strip()
    if normalized in {"image/jpeg", "image/jpg"}:
        return ".jpg", "image/jpeg"
    if normalized == "image/png":
        return ".png", "image/png"
    if normalized in {"audio/wav", "audio/x-wav", "audio/wave"}:
        return ".wav", "audio/wav"
    if normalized in {"audio/mpeg", "audio/mp3"}:
        return ".mp3", "audio/mpeg"
    if normalized in {"audio/ogg", "application/ogg"}:
        return ".ogg", "audio/ogg"
    if normalized in {"audio/mp4", "audio/x-m4a"}:
        return ".m4a", "audio/mp4"
    if normalized == "audio/amr":
        return ".amr", "audio/amr"
    if normalized == "audio/flac":
        return ".flac", "audio/flac"
    if normalized == "audio/webm":
        return ".webm", "audio/webm"
    return default, normalized or "application/octet-stream"


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


def save_image_bytes(data: bytes, output_dir: Path, *, prefix: str, media_type: str = "image/png") -> ImageFile:
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix, saved_media_type = _suffix_for_media_type(media_type or "image/png", default=".png")
    if suffix not in {".png", ".jpg"}:
        suffix, saved_media_type = ".png", "image/png"
    stem = f"{prefix}_{now_compact()}_{uuid4().hex[:8]}"
    path = output_dir / f"{stem}{suffix}"
    path.write_bytes(bytes(data or b""))
    return ImageFile(path=path, media_type=saved_media_type)


def save_media_bytes(data: bytes, output_dir: Path, *, prefix: str, media_type: str) -> ImageFile:
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix, saved_media_type = _suffix_for_media_type(media_type, default=".bin")
    stem = f"{prefix}_{now_compact()}_{uuid4().hex[:8]}"
    path = output_dir / f"{stem}{suffix}"
    path.write_bytes(bytes(data or b""))
    return ImageFile(path=path, media_type=saved_media_type)


def cleanup_render_dir(output_dir: Path, *, max_files: int) -> int:
    if max_files <= 0 or not output_dir.exists():
        return 0
    max_files = max(20, int(max_files))
    files = [
        path
        for path in output_dir.iterdir()
        if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES
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
