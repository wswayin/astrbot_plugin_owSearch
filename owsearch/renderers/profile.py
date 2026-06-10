from __future__ import annotations

from PIL import ImageDraw

from ..models import PlayerProfile
from .base import MUTED, ORANGE, PANEL_2, TEAL, TEXT, badge, canvas, draw_header, draw_kv, font_pack, format_num, rounded_panel


def render_profile_image(profile: PlayerProfile, *, font_paths: list[str] | None = None):
    width, height = 1180, 820
    image = canvas(width, height)
    draw = ImageDraw.Draw(image)
    fonts = font_pack(font_paths)
    draw_header(draw, profile.identity.full_id, "玩家资料 / Dashen Profile", width, fonts)

    rounded_panel(draw, (48, 178, width - 48, 370))
    badge(draw, (78, 210), "PLAYER", fonts["small_bold"], fill=ORANGE)
    draw.text((78, 260), profile.identity.title or "公开资料", font=fonts["section"], fill=TEXT)
    draw.text((78, 305), f"等级 {profile.identity.level or '-'}", font=fonts["body"], fill=MUTED)
    draw_kv(draw, 420, 222, "游戏时间", f"{profile.identity.game_time or '未知'} h", fonts)
    summary = profile.summary
    draw_kv(draw, 650, 222, "竞技总场次", format_num(summary.get("matchSum")), fonts, accent=ORANGE)
    draw_kv(draw, 880, 222, "竞技胜率", f"{summary.get('winRate') or '未知'}%", fonts)

    rounded_panel(draw, (48, 410, width - 48, height - 52), fill=PANEL_2)
    draw.text((78, 438), "职责概览", font=fonts["section"], fill=TEXT)
    y = 500
    if not profile.role_stats:
        draw.text((78, y), "没有公开的竞技职责数据。", font=fonts["body"], fill=MUTED)
        return image
    for role in profile.role_stats[:4]:
        draw.rounded_rectangle((78, y, width - 78, y + 70), radius=8, fill=(31, 35, 43))
        draw.text((104, y + 20), role.role_label, font=fonts["body_bold"], fill=TEAL)
        draw.text((240, y + 20), role.rank_label, font=fonts["body"], fill=TEXT)
        draw.text((510, y + 20), f"{role.match_sum} 场", font=fonts["body"], fill=MUTED)
        draw.text((690, y + 20), f"胜率 {role.win_rate or '未知'}%", font=fonts["body"], fill=MUTED)
        draw.text((910, y + 20), f"KDA {role.kda or '-'}", font=fonts["body"], fill=MUTED)
        y += 84
    return image
