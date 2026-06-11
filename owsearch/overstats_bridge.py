from __future__ import annotations

import base64
import importlib
from pathlib import Path
from typing import Any

from overstats.config import DashenClientConfig, DashenCredentialConfig
from overstats.config import config as overstats_config
from overstats.src.client import apiclient as overstats_api
from overstats.src.client.apiclient import DashenAPIClient
from overstats.src.modules.bnet_search import BnetSearchModule
from overstats.src.modules.dashen_match import DashenMatchModule, DashenMatchQuery, DashenMatchRequests
from overstats.src.modules.dashen_match.render import RenderedImage
from overstats.src.modules.dashen_competitive_strength import (
    DashenCompetitiveStrengthModule,
    DashenCompetitiveStrengthQuery,
)
from overstats.src.modules.dashen_profile import DashenProfileModule, DashenProfileQuery
from overstats.src.modules.dashen_quick_strength import DashenQuickStrengthModule, DashenQuickStrengthQuery
from overstats.src.modules.dashen_rank_history import DashenRankHistoryModule, DashenRankHistoryQuery
from overstats.src.modules.dashen_rank_leaderboard import (
    DashenRankLeaderboardModule,
    DashenRankLeaderboardQuery,
    DashenRankLeaderboardRequests,
)
from overstats.src.modules.dashen_hero_leaderboard import (
    DashenHeroLeaderboardModule,
    DashenHeroLeaderboardQuery,
    DashenHeroLeaderboardRequests,
)
from overstats.src.modules.dashen_hero_treemap import DashenHeroTreemapModule, DashenHeroTreemapQuery
from overstats.src.modules.dashen_sameplay import DashenSameplayModule, DashenSameplayQuery
from overstats.src.modules.dashen_summary import DashenSummaryModule, DashenSummaryQuery
from overstats.src.modules.errors import ModuleError
from overstats.src.modules.ow_hero_pick_rate import OWHeroPickRateModule, OWHeroPickRateQuery
from overstats.src.modules.ow_hero_wiki import OWHeroWikiModule, OWHeroWikiQuery
from overstats.src.modules.ow_shop import OWShopModule
from overstats.src.modules.ow_esports import OWEsportsModule, OWEsportsRequests
from overstats.src.modules.patch_notes import PatchNotesModule
from overstats.src.modules.player_identity_search import PlayerIdentitySearchModule, PlayerIdentitySearchQuery

from .config import PluginConfig
from .errors import OwSearchError
from .models import ReplyItem
from .renderers import cleanup_render_dir, save_image_bytes


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_ANALYSIS_PERSONA_PROMPT = str(getattr(overstats_config, "ANALYSIS_PERSONA_PROMPT", "") or "")


