from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .constants import DASHEN_ORIGIN, DASHEN_REFERER, DASHEN_USER_AGENT
from .errors import ConfigError


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "get"):
        return value
    return {}


def _get(mapping: Mapping[str, Any], key: str, default: Any = None) -> Any:
    try:
        return mapping.get(key, default)
    except Exception:
        return default


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "启用", "是"}


def _split_paths(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [item.strip() for item in text.split(";") if item.strip()]


@dataclass(frozen=True)
class DashenConfig:
    role_id: int = 0
    token: str = ""
    server: int = 1
    dts: int = 2026
    client_type: str = "60"
    origin: str = DASHEN_ORIGIN
    referer: str = DASHEN_REFERER
    user_agent: str = DASHEN_USER_AGENT
    timeout_seconds: int = 20
    max_concurrent_requests: int = 2
    include_fight: bool = True

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "DashenConfig":
        return cls(
            role_id=_as_int(_get(raw, "role_id", 0), 0),
            token=str(_get(raw, "token", "") or "").strip(),
            server=_as_int(_get(raw, "server", 1), 1),
            dts=_as_int(_get(raw, "dts", 2026), 2026),
            client_type=str(_get(raw, "client_type", "60") or "60").strip(),
            timeout_seconds=max(5, _as_int(_get(raw, "timeout_seconds", 20), 20)),
            max_concurrent_requests=max(1, _as_int(_get(raw, "max_concurrent_requests", 2), 2)),
            include_fight=_as_bool(_get(raw, "include_fight", True), True),
        )

    def validate(self) -> None:
        if self.role_id <= 0 or not self.token:
            raise ConfigError(
                "Dashen 凭据未配置。",
                "请在插件配置里填写 dashen.role_id 和 dashen.token 后再查询。",
            )


@dataclass(frozen=True)
class AiConfig:
    enabled: bool = False
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    timeout_seconds: int = 60

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "AiConfig":
        return cls(
            enabled=_as_bool(_get(raw, "enabled", False), False),
            base_url=str(_get(raw, "base_url", "") or "").strip(),
            api_key=str(_get(raw, "api_key", "") or "").strip(),
            model=str(_get(raw, "model", "") or "").strip(),
            timeout_seconds=max(10, _as_int(_get(raw, "timeout_seconds", 60), 60)),
        )

    @property
    def ready(self) -> bool:
        if not self.enabled:
            return False
        if not self.base_url or not self.api_key:
            return False
        if "replace-with-your" in self.api_key.lower():
            return False
        return True


@dataclass(frozen=True)
class RenderConfig:
    max_bytes: int = 5 * 1024 * 1024
    font_paths: list[str] = field(default_factory=list)
    max_render_files: int = 300

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "RenderConfig":
        return cls(
            max_bytes=max(512 * 1024, _as_int(_get(raw, "max_bytes", 5 * 1024 * 1024), 5 * 1024 * 1024)),
            font_paths=_split_paths(_get(raw, "font_paths", "")),
            max_render_files=max(20, _as_int(_get(raw, "max_render_files", 300), 300)),
        )


@dataclass(frozen=True)
class PluginConfig:
    dashen: DashenConfig = field(default_factory=DashenConfig)
    ai: AiConfig = field(default_factory=AiConfig)
    render: RenderConfig = field(default_factory=RenderConfig)
    storage_dir: str = "data"
    ow_esports_api_key: str = ""
    default_match_limit: int = 10
    debug: bool = False

    @classmethod
    def from_mapping(cls, raw_config: Any) -> "PluginConfig":
        raw = _as_mapping(raw_config)
        return cls(
            dashen=DashenConfig.from_mapping(_as_mapping(_get(raw, "dashen", {}))),
            ai=AiConfig.from_mapping(_as_mapping(_get(raw, "ai", {}))),
            render=RenderConfig.from_mapping(_as_mapping(_get(raw, "render", {}))),
            storage_dir=str(_get(raw, "storage_dir", "data") or "data").strip(),
            ow_esports_api_key=str(_get(raw, "ow_esports_api_key", "") or "").strip(),
            default_match_limit=max(3, min(20, _as_int(_get(raw, "default_match_limit", 10), 10))),
            debug=_as_bool(_get(raw, "debug", False), False),
        )

    def resolve_storage_dir(self, plugin_root: Path) -> Path:
        path = Path(self.storage_dir or "data")
        if not path.is_absolute():
            path = plugin_root / path
        return path
