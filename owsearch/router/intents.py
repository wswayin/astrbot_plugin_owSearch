from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


IntentName = Literal[
    "help",
    "profile",
    "match_list",
    "match_detail",
    "sameplay_list",
    "sameplay_detail",
    "summary",
    "quick_strength",
    "competitive_strength",
    "rank_history",
    "rank_leaderboard",
    "hero_leaderboard",
    "hero_treemap",
    "hero_pick_rate",
    "hero_wiki",
    "shop",
    "patch_notes",
    "esports",
    "identity_search",
    "refresh",
    "debug_matches",
    "debug_config",
    "debug_ai",
    "debug_live",
    "debug_render",
    "analysis",
    "courtroom",
]


@dataclass(frozen=True)
class CommandIntent:
    name: IntentName
    bnet_id: str = ""
    bnet_id2: str = ""
    province: str = ""
    role: str = ""
    hero: str = ""
    mode: str = ""
    view: str = ""
    mmr: str = ""
    question: str = ""
    patch_kind: str = ""
    selector: str = ""
    index: int | None = None
    limit: int | None = None
    scope: str = ""
    start_season: int | None = None
    end_season: int | None = None
    history_limit: int | None = None
    show_all_heroes: bool = False
    analyze: bool = False
    refresh: bool = False
    raw_args: str = ""
