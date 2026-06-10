from __future__ import annotations

DASHEN_API_ROOT = "https://datamsapi.ds.163.com/v1/a19ld5tool"
DASHEN_CUSTOMER_API_BASE = f"{DASHEN_API_ROOT}/customer"
DASHEN_SEARCH_BNET_ACCOUNT_URL = f"{DASHEN_API_ROOT}/searchBnetAccount"

DASHEN_ORIGIN = "https://act.ds.163.com"
DASHEN_REFERER = "https://act.ds.163.com/"
DASHEN_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 "
    "app/df_client dfVersion/100111"
)

NORMAL_GAME_MODES = ("leisure", "sport")
FIGHT_GAME_MODES = ("QuickFight", "LeisureFight", "SportFight")

ROLE_LABELS = {
    "tank": "重装",
    "dps": "输出",
    "damage": "输出",
    "healer": "支援",
    "support": "支援",
    "open": "开放",
}

ROLE_ORDER = {
    "tank": 0,
    "dps": 1,
    "damage": 1,
    "healer": 2,
    "support": 2,
}

RESULT_LABELS = {
    1: "胜利",
    0: "平局",
    -1: "失败",
}
