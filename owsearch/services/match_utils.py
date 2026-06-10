from __future__ import annotations

import datetime as dt
from typing import Any, Iterable, Sequence

from ..constants import ROLE_ORDER
from ..models import MatchDetail, MatchSummary, as_int, pick

DASHEN_SEASON_ROLLOVER_AT = dt.datetime(2026, 4, 15, 0, 0, 0)
DASHEN_SEASON_BEFORE_ROLLOVER = 21
DASHEN_SEASON_AFTER_ROLLOVER = 22


def get_live_dashen_season(now: dt.datetime | None = None) -> int:
    now = now or dt.datetime.now()
    return DASHEN_SEASON_AFTER_ROLLOVER if now >= DASHEN_SEASON_ROLLOVER_AT else DASHEN_SEASON_BEFORE_ROLLOVER


def get_recent_dashen_seasons(include_previous: bool = True) -> list[int]:
    current = get_live_dashen_season()
    seasons = [current]
    if include_previous and current > 1:
        seasons.append(current - 1)
    return seasons


def iter_dashen_season_request_values(season: int | None) -> Iterable[int | None]:
    if season is None:
        yield None
        return
    if int(season) == get_live_dashen_season():
        yield None
    yield int(season)


def payload_data(payload: Any) -> Any:
    if isinstance(payload, dict):
        return payload.get("data", payload)
    return payload


def extract_match_entries(payload: Any, *preferred_keys: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [dict(item) for item in payload if isinstance(item, dict)]
    data = payload_data(payload)
    if isinstance(data, list):
        return [dict(item) for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    keys = preferred_keys or ("matchList", "recentMatchList")
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return [dict(item) for item in value if isinstance(item, dict)]
    return []


def match_begin_ts(match: dict[str, Any]) -> int:
    return as_int(pick(match, "beginTs", "begin_ts", "startTime", default=0))


def merge_unique_match_entries(existing: Sequence[dict[str, Any]], new_entries: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in (existing or [], new_entries or []):
        for item in source:
            if not isinstance(item, dict):
                continue
            copied = dict(item)
            match_id = str(copied.get("matchId") or copied.get("match_id") or "").strip()
            if match_id:
                if match_id in seen:
                    continue
                seen.add(match_id)
            merged.append(copied)
    merged.sort(key=match_begin_ts, reverse=True)
    return merged


def is_fight_match_payload(match: dict[str, Any]) -> bool:
    return "fight" in str(match.get("gameMode") or match.get("game_mode") or "").lower()


def detail_root(detail: MatchDetail) -> dict[str, Any]:
    data = payload_data(detail.payload)
    return data if isinstance(data, dict) else {}


def _rank_label(rank: dict[str, Any]) -> str:
    name = str(pick(rank, "rank_name", "rankName", default="") or "")
    sub = str(pick(rank, "rank_sub_tier", "rankSubTier", default="") or "")
    if name and sub:
        return f"{name} {sub}"
    return name or "无段位"


def _row_from_player(player: dict[str, Any], side: str) -> dict[str, Any]:
    rank = player.get("rankInfo") if isinstance(player.get("rankInfo"), dict) else {}
    role = str(pick(player, "roleType", "role_type", default="") or "")
    return {
        "side": side,
        "name": str(pick(player, "name", "fullId", "full_id", default="未知玩家") or "未知玩家"),
        "bnet_id": str(pick(player, "bnetId", "bnet_id", default="") or ""),
        "customer_token": str(pick(player, "customerToken", "customer_token", default="") or ""),
        "hero_guid": str(pick(player, "heroGuid", "heroId", "hero_guid", default="") or ""),
        "hero_name": str(pick(player, "heroName", "hero_name", default="") or ""),
        "role_type": role,
        "kill": as_int(pick(player, "kill", default=0)),
        "assist": as_int(pick(player, "assist", default=0)),
        "death": as_int(pick(player, "death", default=0)),
        "hero_damage": as_int(pick(player, "heroDamage", "damage", default=0)),
        "cure": as_int(pick(player, "cure", "healing", default=0)),
        "resist_damage": as_int(pick(player, "resistDamage", "mitigation", default=0)),
        "final_hit": as_int(pick(player, "finalHit", "final_hit", default=0)),
        "damage_taken": as_int(pick(player, "damageTaken", "damage_taken", default=0)),
        "healing_taken": as_int(pick(player, "healingTaken", "healing_taken", default=0)),
        "rank_label": _rank_label(rank),
        "raw": dict(player),
    }


def extract_player_rows(detail: MatchDetail) -> list[dict[str, Any]]:
    root = detail_root(detail)
    rows: list[dict[str, Any]] = []
    for item in root.get("teammateList") or root.get("teamList") or []:
        if isinstance(item, dict):
            rows.append(_row_from_player(item, "team"))
    for item in root.get("enemyList") or root.get("opponentList") or []:
        if isinstance(item, dict):
            rows.append(_row_from_player(item, "enemy"))
    rows.sort(
        key=lambda row: (
            0 if row.get("side") == "team" else 1,
            ROLE_ORDER.get(str(row.get("role_type") or ""), 9),
            -int(row.get("hero_damage") or 0),
        )
    )
    return rows


def focus_player_row(detail: MatchDetail, rows: Sequence[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    rows = list(rows or extract_player_rows(detail))
    target_names = {
        detail.identity.full_id.casefold(),
        detail.identity.query.casefold(),
    }
    target_bnet = str(detail.identity.bnet_id or "").strip()
    for row in rows:
        name = str(row.get("name") or "").casefold()
        if name and name in target_names:
            return dict(row)
        if target_bnet and str(row.get("bnet_id") or "") == target_bnet:
            return dict(row)
    if detail.source_match:
        summary = MatchSummary.from_payload(detail.source_match)
        return {
            "side": "team",
            "name": detail.identity.full_id,
            "bnet_id": detail.identity.bnet_id,
            "hero_guid": summary.hero_guid,
            "hero_name": summary.hero_name,
            "role_type": summary.role_type,
            "kill": summary.kill,
            "assist": summary.assist,
            "death": summary.death,
            "hero_damage": summary.hero_damage,
            "cure": summary.cure,
            "resist_damage": summary.resist_damage,
            "rank_label": "",
            "raw": dict(detail.source_match),
        }
    return None


def summarize_match_for_text(detail: MatchDetail) -> str:
    root = detail_root(detail)
    summary = detail.summary
    duration = as_int(pick(root, "gameTimeSec", "duration", default=0))
    duration_text = f"{duration // 60}:{duration % 60:02d}" if duration > 0 else "未知"
    return (
        f"模式={summary.mode_label}; 结果={summary.result_label}; "
        f"比分={summary.team_score}:{summary.opponent_score}; "
        f"时间={summary.begin_text}; 时长={duration_text}; "
        f"地图={summary.map_name or summary.map_guid or pick(root, 'mapName', 'mapGuid', default='未知')}"
    )
