from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import ImageFont


CJK_NAME_HINTS = (
    "noto",
    "sourcehan",
    "source-han",
    "sarasa",
    "wqy",
    "wenquanyi",
    "droid",
    "fallback",
    "pingfang",
    "heiti",
    "songti",
    "msyh",
    "simsun",
    "simhei",
)

LATIN_FALLBACK_HINTS = (
    "dejavu",
    "liberation",
    "freefont",
    "arial",
)

CJK_SAMPLE_TEXT = "测试守望先锋"
MISSING_GLYPH_SAMPLE = "\U0010ffff"

REGULAR_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/Deng.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/source-han-sans/SourceHanSansCN-Regular.otf",
    "/usr/share/fonts/opentype/source-han-sans/SourceHanSansSC-Regular.otf",
    "/usr/share/fonts/adobe-source-han-sans/SourceHanSansCN-Regular.otf",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

BOLD_CANDIDATES = [
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/Dengb.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/source-han-sans/SourceHanSansCN-Bold.otf",
    "/usr/share/fonts/opentype/source-han-sans/SourceHanSansSC-Bold.otf",
    "/usr/share/fonts/adobe-source-han-sans/SourceHanSansCN-Bold.otf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

FONT_SEARCH_DIRS = [
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    "/opt/share/fonts",
    "/System/Library/Fonts",
    "/Library/Fonts",
    "C:/Windows/Fonts",
]

FONT_EXTENSIONS = {".ttf", ".ttc", ".otf"}


def _existing(paths: list[str]) -> list[str]:
    return [path for path in paths if Path(path).exists()]


def _path_sort_key(path: Path) -> tuple[int, str]:
    name = path.name.lower().replace(" ", "").replace("_", "").replace("-", "")
    is_cjk = any(hint.replace("-", "") in name for hint in CJK_NAME_HINTS)
    return (0 if is_cjk else 1, str(path).lower())


def _font_files_under(directory: Path) -> list[str]:
    try:
        files = [path for path in directory.rglob("*") if path.suffix.lower() in FONT_EXTENSIONS and path.is_file()]
    except Exception:
        return []
    return [str(path) for path in sorted(files, key=_path_sort_key)]


def _expand_font_paths(paths: list[str]) -> list[str]:
    expanded: list[str] = []
    for item in paths:
        path = Path(item).expanduser()
        if path.is_file():
            expanded.append(str(path))
        elif path.is_dir():
            expanded.extend(_font_files_under(path))
        else:
            expanded.append(str(path))
    return expanded


@lru_cache(maxsize=1)
def _system_font_paths() -> tuple[str, ...]:
    discovered: list[str] = []
    for item in FONT_SEARCH_DIRS:
        directory = Path(item)
        if directory.is_dir():
            discovered.extend(_font_files_under(directory))
    return tuple(discovered)


def _dedupe(paths: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for path in paths:
        key = str(Path(path)).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def _candidate_paths(bold: bool, custom_paths: list[str] | None = None) -> list[str]:
    candidates = _expand_font_paths(list(custom_paths or []))
    candidates.extend(BOLD_CANDIDATES if bold else REGULAR_CANDIDATES)
    candidates.extend(_system_font_paths())
    return _dedupe(candidates)


def _try_font_path(path: str, size: int) -> ImageFont.ImageFont | None:
    try:
        return ImageFont.truetype(path, size=size)
    except Exception:
        return None


def _glyph_signature(font: ImageFont.ImageFont, text: str) -> tuple[tuple[int, int], tuple[int, int, int, int] | None, bytes]:
    mask = font.getmask(text)
    return mask.size, mask.getbbox(), bytes(mask)


@lru_cache(maxsize=512)
def _font_supports_cjk(path: str) -> bool:
    font = _try_font_path(path, 32)
    if font is None:
        return False
    try:
        missing = _glyph_signature(font, MISSING_GLYPH_SAMPLE)
        sample_signatures = [_glyph_signature(font, char) for char in CJK_SAMPLE_TEXT]
    except Exception:
        return False
    supported = [signature for signature in sample_signatures if signature != missing]
    return len(set(supported)) >= 2


def resolve_font_path(*, bold: bool = False, custom_paths: list[str] | None = None) -> str | None:
    loadable: list[str] = []
    for path in _existing(_candidate_paths(bold, custom_paths)):
        if _try_font_path(path, 18) is not None:
            loadable.append(path)
            if _font_supports_cjk(path):
                return path
    return loadable[0] if loadable else None


def load_font(size: int, *, bold: bool = False, custom_paths: list[str] | None = None) -> ImageFont.ImageFont:
    path = resolve_font_path(bold=bold, custom_paths=custom_paths)
    if path:
        font = _try_font_path(path, size)
        if font:
            return font
    return ImageFont.load_default()


def _looks_like_cjk_font(path: str | None, custom_paths: list[str] | None = None) -> bool:
    if not path:
        return False
    if _font_supports_cjk(path):
        return True
    normalized = str(Path(path)).lower().replace(" ", "").replace("_", "")
    if any(hint in normalized for hint in CJK_NAME_HINTS):
        return True
    if any(hint in normalized for hint in LATIN_FALLBACK_HINTS):
        return False
    return False


def has_cjk_font(custom_paths: list[str] | None = None) -> bool:
    return _looks_like_cjk_font(resolve_font_path(custom_paths=custom_paths), custom_paths)


def font_diagnostics(custom_paths: list[str] | None = None) -> dict[str, str | bool]:
    regular = resolve_font_path(custom_paths=custom_paths)
    bold = resolve_font_path(bold=True, custom_paths=custom_paths)
    return {
        "cjk_ready": _looks_like_cjk_font(regular, custom_paths),
        "regular": regular or "",
        "bold": bold or "",
    }
