from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from ..cache.context import ContextCache, ContextKey
from ..clients.dashen import DashenClient
from ..constants import FIGHT_GAME_MODES, NORMAL_GAME_MODES
from ..errors import DashenApiError, NotFoundError
from ..models import MatchDetail, MatchSummary, PlayerIdentity
from .identity import IdentityService
from .match_utils import (
    extract_match_entries,
    get_recent_dashen_seasons,
    is_fight_match_payload,
    iter_dashen_season_request_values,
    merge_unique_match_entries,
)


@dataclass(frozen=True)
class MatchListResult:
    identity: PlayerIdentity
    matches: list[MatchSummary] = field(default_factory=list)
    raw_matches: list[dict[str, Any]] = field(default_factory=list)


class MatchService:
    def __init__(self, client: DashenClient, identity_service: IdentityService, context_cache: ContextCache) -> None:
        self.client = client
        self.identity_service = identity_service
        self.context_cache = context_cache

    async def list_recent_matches(
        self,
        bnet_id: str,
        *,
        context_key: ContextKey | None = None,
        refresh: bool = False,
        limit: int = 10,
        include_fight: bool = True,
    ) -> MatchListResult:
        identity = await self.identity_service.resolve_bnet(bnet_id, refresh=refresh)
        raw_matches = await self._list_for_identity(identity, limit=limit, include_fight=include_fight)
        summaries = [MatchSummary.from_payload(item) for item in raw_matches[:limit]]
        if context_key is not None:
            self.context_cache.set(
                context_key,
                {
                    "identity": identity.to_cache(),
                    "matches_raw": [item.raw for item in summaries],
                },
            )
        return MatchListResult(identity=identity, matches=summaries, raw_matches=[item.raw for item in summaries])

    async def detail_by_context_index(self, context_key: ContextKey, index: int) -> MatchDetail:
        context = self.context_cache.get(context_key)
        if not context:
            raise NotFoundError("没有可用的上一条战绩列表。", "请先发送 /ow 战绩 玩家#12345，再用 /ow 详情 1。")
        identity = PlayerIdentity.from_cache(context.get("identity") or {})
        raw_matches = [item for item in context.get("matches_raw") or [] if isinstance(item, dict)]
        return await self.detail_by_index(identity, raw_matches, index)

    async def detail_for_bnet_selector(
        self,
        bnet_id: str,
        *,
        index: int | None = None,
        selector: str = "",
        include_fight: bool = True,
    ) -> MatchDetail:
        identity = await self.identity_service.resolve_bnet(bnet_id)
        if index is not None:
            raw_matches = await self._list_for_identity(identity, limit=max(10, index), include_fight=include_fight)
            return await self.detail_by_index(identity, raw_matches, index)
        match_id = str(selector or "").strip()
        if not match_id:
            raise NotFoundError("缺少单局序号或 matchId。", "示例：/ow 详情 玩家#12345 1")
        return await self.detail_by_match_id(identity, match_id)

    async def detail_by_index(self, identity: PlayerIdentity, raw_matches: list[dict[str, Any]], index: int) -> MatchDetail:
        if index <= 0:
            raise NotFoundError("单局序号需要从 1 开始。")
        offset = index - 1
        if offset >= len(raw_matches):
            raise NotFoundError(f"没有第 {index} 场记录。", f"当前缓存/列表里只有 {len(raw_matches)} 场。")
        source_match = dict(raw_matches[offset])
        return await self._fetch_detail(identity, source_match)

    async def detail_by_match_id(self, identity: PlayerIdentity, match_id: str) -> MatchDetail:
        source_match = {"matchId": str(match_id)}
        try:
            return await self._fetch_detail(identity, source_match)
        except DashenApiError:
            fight_payload = await self.client.fight_query_match_info(identity.customer_token, match_id)
            source_match["gameMode"] = "SportFight"
            return self._build_detail(identity, source_match, fight_payload, match_kind="fight")

    async def latest_analyzable_detail(
        self,
        bnet_id: str,
        *,
        context_key: ContextKey | None = None,
        index: int = 1,
    ) -> MatchDetail:
        if index <= 0:
            raise NotFoundError("单局序号需要从 1 开始。")
        identity = await self.identity_service.resolve_bnet(bnet_id)
        raw_matches = await self._list_for_identity(identity, limit=20, include_fight=False)
        raw_matches = [item for item in raw_matches if not is_fight_match_payload(item)]
        if not raw_matches:
            raise NotFoundError("没有找到可分析的快速/竞技对局。", "角斗模式暂不支持全员数据和 AI 分析。")
        if index > len(raw_matches):
            raise NotFoundError(f"没有第 {index} 场可分析对局。", f"当前最近列表里只有 {len(raw_matches)} 场快速/竞技对局。")
        if context_key is not None:
            self.context_cache.set(
                context_key,
                {
                    "identity": identity.to_cache(),
                    "matches_raw": raw_matches,
                },
            )
        return await self._fetch_detail(identity, raw_matches[index - 1])

    async def _list_for_identity(self, identity: PlayerIdentity, *, limit: int, include_fight: bool) -> list[dict[str, Any]]:
        limit = max(1, min(20, int(limit)))
        matches: list[dict[str, Any]] = []
        first_error: Exception | None = None
        for logical_season in get_recent_dashen_seasons(include_previous=True):
            season_matches: list[dict[str, Any]] = []
            for request_season in iter_dashen_season_request_values(logical_season):
                try:
                    payloads = await self._fetch_recent_payloads(identity.customer_token, request_season, include_fight=include_fight)
                except Exception as exc:
                    first_error = first_error or exc
                    continue
                for payload, default_game_mode in payloads:
                    for match in extract_match_entries(payload, "matchList", "recentMatchList"):
                        item = dict(match)
                        item.setdefault("gameMode", default_game_mode)
                        item["_dashenSeason"] = logical_season
                        season_matches.append(item)
                if season_matches:
                    break
            matches = merge_unique_match_entries(matches, season_matches)
            if len(matches) >= limit:
                break
        if not matches and first_error:
            raise first_error
        return matches[:limit]

    async def _fetch_recent_payloads(
        self,
        customer_token: str,
        season: int | None,
        *,
        include_fight: bool,
    ) -> list[tuple[dict[str, Any], str]]:
        task_specs: list[tuple[asyncio.Future, str]] = []
        for mode in NORMAL_GAME_MODES:
            task_specs.append((asyncio.ensure_future(self.client.query_count_info(customer_token, mode, season=season)), mode))
            task_specs.append((asyncio.ensure_future(self.client.query_match_list(customer_token, mode, page=1, season=season)), mode))
            task_specs.append((asyncio.ensure_future(self.client.query_match_list(customer_token, mode, page=2, season=season)), mode))
        if include_fight:
            for mode in FIGHT_GAME_MODES:
                task_specs.append((asyncio.ensure_future(self.client.fight_query_match_list(customer_token, mode, page=1, season=season)), mode))
        results = await asyncio.gather(*(task for task, _ in task_specs), return_exceptions=True)
        payloads: list[tuple[dict[str, Any], str]] = []
        first_error: Exception | None = None
        for result, (_, mode) in zip(results, task_specs):
            if isinstance(result, Exception):
                first_error = first_error or result
                continue
            if isinstance(result, dict):
                payloads.append((result, mode))
        if not payloads and first_error:
            raise first_error
        return payloads

    async def _fetch_detail(self, identity: PlayerIdentity, source_match: dict[str, Any]) -> MatchDetail:
        match_id = str(source_match.get("matchId") or source_match.get("match_id") or "").strip()
        if not match_id:
            raise NotFoundError("这条战绩没有 matchId，无法查询详情。")
        if is_fight_match_payload(source_match):
            payload = await self.client.fight_query_match_info(identity.customer_token, match_id)
            return self._build_detail(identity, source_match, payload, match_kind="fight")
        payload = await self.client.query_match_info(identity.customer_token, match_id)
        return self._build_detail(identity, source_match, payload, match_kind="normal")

    @staticmethod
    def _build_detail(
        identity: PlayerIdentity,
        source_match: dict[str, Any],
        payload: dict[str, Any],
        *,
        match_kind: str,
    ) -> MatchDetail:
        summary_source = dict(source_match)
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        for key in ("matchRet", "mapGuid", "gameTimeSec", "startTime", "teamScore", "opponentScore"):
            if key not in summary_source and key in data:
                summary_source[key] = data[key]
        summary = MatchSummary.from_payload(summary_source)
        return MatchDetail(
            identity=identity,
            summary=summary,
            payload=payload,
            source_match=dict(source_match),
            match_kind="fight" if match_kind == "fight" else "normal",
        )
