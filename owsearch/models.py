from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .constants import RESULT_LABELS, ROLE_LABELS
from .utils.time import format_timestamp


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def pick(data: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return default


@dataclass(frozen=True)
class PlayerIdentity:
    query: str
    full_id: str
    bnet_id: str = ""
    customer_token: str = ""
    icon: str = ""
    title: str = ""
    level: int = 0
    game_time: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_search_payload(cls, query: str, payload: dict[str, Any]) -> "PlayerIdentity":
        data = payload.get("data") if isinstance(payload, dict) else {}
        if not isinstance(data, dict):
            data = {}
        return cls(
            query=query,
            full_id=str(pick(data, "name", "fullId", "full_id", default=query) or query),
            bnet_id=str(pick(data, "bnetId", "bnet_id", default="") or ""),
            customer_token=str(pick(data, "customerToken", "customer_token", default="") or ""),
            icon=str(pick(data, "icon", default="") or ""),
            title=str(pick(data, "title", default="") or ""),
            level=as_int(pick(data, "level", default=0)),
            game_time=str(pick(data, "gameTime", "game_time", default="") or ""),
            raw=dict(data),
        )

    @classmethod
    def from_cache(cls, payload: dict[str, Any]) -> "PlayerIdentity":
        return cls(
            query=str(payload.get("query") or payload.get("full_id") or ""),
            full_id=str(payload.get("full_id") or payload.get("query") or ""),
            bnet_id=str(payload.get("bnet_id") or ""),
            customer_token=str(payload.get("customer_token") or ""),
            icon=str(payload.get("icon") or ""),
            title=str(payload.get("title") or ""),
            level=as_int(payload.get("level")),
            game_time=str(payload.get("game_time") or ""),
            raw=dict(payload.get("raw") or {}),
        )

    def to_cache(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "full_id": self.full_id,
            "bnet_id": self.bnet_id,
            "customer_token": self.customer_token,
            "icon": self.icon,
            "title": self.title,
            "level": self.level,
            "game_time": self.game_time,
            "raw": self.raw,
        }


@dataclass(frozen=True)
class RoleStat:
    role_type: str
    role_label: str
    match_sum: int = 0
    win_rate: str = ""
    kda: str = ""
    rank_name: str = ""
    rank_sub_tier: str = ""
    rank_score: int = 0
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "RoleStat":
        rank = data.get("lastRankInfo") or data.get("rankInfo") or {}
        if not isinstance(rank, dict):
            rank = {}
        role_type = str(pick(data, "roleType", "role_type", default="") or "")
        return cls(
            role_type=role_type,
            role_label=ROLE_LABELS.get(role_type, role_type or "未知"),
            match_sum=as_int(pick(data, "matchSum", "match_sum", default=0)),
            win_rate=str(pick(data, "winRate", "win_rate", default="") or ""),
            kda=str(pick(data, "kda", default="") or ""),
            rank_name=str(pick(rank, "rank_name", "rankName", default="") or ""),
            rank_sub_tier=str(pick(rank, "rank_sub_tier", "rankSubTier", default="") or ""),
            rank_score=as_int(pick(rank, "rankScore", "rank_score", default=0)),
            raw=dict(data),
        )

    @property
    def rank_label(self) -> str:
        if self.rank_name and self.rank_sub_tier:
            return f"{self.rank_name} {self.rank_sub_tier}"
        return self.rank_name or "无段位"


@dataclass(frozen=True)
class PlayerProfile:
    identity: PlayerIdentity
    role_stats: list[RoleStat] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    card_raw: dict[str, Any] = field(default_factory=dict)
    count_raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MatchSummary:
    match_id: str
    begin_ts: int = 0
    result: int = 0
    game_mode: str = ""
    instance_type: str = ""
    map_guid: str = ""
    map_name: str = ""
    hero_guid: str = ""
    hero_name: str = ""
    hero_icon: str = ""
    role_type: str = ""
    team_score: int = 0
    opponent_score: int = 0
    kill: int = 0
    assist: int = 0
    death: int = 0
    hero_damage: int = 0
    cure: int = 0
    resist_damage: int = 0
    season: int = 0
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "MatchSummary":
        return cls(
            match_id=str(pick(data, "matchId", "match_id", default="") or ""),
            begin_ts=as_int(pick(data, "beginTs", "begin_ts", "startTime", default=0)),
            result=as_int(pick(data, "matchRet", "result", default=0)),
            game_mode=str(pick(data, "gameMode", "game_mode", default="") or ""),
            instance_type=str(pick(data, "instanceType", "instance_type", default="") or ""),
            map_guid=str(pick(data, "mapGuid", "map_guid", default="") or ""),
            map_name=str(pick(data, "mapName", "map_name", default="") or ""),
            hero_guid=str(pick(data, "heroGuid", "heroId", "hero_guid", default="") or ""),
            hero_name=str(pick(data, "heroName", "hero_name", default="") or ""),
            hero_icon=str(pick(data, "heroIcon", "hero_icon", default="") or ""),
            role_type=str(pick(data, "roleType", "role_type", default="") or ""),
            team_score=as_int(pick(data, "teamScore", "team_score", default=0)),
            opponent_score=as_int(pick(data, "opponentScore", "opponent_score", default=0)),
            kill=as_int(pick(data, "kill", default=0)),
            assist=as_int(pick(data, "assist", default=0)),
            death=as_int(pick(data, "death", default=0)),
            hero_damage=as_int(pick(data, "heroDamage", "damage", default=0)),
            cure=as_int(pick(data, "cure", "healing", default=0)),
            resist_damage=as_int(pick(data, "resistDamage", "mitigation", default=0)),
            season=as_int(pick(data, "_dashenSeason", "season", default=0)),
            raw=dict(data),
        )

    @property
    def is_fight(self) -> bool:
        return "fight" in self.game_mode.lower()

    @property
    def result_label(self) -> str:
        return RESULT_LABELS.get(self.result, "未知")

    @property
    def role_label(self) -> str:
        return ROLE_LABELS.get(self.role_type, self.role_type or "未知")

    @property
    def mode_label(self) -> str:
        lower = f"{self.game_mode} {self.instance_type}".lower()
        if "fight" in lower:
            return "角斗"
        if "rank" in lower or "sport" in lower:
            return "竞技"
        if "leisure" in lower or "quick" in lower:
            return "快速"
        return self.game_mode or self.instance_type or "未知"

    @property
    def begin_text(self) -> str:
        return format_timestamp(self.begin_ts)


@dataclass(frozen=True)
class MatchDetail:
    identity: PlayerIdentity
    summary: MatchSummary
    payload: dict[str, Any]
    source_match: dict[str, Any] = field(default_factory=dict)
    match_kind: Literal["normal", "fight"] = "normal"

    @property
    def data(self) -> dict[str, Any]:
        data = self.payload.get("data", self.payload)
        return data if isinstance(data, dict) else {}


@dataclass(frozen=True)
class ReplyItem:
    kind: Literal["text", "image"]
    content: str = ""
    path: str = ""
    media_type: str = ""

    @classmethod
    def text(cls, content: str) -> "ReplyItem":
        return cls(kind="text", content=content)

    @classmethod
    def image(cls, path: str, media_type: str = "image/png") -> "ReplyItem":
        return cls(kind="image", path=path, media_type=media_type)
