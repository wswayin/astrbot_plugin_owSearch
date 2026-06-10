from __future__ import annotations

from typing import Any

from PIL import ImageDraw

from ..models import MatchDetail
from ..services.match_utils import extract_player_rows, focus_player_row, summarize_match_for_text
from .base import (
    GREEN,
    MUTED,
    ORANGE,
    PANEL,
    PANEL_2,
    PURPLE,
    RED,
    TEAL,
    TEXT,
    YELLOW,
    badge,
    canvas,
    draw_header,
    draw_kv,
    draw_wrapped,
    font_pack,
    format_num,
    join_lines,
    rounded_panel,
)


def _result_color(result: int):
    if result == 1:
        return GREEN
    if result < 0:
        return RED
    return ORANGE


def render_match_detail_image(detail: MatchDetail, *, font_paths: list[str] | None = None):
    width, height = 1220, 820
    image = canvas(width, height)
    draw = ImageDraw.Draw(image)
    fonts = font_pack(font_paths)
    summary = detail.summary
    draw_header(draw, f"{detail.identity.full_id} 单局战绩", summarize_match_for_text(detail), width, fonts)

    result_color = _result_color(summary.result)
    rounded_panel(draw, (48, 178, width - 48, 390))
    badge(draw, (78, 208), summary.result_label, fonts["body_bold"], fill=result_color)
    draw.text((78, 270), f"{summary.team_score} : {summary.opponent_score}", font=fonts["hero"], fill=TEXT)
    draw.text((78, 334), f"{summary.mode_label} / {summary.begin_text}", font=fonts["body"], fill=MUTED)

    focus = focus_player_row(detail) or {}
    draw_kv(draw, 410, 218, "击杀", format_num(focus.get("kill", summary.kill)), fonts, accent=TEAL)
    draw_kv(draw, 560, 218, "助攻", format_num(focus.get("assist", summary.assist)), fonts, accent=YELLOW)
    draw_kv(draw, 710, 218, "死亡", format_num(focus.get("death", summary.death)), fonts, accent=RED)
    draw_kv(draw, 890, 218, "伤害", format_num(focus.get("hero_damage", summary.hero_damage)), fonts, accent=ORANGE)
    draw_kv(draw, 1040, 218, "治疗", format_num(focus.get("cure", summary.cure)), fonts, accent=GREEN)

    rounded_panel(draw, (48, 430, width - 48, height - 52), fill=PANEL_2)
    draw.text((78, 462), "焦点玩家", font=fonts["section"], fill=TEXT)
    if focus:
        left = 78
        y = 525
        entries = [
            ("玩家", focus.get("name") or detail.identity.full_id),
            ("职责", focus.get("role_type") or summary.role_label),
            ("段位", focus.get("rank_label") or "未知"),
            ("承伤", format_num(focus.get("damage_taken") or focus.get("resist_damage"))),
            ("受到治疗", format_num(focus.get("healing_taken"))),
            ("最后一击", format_num(focus.get("final_hit"))),
        ]
        for idx, (label, value) in enumerate(entries):
            x = left + (idx % 3) * 350
            y2 = y + (idx // 3) * 90
            draw.text((x, y2), label, font=fonts["small"], fill=MUTED)
            draw.text((x, y2 + 30), str(value), font=fonts["body_bold"], fill=TEXT if idx else TEAL)
    else:
        draw.text((78, 525), "详情里没有匹配到焦点玩家行，已展示列表摘要。", font=fonts["body"], fill=MUTED)
    return image


def render_all_players_image(detail: MatchDetail, *, font_paths: list[str] | None = None):
    rows = extract_player_rows(detail)
    width = 1320
    row_h = 64
    height = max(760, 220 + row_h * max(1, len(rows)) + 58)
    image = canvas(width, height)
    draw = ImageDraw.Draw(image)
    fonts = font_pack(font_paths)
    draw_header(draw, f"{detail.identity.full_id} 全员数据", summarize_match_for_text(detail), width, fonts)

    rounded_panel(draw, (48, 176, width - 48, height - 44), fill=PANEL_2)
    if not rows:
        draw.text((82, 220), "这局详情没有返回全员列表。", font=fonts["body"], fill=MUTED)
        return image

    xs = [78, 168, 430, 585, 700, 810, 930, 1050, 1180]
    headers = ["阵营", "玩家", "职责", "段位", "K/A/D", "伤害", "治疗", "承伤", "最后一击"]
    y = 202
    for x, head in zip(xs, headers):
        draw.text((x, y), head, font=fonts["small_bold"], fill=MUTED)
    y += 34
    for idx, row in enumerate(rows):
        is_focus = str(row.get("name") or "").casefold() == detail.identity.full_id.casefold()
        fill = (43, 45, 53) if idx % 2 else (32, 36, 43)
        if is_focus:
            fill = (56, 48, 32)
        draw.rounded_rectangle((68, y - 8, width - 68, y + 48), radius=8, fill=fill)
        side = "我方" if row.get("side") == "team" else "敌方"
        side_color = TEAL if row.get("side") == "team" else RED
        values = [
            side,
            str(row.get("name") or "未知玩家")[:22],
            str(row.get("role_type") or "-"),
            str(row.get("rank_label") or "-"),
            f"{row.get('kill', 0)}/{row.get('assist', 0)}/{row.get('death', 0)}",
            format_num(row.get("hero_damage")),
            format_num(row.get("cure")),
            format_num(row.get("resist_damage") or row.get("damage_taken")),
            format_num(row.get("final_hit")),
        ]
        for x, value in zip(xs, values):
            color = side_color if value == side else (ORANGE if is_focus and x == xs[1] else TEXT)
            draw.text((x, y + 8), value, font=fonts["small_bold"] if is_focus else fonts["small"], fill=color)
        y += row_h
    return image


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value:
        return [str(value)]
    return []


def render_analysis_image(detail: MatchDetail, analysis: Any, *, font_paths: list[str] | None = None):
    width, height = 1220, 900
    image = canvas(width, height)
    draw = ImageDraw.Draw(image)
    fonts = font_pack(font_paths)
    draw_header(draw, f"{detail.identity.full_id} AI 开庭", summarize_match_for_text(detail), width, fonts)

    ok = bool(getattr(analysis, "ok", False))
    data = getattr(analysis, "data", {}) or {}
    fallback = str(getattr(analysis, "fallback_text", "") or "")
    model = str(getattr(analysis, "model", "") or "")

    rounded_panel(draw, (48, 176, width - 48, 344))
    score = str(data.get("score") or ("-" if not ok else "B"))
    badge(draw, (78, 214), f"评分 {score}", fonts["body_bold"], fill=PURPLE if ok else RED, text_fill=TEXT)
    verdict = str(data.get("verdict") or data.get("general_summary") or data.get("summary") or fallback or "AI 分析暂不可用。")
    draw_wrapped(draw, (78, 272), verdict, fonts["section"], max_width=width - 156, fill=TEXT, max_lines=2)

    rounded_panel(draw, (48, 382, width - 48, height - 52), fill=PANEL_2)
    if not ok:
        draw.text((78, 420), "分析未生成", font=fonts["section"], fill=RED)
        draw_wrapped(draw, (78, 470), fallback or "请检查 AI 配置。", fonts["body"], max_width=width - 156, fill=TEXT)
        draw.text((78, height - 92), f"model: {model or '-'}", font=fonts["small"], fill=MUTED)
        return image

    sections = [
        ("亮点", join_lines(_as_list(data.get("highlights"))), TEAL),
        ("问题", join_lines(_as_list(data.get("problems"))), RED),
        ("建议", join_lines(_as_list(data.get("advice"))), ORANGE),
    ]
    x_positions = [78, 438, 798]
    for (title, body, color), x in zip(sections, x_positions):
        draw.rounded_rectangle((x, 420, x + 320, 730), radius=8, fill=PANEL)
        draw.text((x + 24, 448), title, font=fonts["section"], fill=color)
        draw_wrapped(draw, (x + 24, 500), body.replace("\n", "；"), fonts["body"], max_width=272, fill=TEXT, max_lines=7)

    meme = str(data.get("meme_line") or data.get("extra") or "")
    draw.text((78, 770), "庭审结语", font=fonts["section"], fill=YELLOW)
    draw_wrapped(draw, (78, 814), meme or "mamba out。", fonts["body_bold"], max_width=width - 156, fill=TEXT, max_lines=2)
    draw.text((78, height - 92), f"model: {model or '-'}", font=fonts["small"], fill=MUTED)
    return image
