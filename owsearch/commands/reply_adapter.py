from __future__ import annotations

from typing import Any

from ..cache.context import ContextKey


def _call_first(obj: Any, names: tuple[str, ...]) -> str:
    for name in names:
        attr = getattr(obj, name, None)
        if callable(attr):
            try:
                value = attr()
            except TypeError:
                continue
            if value:
                return str(value)
        elif attr:
            return str(attr)
    return ""


def context_key_from_event(event: Any) -> ContextKey:
    platform = _call_first(event, ("get_platform_name", "platform_name", "platform")) or "unknown"
    session = _call_first(event, ("get_group_id", "get_session_id", "session_id", "group_id")) or "private"
    user = _call_first(event, ("get_sender_id", "sender_id", "user_id", "get_sender_name")) or "unknown"
    origin = getattr(event, "unified_msg_origin", None)
    if origin and session == "private":
        session = str(origin)
    return ContextKey(platform=platform, session=session, user=user)


def message_text_from_event(event: Any) -> str:
    for name in ("message_str", "message", "text"):
        value = getattr(event, name, None)
        if value:
            return str(value)
    getter = getattr(event, "get_message_str", None)
    if callable(getter):
        try:
            return str(getter())
        except Exception:
            return ""
    return ""
