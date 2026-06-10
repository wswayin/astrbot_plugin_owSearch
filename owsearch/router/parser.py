from __future__ import annotations

import re
import shlex

from .intents import CommandIntent


COMMAND_PREFIX_RE = re.compile(r"^\s*/?(ow|守望)\b", re.IGNORECASE)
BATTLE_TAG_RE = re.compile(r"^[^\s#]+#\d{3,}$")
UUIDISH_RE = re.compile(r"^[0-9a-fA-F-]{16,}$")


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


def parse_command(message: str) -> CommandIntent:
    raw_args = _strip_command(message)
    tokens = _split_args(raw_args)
    if not tokens:
        return CommandIntent(name="help", raw_args=raw_args)

    head = tokens[0].lower()
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
        bnet_id = rest[0] if rest else ""
        return CommandIntent(name="courtroom", bnet_id=bnet_id, show_all_heroes=True, analyze=True, raw_args=raw_args)

    if head in {"refresh", "刷新"}:
        bnet_id = rest[0] if rest else ""
        return CommandIntent(name="refresh", bnet_id=bnet_id, refresh=True, raw_args=raw_args)

    if head == "debug" and rest:
        sub = rest[0].lower()
        bnet_id = rest[1] if len(rest) > 1 else ""
        if sub in {"config", "配置", "conf"}:
            return CommandIntent(name="debug_config", raw_args=raw_args)
        if sub in {"live", "dashen", "接口", "联调"}:
            return CommandIntent(name="debug_live", bnet_id=bnet_id, limit=_parse_limit(rest[2:], None), raw_args=raw_args)
        if sub in {"render", "image", "图片", "图"}:
            return CommandIntent(name="debug_render", raw_args=raw_args)
        if sub in {"matches", "战绩", "对局"}:
            return CommandIntent(name="debug_matches", bnet_id=bnet_id, limit=_parse_limit(rest[2:], None), raw_args=raw_args)

    if BATTLE_TAG_RE.match(tokens[0]):
        return CommandIntent(name="profile", bnet_id=tokens[0], raw_args=raw_args)

    return CommandIntent(name="help", raw_args=raw_args)