def _int_or_default(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _module_error_to_owsearch(exc: ModuleError, *, requested_index: int | None = None) -> OwSearchError:
    details = dict(exc.details or {})
    if exc.error == "match_index_out_of_range":
        match_count = _int_or_default(details.get("match_count"), 0)
        internal_index = _int_or_default(details.get("index"), 0)
        display_index = int(requested_index) if requested_index is not None else internal_index + 1
        if match_count <= 0:
            return OwSearchError(
                "没有找到可用的最近对局。",
                "大神接口本次返回 0 条可用于详情/开庭的对局。请确认玩家公开战绩、Dashen role/token 未过期，或先用 /ow 战绩 玩家#12345 查看列表。",
                code=exc.error,
                details=details,
            )
        return OwSearchError(
            f"可用对局只有 {match_count} 场，无法查询第 {display_index} 场。",
            f"请改用 1 到 {match_count} 之间的数字，例如 /ow 开庭 玩家#12345 1。",
            code=exc.error,
            details=details,
        )
    return OwSearchError(exc.message, exc.hint, code=exc.error, details=details)


class OverstatsBridge:
    def __init__(self, config: PluginConfig, data_dir: Path) -> None:
        self.config = config
        self.data_dir = data_dir
        self.render_dir = data_dir / "renders"
        self.client = self._build_client()
        self._patch_overstats_global_client()
        self.search_module = BnetSearchModule(self.client)
        self.match_module = DashenMatchModule(api_client=self.client, search_module=self.search_module)
        self.profile_module = DashenProfileModule(api_client=self.client, search_module=self.search_module)
        self.sameplay_module = DashenSameplayModule(requests=DashenMatchRequests(self.client))
        self.sameplay_module.match_module = self.match_module
        self.summary_module = DashenSummaryModule(search_module=self.search_module)
        self.quick_strength_module = DashenQuickStrengthModule(api_client=self.client, search_module=self.search_module)
        self.competitive_strength_module = DashenCompetitiveStrengthModule(
            api_client=self.client,
            search_module=self.search_module,
        )
        self.rank_history_module = DashenRankHistoryModule(api_client=self.client, search_module=self.search_module)
        self.rank_leaderboard_module = DashenRankLeaderboardModule(
            requests=DashenRankLeaderboardRequests(self.client),
        )
        self.hero_leaderboard_module = DashenHeroLeaderboardModule(
            requests=DashenHeroLeaderboardRequests(self.client),
        )
        self.hero_treemap_module = DashenHeroTreemapModule(api_client=self.client, search_module=self.search_module)
        self.hero_pick_rate_module = OWHeroPickRateModule()
        self.hero_wiki_module = OWHeroWikiModule()
        self.shop_module = OWShopModule(cache_root=data_dir / "overstats_cache" / "ow_shop")
        self.patch_notes_module = PatchNotesModule(cache_root=data_dir / "overstats_cache" / "patch_notes")
        self.esports_module = OWEsportsModule(requests=OWEsportsRequests(self.client))
        self.identity_search_module = PlayerIdentitySearchModule()

    def _build_client(self) -> DashenAPIClient:
        dashen = self.config.dashen
        client_config = DashenClientConfig(
            accounts=(
                DashenCredentialConfig(
                    name="astrbot-1",
                    role_id=int(dashen.role_id or 0),
                    token=str(dashen.token or ""),
                    dts=int(dashen.dts or 2026),
                    server=int(dashen.server or 1),
                ),
            ),
            bigdata_dts=int(dashen.dts or 2026),
            account_max_requests_per_second=5,
            account_rate_limit_window_seconds=1.0,
            client_type=str(dashen.client_type or "60"),
            origin=str(dashen.origin or "https://act.ds.163.com"),
            referer=str(dashen.referer or "https://act.ds.163.com/"),
            user_agent=str(dashen.user_agent or ""),
            account_failure_cooldown_seconds=60,
            international_proxy="",
            netease_proxies=(None,),
            ow_esports_api_key=str(self.config.ow_esports_api_key or ""),
        )
        self._patch_overstats_dashen_runtime()
        return DashenAPIClient(client_config=client_config)

    def _patch_overstats_dashen_runtime(self) -> None:
        dashen = self.config.dashen
        overstats_api.DASHEN_BIGDATA_DTS = int(dashen.dts or 2026)
        overstats_api.DASHEN_CLIENT_TYPE = str(dashen.client_type or "60")
        overstats_api.DASHEN_ORIGIN = str(dashen.origin or "https://act.ds.163.com")
        overstats_api.DASHEN_REFERER = str(dashen.referer or "https://act.ds.163.com/")
        overstats_api.DASHEN_USER_AGENT = str(dashen.user_agent or "")
        overstats_config.OW_ESPORTS_API_KEY = str(self.config.ow_esports_api_key or "")
        overstats_api.OW_ESPORTS_API_KEY = str(self.config.ow_esports_api_key or "")
        overstats_api.OW_ESPORTS_HEADERS = overstats_api._build_ow_esports_headers(self.config.ow_esports_api_key)

    def _patch_overstats_global_client(self) -> None:
        overstats_api.dashen_api_client = self.client
        overstats_api.http_client = self.client.netease_client
        overstats_api.http_client_with_proxy = self.client.proxy_client
        for module_name in (
            "overstats.src.modules.dashen_summary.engine",
            "overstats.src.modules.dashen_summary.runtime.dashen",
            "overstats.src.modules.dashen_summary.runtime.season_conclusion",
        ):
            try:
                module = importlib.import_module(module_name)
            except ModuleNotFoundError:
                continue
            if hasattr(module, "dashen_api_client"):
                setattr(module, "dashen_api_client", self.client)

    def _patch_overstats_analysis_runtime(self) -> None:
        ai = self.config.ai
        overstats_config.ANALYSIS_BASE_URL = str(ai.base_url or "")
        overstats_config.ANALYSIS_API_KEY = str(ai.api_key or "")
        overstats_config.ANALYSIS_PERSONA_PROMPT = ORIGINAL_ANALYSIS_PERSONA_PROMPT
        if ai.model:
            overstats_config.ANALYSIS_OPENAI_MODEL = ai.model
            overstats_config.ANALYSIS_DEEPSEEK_MODEL = ai.model
            overstats_config.ANALYSIS_GOOGLE_MODEL = ai.model

    async def close(self) -> None:
        await self.client.aclose()

    async def courtroom(self, bnet_id: str, *, index: int = 1) -> list[ReplyItem]:
        self.config.dashen.validate()
        self._patch_overstats_analysis_runtime()
        one_based_index = max(1, int(index or 1))
        query = DashenMatchQuery(
            bnet_id=bnet_id,
            include_fight=False,
            target_count=max(20, one_based_index),
        )
        try:
            output = await self.match_module.query_match_detail_replies(
                query=query,
                index=one_based_index - 1,
                show_all_heroes=True,
                analyze=True,
            )
        except ModuleError as exc:
            raise _module_error_to_owsearch(exc, requested_index=one_based_index) from exc
        return self._reply_items_from_overstats(output.replies, prefix="overstats_court")

    async def match_list(self, bnet_id: str, *, limit: int = 10, include_fight: bool = True) -> list[ReplyItem]:
        self.config.dashen.validate()
        query = DashenMatchQuery(
            bnet_id=bnet_id,
            include_fight=include_fight,
            target_count=max(1, min(20, int(limit or 10))),
        )
        try:
            output = await self.match_module.query_match_list(query, render=True)
        except ModuleError as exc:
            raise OwSearchError(exc.message, exc.hint, code=exc.error, details=exc.details) from exc
        if output.image is None:
            return [ReplyItem.text("没有生成战绩列表图片。")]
        return [self._reply_item_from_rendered(output.image, prefix="overstats_matches")]

    async def profile(self, bnet_id: str) -> list[ReplyItem]:
        self.config.dashen.validate()
        try:
            output = await self.profile_module.query_profile_image(
                DashenProfileQuery(bnet_id=bnet_id),
                render_mode="quick",
            )
        except ModuleError as exc:
            raise OwSearchError(exc.message, exc.hint, code=exc.error, details=exc.details) from exc
        if output.image is None:
            return [ReplyItem.text("没有生成玩家资料图片。")]
        return [self._reply_item_from_rendered(output.image, prefix="overstats_profile")]

    async def match_detail(
        self,
        bnet_id: str,
        *,
        index: int = 1,
        show_all_heroes: bool = False,
        analyze: bool = False,
        include_fight: bool = True,
    ) -> list[ReplyItem]:
        self.config.dashen.validate()
        self._patch_overstats_analysis_runtime()
        one_based_index = max(1, int(index or 1))
        query = DashenMatchQuery(
            bnet_id=bnet_id,
            include_fight=include_fight,
            target_count=max(20, one_based_index),
        )
        try:
            output = await self.match_module.query_match_detail_replies(
                query=query,
                index=one_based_index - 1,
                show_all_heroes=show_all_heroes,
                analyze=analyze,
            )
        except ModuleError as exc:
            raise _module_error_to_owsearch(exc, requested_index=one_based_index) from exc
        return self._reply_items_from_overstats(output.replies, prefix="overstats_detail")

    async def sameplay_list(self, player1_bnet_id: str, player2_bnet_id: str, *, limit: int = 20) -> list[ReplyItem]:
        self.config.dashen.validate()
        query = DashenSameplayQuery(
            player1_bnet_id=player1_bnet_id,
            player2_bnet_id=player2_bnet_id,
            limit=max(1, min(40, int(limit or 20))),
        )
        try:
            output = await self.sameplay_module.query_sameplay_list_replies(query)
        except ModuleError as exc:
            raise OwSearchError(exc.message, exc.hint, code=exc.error, details=exc.details) from exc
        return self._reply_items_from_overstats(output.replies, prefix="overstats_sameplay")

    async def sameplay_detail(
        self,
        player1_bnet_id: str,
        player2_bnet_id: str,
        *,
        index: int = 1,
        show_all_heroes: bool = False,
        analyze: bool = False,
    ) -> list[ReplyItem]:
        self.config.dashen.validate()
        self._patch_overstats_analysis_runtime()
        one_based_index = max(1, int(index or 1))
        query = DashenSameplayQuery(
            player1_bnet_id=player1_bnet_id,
            player2_bnet_id=player2_bnet_id,
            limit=max(20, one_based_index),
        )
        try:
            output = await self.sameplay_module.query_sameplay_detail_replies(
                query,
                index=one_based_index - 1,
                show_all_heroes=show_all_heroes,
                analyze=analyze,
            )
        except ModuleError as exc:
            raise _module_error_to_owsearch(exc, requested_index=one_based_index) from exc
        return self._reply_items_from_overstats(output.replies, prefix="overstats_sameplay_detail")

    async def summary(self, bnet_id: str, *, scope: str = "today") -> list[ReplyItem]:
        self.config.dashen.validate()
        self._patch_overstats_global_client()
        query = DashenSummaryQuery(bnet_id=bnet_id, scope=scope or "today")
        try:
            output = await self.summary_module.query_summary(query)
        except ModuleError as exc:
            raise OwSearchError(exc.message, exc.hint, code=exc.error, details=exc.details) from exc
        rendered = RenderedImage(content=output.image_bytes, media_type=output.image_media_type)
        return [self._reply_item_from_rendered(rendered, prefix=f"overstats_summary_{output.scope}")]

    async def quick_strength(self, bnet_id: str, *, limit: int = 12) -> list[ReplyItem]:
        self.config.dashen.validate()
        query = DashenQuickStrengthQuery(bnet_id=bnet_id, limit=max(1, min(20, int(limit or 12))))
        try:
            output = await self.quick_strength_module.query_quick_strength(query, render=True)
        except ModuleError as exc:
            raise OwSearchError(exc.message, exc.hint, code=exc.error, details=exc.details) from exc
        if output.image is None:
            return [ReplyItem.text("没有生成快速强度图片。")]
        return [self._reply_item_from_rendered(output.image, prefix="overstats_quick_strength")]

    async def competitive_strength(self, bnet_id: str, *, limit: int = 12) -> list[ReplyItem]:
        self.config.dashen.validate()
        query = DashenCompetitiveStrengthQuery(bnet_id=bnet_id, limit=max(1, min(20, int(limit or 12))))
        try:
            output = await self.competitive_strength_module.query_competitive_strength(query, render=True)
        except ModuleError as exc:
            raise OwSearchError(exc.message, exc.hint, code=exc.error, details=exc.details) from exc
        if output.image is None:
            return [ReplyItem.text("没有生成竞技强度图片。")]
        return [self._reply_item_from_rendered(output.image, prefix="overstats_competitive_strength")]

    async def rank_history(
        self,
        bnet_id: str,
        *,
        start_season: int | None = None,
        end_season: int | None = None,
    ) -> list[ReplyItem]:
        self.config.dashen.validate()
        query = DashenRankHistoryQuery(
            bnet_id=bnet_id,
            start_season=start_season,
            end_season=end_season,
        )
        try:
            output = await self.rank_history_module.query_rank_history(query, render=True)
        except ModuleError as exc:
            raise OwSearchError(exc.message, exc.hint, code=exc.error, details=exc.details) from exc
        if output.image is None:
            return [ReplyItem.text("没有生成段位历史图片。")]
        return [self._reply_item_from_rendered(output.image, prefix="overstats_rank_history")]

    async def rank_leaderboard(self, province: str, role: str) -> list[ReplyItem]:
        self.config.dashen.validate()
        query = DashenRankLeaderboardQuery(province=province, role=role)
        try:
            output = await self.rank_leaderboard_module.query_rank_leaderboard(query, render=True)
        except ModuleError as exc:
            raise OwSearchError(exc.message, exc.hint, code=exc.error, details=exc.details) from exc
        if output.image is None:
            return [ReplyItem.text("没有生成省榜图片。")]
        return [self._reply_item_from_rendered(output.image, prefix="overstats_rank_leaderboard")]

    async def hero_leaderboard(self, province: str, hero: str, *, mode: str = "preset") -> list[ReplyItem]:
        self.config.dashen.validate()
        query = DashenHeroLeaderboardQuery(province=province, hero=hero, mode=mode or "preset")
        try:
            output = await self.hero_leaderboard_module.query_hero_leaderboard(query, render=True)
        except ModuleError as exc:
            raise OwSearchError(exc.message, exc.hint, code=exc.error, details=exc.details) from exc
        if output.image is None:
            return [ReplyItem.text("没有生成英雄榜图片。")]
        return [self._reply_item_from_rendered(output.image, prefix="overstats_hero_leaderboard")]

    async def hero_treemap(self, bnet_id: str, *, mode: str = "competitive", season: int | None = None) -> list[ReplyItem]:
        self.config.dashen.validate()
        query = DashenHeroTreemapQuery(bnet_id=bnet_id, mode=mode or "competitive", season=season)
        try:
            output = await self.hero_treemap_module.query_treemap(query, render=True)
        except ModuleError as exc:
            raise OwSearchError(exc.message, exc.hint, code=exc.error, details=exc.details) from exc
        if output.image is None:
            return [ReplyItem.text("没有生成英雄占比图片。")]
        return [self._reply_item_from_rendered(output.image, prefix="overstats_hero_treemap")]

    async def hero_pick_rate(
        self,
        *,
        view: str = "ranking",
        mode: str = "quick",
        mmr: str = "all",
        hero: str = "",
        history_limit: int | None = None,
    ) -> list[ReplyItem]:
        query = OWHeroPickRateQuery(
            view=view or "ranking",
            game_mode=mode or "quick",
            mmr=mmr or "all",
            hero=hero,
            history_limit=history_limit or 20,
        )
        try:
            output = await self.hero_pick_rate_module.query_pick_rate(query, render=True)
        except ModuleError as exc:
            raise OwSearchError(exc.message, exc.hint, code=exc.error, details=exc.details) from exc
        if output.image is None:
            return [ReplyItem.text("没有生成英雄登场率图片。")]
        return [self._reply_item_from_rendered(output.image, prefix="overstats_hero_pick_rate")]

    async def hero_wiki(self, hero: str, *, question: str = "") -> list[ReplyItem]:
        self._patch_overstats_analysis_runtime()
        query = OWHeroWikiQuery(hero=hero, question=question)
        try:
            output = await self.hero_wiki_module.query_hero(query, render=True)
        except ModuleError as exc:
            raise OwSearchError(exc.message, exc.hint, code=exc.error, details=exc.details) from exc
        if output.image is None:
            return [ReplyItem.text("没有生成英雄资料图片。")]
        return [self._reply_item_from_rendered(output.image, prefix="overstats_hero_wiki")]

    async def shop(self) -> list[ReplyItem]:
        try:
            output = await self.shop_module.query_shop(render=True)
        except ModuleError as exc:
            raise OwSearchError(exc.message, exc.hint, code=exc.error, details=exc.details) from exc
        if output.image is None:
            return [ReplyItem.text("没有生成商店图片。")]
        return [self._reply_item_from_rendered(output.image, prefix="overstats_shop")]

    async def patch_notes(self, *, patch_kind: str = "latest") -> list[ReplyItem]:
        self._patch_overstats_analysis_runtime()
        try:
            output = await self.patch_notes_module.query_patch_notes(patch_kind=patch_kind or "latest", render=True)
        except ModuleError as exc:
            raise OwSearchError(exc.message, exc.hint, code=exc.error, details=exc.details) from exc
        if output.image is None:
            return [ReplyItem.text("没有生成补丁说明图片。")]
        return [self._reply_item_from_rendered(output.image, prefix="overstats_patch_notes")]

    async def esports(self) -> list[ReplyItem]:
        self._patch_overstats_dashen_runtime()
        try:
            output = await self.esports_module.query_ow_esports(render=True)
        except ModuleError as exc:
            raise OwSearchError(exc.message, exc.hint, code=exc.error, details=exc.details) from exc
        if output.image is None:
            return [ReplyItem.text("没有生成电竞赛程图片。")]
        return [self._reply_item_from_rendered(output.image, prefix="overstats_esports")]

    async def identity_search(self, bnet_id: str, *, limit: int = 10) -> list[ReplyItem]:
        query = PlayerIdentitySearchQuery(bnet_id=bnet_id, limit=max(1, min(50, int(limit or 10))))
        try:
            output = await self.identity_search_module.search(query)
        except ModuleError as exc:
            raise OwSearchError(exc.message, exc.hint, code=exc.error, details=exc.details) from exc
        if not output.matches:
            return [ReplyItem.text(f"未找到 bnet_id={query.bnet_id} 的本地身份记录。")]
        lines = [f"本地身份反查：{query.bnet_id}"]
        for index, item in enumerate(output.matches, start=1):
            tag = item.battletag or f"{item.battlename}#{item.battlenum}".strip("#")
            lines.append(f"{index}. {tag or '-'} / bnet_id={item.bnet_id} / {item.match_type}")
        return [ReplyItem.text("\n".join(lines))]

    def _reply_item_from_rendered(self, rendered: RenderedImage, *, prefix: str) -> ReplyItem:
        saved = save_image_bytes(
            rendered.content,
            self.render_dir,
            prefix=prefix,
            media_type=rendered.media_type,
        )
        cleanup_render_dir(self.render_dir, max_files=self.config.render.max_render_files)
        return ReplyItem.image(str(saved.path), saved.media_type)

    def _reply_items_from_overstats(self, replies: list[dict[str, Any]], *, prefix: str) -> list[ReplyItem]:
        result: list[ReplyItem] = []
        for index, reply in enumerate(replies or [], start=1):
            kind = str(reply.get("type") or "").lower()
            if kind == "image":
                encoded = str(reply.get("base64") or "")
                if not encoded:
                    continue
                data = base64.b64decode(encoded)
                rendered = RenderedImage(content=data, media_type=str(reply.get("media_type") or "image/png"))
                result.append(self._reply_item_from_rendered(rendered, prefix=f"{prefix}_{index}"))
                continue
            if kind == "text":
                text = str(reply.get("data") or "").strip()
                if text:
                    result.append(ReplyItem.text(text))
        return result
