from __future__ import annotations

from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from .fonts import load_font

BG = (18, 20, 24)
PANEL = (34, 38, 46)
PANEL_2 = (43, 48, 58)
TEXT = (244, 247, 252)
MUTED = (169, 178, 193)
SUBTLE = (104, 116, 133)
ORANGE = (255, 151, 51)
TEAL = (46, 205, 195)
RED = (235, 86, 86)
GREEN = (94, 204, 123)
YELLOW = (246, 201, 87)
PURPLE = (172, 137, 255)


def canvas(width: int, height: int) -> Image.Image:
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / max(1, height - 1)
        r = int(BG[0] * (1 - ratio) + 29 * ratio)
        g = int(BG[1] * (1 - ratio) + 32 * ratio)
        b = int(BG[2] * (1 - ratio) + 38 * ratio)
        draw.line((0, y, width, y), fill=(r, g, b))
    draw.rectangle((0, 0, width, 8), fill=ORANGE)
    return image


def font_pack(custom_paths: list[str] | None = None) -> dict[str, ImageFont.ImageFont]:
    return {
        "hero": load_font(52, bold=True, custom_paths=custom_paths),
        "title": load_font(36, bold=True, custom_paths=custom_paths),
        "section": load_font(28, bold=True, custom_paths=custom_paths),
        "body": load_font(24, custom_paths=custom_paths),
        "body_bold": load_font(24, bold=True, custom_paths=custom_paths),
        "small": load_font(19, custom_paths=custom_paths),
        "small_bold": load_font(19, bold=True, custom_paths=custom_paths),
    }


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), str(text), font=font)
    return int(box[2] - box[0])


def draw_header(draw: ImageDraw.ImageDraw, title: str, subtitle: str, width: int, fonts: dict[str, ImageFont.ImageFont]) -> None:
    draw.text((48, 38), title, font=fonts["hero"], fill=TEXT)
    draw.text((50, 100), subtitle, font=fonts["body"], fill=MUTED)
    draw.line((48, 142, width - 48, 142), fill=(72, 79, 92), width=2)


def rounded_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], *, fill: tuple[int, int, int] = PANEL) -> None:
    draw.rounded_rectangle(box, radius=8, fill=fill, outline=(72, 79, 92), width=1)


def badge(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    *,
    fill: tuple[int, int, int] = ORANGE,
    text_fill: tuple[int, int, int] = (20, 22, 26),
) -> tuple[int, int, int, int]:
    x, y = xy
    w = text_width(draw, text, font) + 28
    h = 34
    box = (x, y, x + w, y + h)
    draw.rounded_rectangle(box, radius=8, fill=fill)
    draw.text((x + 14, y + 6), text, font=font, fill=text_fill)
    return box


def draw_kv(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, value: str, fonts: dict[str, ImageFont.ImageFont], accent=TEAL) -> None:
    draw.text((x, y), label, font=fonts["small"], fill=MUTED)
    draw.text((x, y + 28), value, font=fonts["section"], fill=accent)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    text = str(text or "")
    if not text:
        return [""]
    lines: list[str] = []
    current = ""
    for char in text:
        if char == "\n":
            lines.append(current)
            current = ""
            continue
        test = current + char
        if current and text_width(draw, test, font) > max_width:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines or [""]


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    *,
    max_width: int,
    fill: tuple[int, int, int] = TEXT,
    line_gap: int = 8,
    max_lines: int | None = None,
) -> int:
    x, y = xy
    lines = wrap_text(draw, text, font, max_width)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip("。,.，") + "..."
    line_height = int(font.size if hasattr(font, "size") else 20) + line_gap
    for idx, line in enumerate(lines):
        draw.text((x, y + idx * line_height), line, font=font, fill=fill)
    return y + len(lines) * line_height


def format_num(value: int | float | str | None) -> str:
    try:
        number = int(float(value or 0))
    except (TypeError, ValueError):
        return "0"
    return f"{number:,}"


def join_lines(items: Iterable[str], empty: str = "暂无") -> str:
    lines = [str(item).strip() for item in items if str(item).strip()]
    return "\n".join(lines) if lines else empty
