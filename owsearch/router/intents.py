from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


IntentName = Literal[
    "help",
    "profile",
    "match_list",
    "match_detail",
    "refresh",
    "debug_matches",
    "debug_config",
    "debug_live",
    "debug_render",
    "analysis",
    "courtroom",
]


@dataclass(frozen=True)
class CommandIntent:
    name: IntentName
    bnet_id: str = ""
    selector: str = ""
    index: int | None = None
    limit: int | None = None
    show_all_heroes: bool = False
    analyze: bool = False
    refresh: bool = False
    raw_args: str = ""
