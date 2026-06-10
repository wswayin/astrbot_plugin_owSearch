from __future__ import annotations

import re
import shlex

from .intents import CommandIntent


COMMAND_PREFIX_RE = re.compile(r"^\s*/?(ow|守望)\b", re.IGNORECASE)
BATTLE_TAG_RE = re.compile(r"^[^\s#]+#\d{3,}$")
UUIDISH_RE = re.compile(r"^[0-9a-fA-F-]{16,}$")
SUMMARY_SCOPE_ALIASES = {
    "today": "today",
    "今日": "today",
    "今天": "today",
    "今日总结": "today",
    "今天总结": "today",
    "日报": "today",
    "总结": "today",
    "summary": "today",
    "yesterday": "yesterday",
    "昨日": "yesterday",
    "昨天": "yesterday",
    "昨日总结": "yesterday",
    "昨天总结": "yesterday",
    "week": "week",
    "weekly": "week",
    "本周": "week",
    "周报": "week",
    "本周总结": "week",
    "周总结": "week",
}
GAME_MODE_ALIASES = {
    "quick": "quick",
    "快速": "quick",
    "快排": "quick",
    "休闲": "quick",
    "competitive": "competitive",
    "竞技": "competitive",
    "排位": "competitive",
    "天梯": "competitive",
}
MMR_ALIASES = {
    "all": "all",
    "全部": "all",
    "全段位": "all",
    "青铜": "Bronze",
    "bronze": "Bronze",
    "白银": "Silver",
    "silver": "Silver",
    "黄金": "Gold",
    "gold": "Gold",
    "白金": "Platinum",
    "铂金": "Platinum",
    "platinum": "Platinum",
    "钻石": "Diamond",
    "diamond": "Diamond",
    "大师": "Master",
    "master": "Master",
    "宗师": "Grandmaster",
    "grandmaster": "Grandmaster",
    "英杰": "Champion",
    "冠军": "Champion",
    "champion": "Champion",
}
PATCH_KIND_ALIASES = {
    "": "latest",
    "latest": "latest",
    "最新": "latest",
    "自动": "latest",
    "auto": "latest",
    "small": "small",
    "小": "small",
    "小更": "small",
    "小更新": "small",
    "小补丁": "small",
    "big": "big",
    "major": "big",
    "大": "big",
    "大更": "big",
    "大更新": "big",
    "大补丁": "big",
}


def _strip_command(text: str) -> str:
    return COMMAND_PREFIX_RE.sub("", str(text or ""), count=1).strip()


def _split_args(text: str) -> list[str]:
    try:
        return shlex.split(text)
    except ValueError:
        return text.split()


def _parse_index(value: str) -> int | None:
    token = str(value or "").strip().rstrip("*")
    if not token.isdigit():
        return None
    parsed = int(token)
    if parsed <= 0:
        return None
    return parsed


def _parse_limit(tokens: list[str], default: int | None = None) -> int | None:
    for token in reversed(tokens):
        if token.isdigit():
            value = int(token)
            if 1 <= value <= 20:
                return value
    return default


def _parse_positive_int(value: str) -> int | None:
    token = str(value or "").strip()
    if not token.isdigit():
        return None
    parsed = int(token)
    return parsed if parsed > 0 else None


def _summary_scope(value: str, default: str = "today") -> str:
    return SUMMARY_SCOPE_ALIASES.get(str(value or "").strip().lower(), default)


def _game_mode(value: str, default: str = "quick") -> str:
    return GAME_MODE_ALIASES.get(str(value or "").strip().lower(), default)


def _mmr(value: str, default: str = "all") -> str:
    return MMR_ALIASES.get(str(value or "").strip().lower(), default)


def _patch_kind(value: str, default: str = "latest") -> str:
    return PATCH_KIND_ALIASES.get(str(value or "").strip().lower(), default)


