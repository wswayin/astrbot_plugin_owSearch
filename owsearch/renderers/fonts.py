from __future__ import annotations

from pathlib import Path

from PIL import ImageFont


REGULAR_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

BOLD_CANDIDATES = [
    "C:/Windows/Fonts/msyhbd.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _existing(paths: list[str]) -> list[str]:
    return [path for path in paths if Path(path).exists()]


def load_font(size: int, *, bold: bool = False, custom_paths: list[str] | None = None) -> ImageFont.ImageFont:
    candidates = list(custom_paths or [])
    candidates.extend(BOLD_CANDIDATES if bold else REGULAR_CANDIDATES)
    for path in _existing(candidates):
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def has_cjk_font(custom_paths: list[str] | None = None) -> bool:
    candidates = list(custom_paths or []) + REGULAR_CANDIDATES[:5]
    return bool(_existing(candidates))
