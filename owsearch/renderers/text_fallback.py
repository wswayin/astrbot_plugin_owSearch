from __future__ import annotations

from ..models import MatchDetail, MatchSummary, PlayerProfile
from ..services.match_utils import extract_player_rows, summarize_match_for_text


def profile_text(profile: PlayerProfile) -> str:
    lines = [
        f"{profile.identity.full_id}",
        f"游戏时间：{profile.identity.game_time or '未知'} 小时",
    ]
    for role in profile.role_stats:
        lines.append(f"{role.role_label}：{role.rank_label}，{role.match_sum} 场，胜率 {role.win_rate or '未知'}%")
    return "\n".join(lines)


def match_list_text(matches: list[MatchSummary]) -> str:
    if not matches:
        return "没有查到最近对局。"
    lines = []
    for idx, match in enumerate(matches, 1):
        lines.append(
            f"{idx}. {match.begin_text} {match.mode_label} {match.result_label} "
            f"{match.team_score}:{match.opponent_score} KDA {match.kill}/{match.assist}/{match.death}"
        )
    return "\n".join(lines)


def detail_text(detail: MatchDetail) -> str:
    lines = [summarize_match_for_text(detail)]
    for row in extract_player_rows(detail):
        lines.append(
            f"{row['side']} {row['name']} {row['kill']}/{row['assist']}/{row['death']} "
            f"伤害{row['hero_damage']} 治疗{row['cure']} 承伤{row['resist_damage']}"
        )
    return "\n".join(lines)