def _parse_summary_intent(head: str, rest: list[str], raw_args: str) -> CommandIntent:
    scope = _summary_scope(head)
    bnet_id = ""
    if rest:
        first_scope = _summary_scope(rest[0], "")
        if first_scope and len(rest) > 1:
            scope = first_scope
            bnet_id = rest[1]
        else:
            bnet_id = rest[0]
            if len(rest) > 1:
                scope = _summary_scope(rest[1], scope)
    return CommandIntent(name="summary", bnet_id=bnet_id, scope=scope, raw_args=raw_args)


def parse_command(message: str) -> CommandIntent:
    raw_args = _strip_command(message)
    tokens = _split_args(raw_args)
    if not tokens:
        return CommandIntent(name="help", raw_args=raw_args)

    head = tokens[0].lower().lstrip("/")
    rest = tokens[1:]

    shortcut_index = _parse_index(tokens[0])
    if shortcut_index is not None:
        return CommandIntent(
            name="match_detail",
            index=shortcut_index,
            show_all_heroes=tokens[0].endswith("*"),
            analyze=tokens[0].endswith("**"),
            raw_args=raw_args,
        )

    if head in {"help", "帮助", "菜单"}:
        return CommandIntent(name="help", raw_args=raw_args)

    if head in {"profile", "资料", "信息", "卡片"}:
        bnet_id = rest[0] if rest else ""
        return CommandIntent(name="profile", bnet_id=bnet_id, raw_args=raw_args)

    if head in {"matches", "match", "战绩", "对局", "列表", "最近"}:
        bnet_id = rest[0] if rest else ""
        limit = _parse_limit(rest[1:] if len(rest) > 1 else [], None)
        return CommandIntent(name="match_list", bnet_id=bnet_id, limit=limit, raw_args=raw_args)

    if head in {"sameplay", "同玩", "共玩"}:
        player1 = rest[0] if rest else ""
        player2 = rest[1] if len(rest) > 1 else ""
        limit = _parse_limit(rest[2:] if len(rest) > 2 else [], None)
        return CommandIntent(name="sameplay_list", bnet_id=player1, bnet_id2=player2, limit=limit, raw_args=raw_args)

    if head in {"sameplaydetail", "sameplay_detail", "同玩详情", "共玩详情", "同玩单局", "共玩单局"}:
        player1 = rest[0] if rest else ""
        player2 = rest[1] if len(rest) > 1 else ""
        selector = rest[2] if len(rest) > 2 else "1"
        show_all = any(token.endswith("*") for token in rest[2:])
        analyze = any(token.endswith("**") for token in rest[2:])
        return CommandIntent(
            name="sameplay_detail",
            bnet_id=player1,
            bnet_id2=player2,
            selector=selector.rstrip("*"),
            index=_parse_index(selector) or 1,
            show_all_heroes=show_all,
            analyze=analyze,
            raw_args=raw_args,
        )

    if head in {"sameplaycourt", "sameplay_court", "同玩开庭", "共玩开庭"}:
        player1 = rest[0] if rest else ""
        player2 = rest[1] if len(rest) > 1 else ""
        selector = rest[2] if len(rest) > 2 else "1"
        return CommandIntent(
            name="sameplay_detail",
            bnet_id=player1,
            bnet_id2=player2,
            selector=selector.rstrip("*"),
            index=_parse_index(selector) or 1,
            show_all_heroes=True,
            analyze=True,
            raw_args=raw_args,
        )

    if head in SUMMARY_SCOPE_ALIASES:
        return _parse_summary_intent(head, rest, raw_args)

    if head in {"quickstrength", "quick_strength", "快速强度", "快强", "快速强"}:
        bnet_id = rest[0] if rest else ""
        limit = _parse_limit(rest[1:] if len(rest) > 1 else [], None)
        return CommandIntent(name="quick_strength", bnet_id=bnet_id, limit=limit, raw_args=raw_args)

    if head in {"competitivestrength", "competitive_strength", "竞技强度", "竞强", "竞技强"}:
        bnet_id = rest[0] if rest else ""
        limit = _parse_limit(rest[1:] if len(rest) > 1 else [], None)
        return CommandIntent(name="competitive_strength", bnet_id=bnet_id, limit=limit, raw_args=raw_args)

    if head in {"rankhistory", "rank_history", "段位历史", "历史段位", "段位记录"}:
        bnet_id = rest[0] if rest else ""
        start_season = _parse_positive_int(rest[1]) if len(rest) > 1 else None
        end_season = _parse_positive_int(rest[2]) if len(rest) > 2 else None
        return CommandIntent(
            name="rank_history",
            bnet_id=bnet_id,
            start_season=start_season,
            end_season=end_season,
            raw_args=raw_args,
        )

    if head in {"rankleaderboard", "rank_leaderboard", "省榜", "段位榜", "段位排行", "省排名"}:
        province = rest[0] if rest else ""
        role = rest[1] if len(rest) > 1 else ""
        return CommandIntent(name="rank_leaderboard", province=province, role=role, raw_args=raw_args)

    if head in {"heroleaderboard", "hero_leaderboard", "英雄榜", "英雄排行", "英雄省榜"}:
        province = rest[0] if rest else ""
        hero = rest[1] if len(rest) > 1 else ""
        mode = rest[2] if len(rest) > 2 else ""
        return CommandIntent(name="hero_leaderboard", province=province, hero=hero, mode=mode, raw_args=raw_args)

    if head in {"herotreemap", "hero_treemap", "英雄占比", "英雄树图", "英雄使用", "英雄池"}:
        bnet_id = rest[0] if rest else ""
        mode = _game_mode(rest[1] if len(rest) > 1 else "", "competitive")
        season = _parse_positive_int(rest[2]) if len(rest) > 2 else None
        return CommandIntent(name="hero_treemap", bnet_id=bnet_id, mode=mode, start_season=season, raw_args=raw_args)

    if head in {"pickrate", "pick_rate", "heropickrate", "hero_pick_rate", "登场率", "英雄登场率", "选取率"}:
        mode = _game_mode(rest[0] if rest else "", "quick")
        mmr = _mmr(rest[1] if len(rest) > 1 else "", "all")
        return CommandIntent(name="hero_pick_rate", view="ranking", mode=mode, mmr=mmr, raw_args=raw_args)

    if head in {"pickratehistory", "pick_rate_history", "登场率历史", "英雄登场率历史", "选取率历史"}:
        hero = rest[0] if rest else ""
        mode = _game_mode(rest[1] if len(rest) > 1 else "", "quick")
        mmr = _mmr(rest[2] if len(rest) > 2 else "", "all")
        history_limit = _parse_limit(rest[3:] if len(rest) > 3 else [], None)
        return CommandIntent(
            name="hero_pick_rate",
            view="history",
            hero=hero,
            mode=mode,
            mmr=mmr,
            history_limit=history_limit,
            raw_args=raw_args,
        )

    if head in {"wiki", "herowiki", "hero_wiki", "英雄资料", "英雄百科", "英雄维基", "技能"}:
        hero = rest[0] if rest else ""
        question = " ".join(rest[1:]) if len(rest) > 1 else ""
        return CommandIntent(name="hero_wiki", hero=hero, question=question, raw_args=raw_args)

    if head in {"shop", "商城", "商店"}:
        return CommandIntent(name="shop", raw_args=raw_args)

    if head in {"patch", "patchnotes", "patch_notes", "补丁", "更新", "补丁说明"}:
        kind = _patch_kind(rest[0] if rest else "", "latest")
        return CommandIntent(name="patch_notes", patch_kind=kind, raw_args=raw_args)

    if head in {"esports", "owesports", "ow_esports", "电竞", "赛程", "比赛"}:
        return CommandIntent(name="esports", raw_args=raw_args)

    if head in {"identity", "identity_search", "playeridentity", "反查", "身份反查", "bnet反查"}:
        bnet_id = rest[0] if rest else ""
        limit = _parse_limit(rest[1:] if len(rest) > 1 else [], None)
        return CommandIntent(name="identity_search", bnet_id=bnet_id, limit=limit, raw_args=raw_args)

    if head in {"detail", "详情", "单局"}:
        if not rest:
            return CommandIntent(name="match_detail", raw_args=raw_args)
        show_all = any(token.endswith("*") for token in rest)
        analyze = any(token.endswith("**") for token in rest)
        first = rest[0]
        first_index = _parse_index(first)
        if first_index is not None and len(rest) == 1:
            return CommandIntent(
                name="match_detail",
                index=first_index,
                show_all_heroes=show_all,
                analyze=analyze,
                raw_args=raw_args,
            )
        bnet_id = first if BATTLE_TAG_RE.match(first) else ""
        selector = rest[1] if bnet_id and len(rest) > 1 else first
        index = _parse_index(selector)
        return CommandIntent(
            name="match_detail",
            bnet_id=bnet_id,
            selector=selector.rstrip("*"),
            index=index,
            show_all_heroes=show_all,
            analyze=analyze,
            raw_args=raw_args,
        )

    if head in {"analysis", "分析", "锐评"}:
        if not rest:
            return CommandIntent(name="analysis", raw_args=raw_args)
        first = rest[0]
        index = _parse_index(first)
        if index is None and not UUIDISH_RE.match(first):
            selector = rest[1] if len(rest) > 1 else ""
            return CommandIntent(
                name="courtroom",
                bnet_id=first,
                selector=selector.rstrip("*"),
                index=_parse_index(selector) or 1,
                show_all_heroes=True,
                analyze=True,
                raw_args=raw_args,
            )
        bnet_id = "" if index is not None or UUIDISH_RE.match(first) else first
        selector = first if not bnet_id else (rest[1] if len(rest) > 1 else "")
        return CommandIntent(
            name="analysis",
            bnet_id=bnet_id,
            selector=selector.rstrip("*"),
            index=index or _parse_index(selector),
            show_all_heroes=True,
            analyze=True,
            raw_args=raw_args,
        )

    if head in {"court", "courtroom", "开庭"}:
        if not rest:
            return CommandIntent(name="courtroom", show_all_heroes=True, analyze=True, raw_args=raw_args)
        first = rest[0]
        first_index = _parse_index(first)
        if first_index is not None:
            return CommandIntent(
                name="analysis",
                index=first_index,
                show_all_heroes=True,
                analyze=True,
                raw_args=raw_args,
            )
        selector = rest[1] if len(rest) > 1 else ""
        return CommandIntent(
            name="courtroom",
            bnet_id=first,
            selector=selector.rstrip("*"),
            index=_parse_index(selector) or 1,
            show_all_heroes=True,
            analyze=True,
            raw_args=raw_args,
        )

    if head in {"refresh", "刷新"}:
        bnet_id = rest[0] if rest else ""
        return CommandIntent(name="refresh", bnet_id=bnet_id, refresh=True, raw_args=raw_args)

    if head == "debug" and rest:
        sub = rest[0].lower()
        bnet_id = rest[1] if len(rest) > 1 else ""
        if sub in {"config", "配置", "conf"}:
            return CommandIntent(name="debug_config", raw_args=raw_args)
        if sub in {"ai", "分析", "llm"}:
            return CommandIntent(name="debug_ai", raw_args=raw_args)
        if sub in {"live", "dashen", "接口", "联调"}:
            return CommandIntent(name="debug_live", bnet_id=bnet_id, limit=_parse_limit(rest[2:], None), raw_args=raw_args)
        if sub in {"render", "image", "图片", "图"}:
            index = _parse_index(rest[2]) if len(rest) > 2 else None
            return CommandIntent(name="debug_render", bnet_id=bnet_id, index=index or 1, raw_args=raw_args)
        if sub in {"matches", "战绩", "对局"}:
            return CommandIntent(name="debug_matches", bnet_id=bnet_id, limit=_parse_limit(rest[2:], None), raw_args=raw_args)

    if BATTLE_TAG_RE.match(tokens[0]):
        return CommandIntent(name="profile", bnet_id=tokens[0], raw_args=raw_args)

    return CommandIntent(name="help", raw_args=raw_args)
