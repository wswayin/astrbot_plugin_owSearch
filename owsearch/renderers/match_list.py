from __future__ import annotations

from PIL import ImageDraw

from ..models import MatchSummary, PlayerIdentity
from .base import GREEN, MUTED, ORANGE, PANEL_2, RED, TEAL, TEXT, canvas, draw_header, font_pack, format_num, rounded_panel


def _result_color(match: MatchSummary):
    if match.result == 1:
        return GREEN
    if match.result < 0:
        return RED
    return ORANGE


def render_match_list_image(identity: PlayerIdentity, matches: list[MatchSummary], *, font_paths: list[str] | None = None):
    width = 1220
    row_h = 82
    height = max(520, 210 + row_h * max(1, len(matches)) + 48)
    image = canvas(width, height)
    draw = ImageDraw.Draw(image)
    fonts = font_pack(font_paths)
    draw_header(draw, f"{identity.full_id} 最近对局", f"回复 /ow 详情 1 查看单局，/ow 开庭 {identity.full_id} 1 开庭", width, fonts)

    rounded_panel(draw, (48, 176, width - 48, height - 44), fill=PANEL_2)
    if not matches:
        draw.text((82, 220), "没有查到最近对局。", font=fonts["body"], fill=MUTED)
        return image

    y = 204
    headers = ["#", "时间", "模式", "结果", "比分", "职责", "K/A/D", "伤害", "治疗", "承伤"]
    xs = [82, 138, 282, 390, 500, 610, 720, 840, 970, 1100]
    for x, head in zip(xs, headers):
        draw.text((x, y), head, font=fonts["small_bold"], fill=MUTED)
    y += 38
    for idx, match in enumerate(matches, 1):
        fill = (28, 32, 39) if idx % 2 else (35, 40, 48)
        draw.rounded_rectangle((70, y - 10, width - 70, y + 58), radius=8, fill=fill)
        color = _result_color(match)
        values = [
            str(idx),
            match.begin_text,
            match.mode_label,
            match.result_label,
            f"{match.team_score}:{match.opponent_score}",
            match.role_label,
            f"{match.kill}/{match.assist}/{match.death}",
            format_num(match.hero_damage),
            format_num(match.cure),
            format_num(match.resist_damage),
        ]
        for x, value in zip(xs, values):
            cell_color = color if value == match.result_label else (TEAL if value == match.mode_label else TEXT)
            draw.text((x, y + 8), value, font=fonts["small_bold"] if x == xs[0] else fonts["small"], fill=cell_color)
        y += row_h
    return image
