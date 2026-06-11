from __future__ import annotations

from pathlib import Path
import sys

PLUGIN_ROOT = Path(__file__).resolve().parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

try:
    from astrbot.api.event import AstrMessageEvent, filter
except ImportError:
    from astrbot.api.event import AstrBotEvent as AstrMessageEvent, filter
if not hasattr(filter, "llm_tool"):
    def _noop_llm_tool(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    filter.llm_tool = _noop_llm_tool
from astrbot.api.star import Context, Star, register

from owsearch.commands.handler import OwCommandHandler
from owsearch.commands.reply_adapter import context_key_from_event, message_text_from_event
from owsearch.config import PluginConfig
from owsearch.models import ReplyItem


@register("astrbot_plugin_owSearch", "wswayin", "Overwatch player and match search through Dashen data.", "0.3.4")
class OwSearchPlugin(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.plugin_config = PluginConfig.from_mapping(config or {})
        data_dir = self.plugin_config.resolve_storage_dir(PLUGIN_ROOT)
        self.handler = OwCommandHandler(self.plugin_config, data_dir)

    @filter.command("ow", alias={"守望"})
    async def ow(self, event: AstrMessageEvent):
        message = message_text_from_event(event)
        context_key = context_key_from_event(event)
        replies = await self.handler.handle(message, context_key)
        for reply in replies:
            yield self._to_astrbot_result(event, reply)

    @filter.command("开庭")
    async def courtroom(self, event: AstrMessageEvent):
        message = message_text_from_event(event)
        stripped = str(message or "").strip()
        normalized = stripped[1:] if stripped.startswith("/") else stripped
        if normalized.startswith("开庭"):
            message = f"/ow {normalized}"
        else:
            message = f"/ow 开庭 {stripped}"
        context_key = context_key_from_event(event)
        replies = await self.handler.handle(message, context_key)
        for reply in replies:
            yield self._to_astrbot_result(event, reply)

    def _to_astrbot_result(self, event: AstrMessageEvent, reply: ReplyItem):
        if reply.kind == "image" and reply.path:
            return event.image_result(reply.path)
        return event.plain_result(reply.content)

    def _reply_results(self, event: AstrMessageEvent, replies: list[ReplyItem]):
        for reply in replies:
            yield self._to_astrbot_result(event, reply)

    @filter.llm_tool(name="ow_player_profile")
    async def ow_player_profile(self, event: AstrMessageEvent, player_id: str):
        '''查询守望先锋玩家资料概览。

        Args:
            player_id(string): 玩家 BattleTag，例如 Player#12345。
        '''
        replies = await self.handler.overstats_bridge.profile(player_id)
        for result in self._reply_results(event, replies):
            yield result

    @filter.llm_tool(name="ow_match_list")
    async def ow_match_list(self, event: AstrMessageEvent, player_id: str, limit: int = 10):
        '''查询守望先锋玩家最近对局列表。

        Args:
            player_id(string): 玩家 BattleTag，例如 Player#12345。
            limit(number): 返回最近多少场，默认 10，最大 20。
        '''
        replies = await self.handler.overstats_bridge.match_list(
            player_id,
            limit=limit or self.plugin_config.default_match_limit,
            include_fight=self.plugin_config.dashen.include_fight,
        )
        self.handler.context_cache.set(
            context_key_from_event(event),
            {"overstats_context": "match_list", "bnet_id": player_id},
        )
        for result in self._reply_results(event, replies):
            yield result

    @filter.llm_tool(name="ow_match_detail")
    async def ow_match_detail(
        self,
        event: AstrMessageEvent,
        player_id: str,
        index: int = 1,
        show_all_heroes: bool = False,
        analyze: bool = False,
    ):
        '''查询守望先锋玩家最近第 N 场对局详情。

        Args:
            player_id(string): 玩家 BattleTag，例如 Player#12345。
            index(number): 最近第几场，1 表示最近一场。
            show_all_heroes(boolean): 是否返回全员数据图。
            analyze(boolean): 是否生成 AI 分析图；为 true 时也会返回全员数据图。
        '''
        replies = await self.handler.overstats_bridge.match_detail(
            player_id,
            index=max(1, int(index or 1)),
            show_all_heroes=bool(show_all_heroes or analyze),
            analyze=bool(analyze),
            include_fight=self.plugin_config.dashen.include_fight,
        )
        for result in self._reply_results(event, replies):
            yield result

    @filter.llm_tool(name="ow_courtroom")
    async def ow_courtroom(self, event: AstrMessageEvent, player_id: str, index: int = 1):
        '''开庭分析守望先锋玩家最近第 N 场可分析对局，返回战绩图、全员数据图和 AI 分析图。

        Args:
            player_id(string): 玩家 BattleTag，例如 Player#12345。
            index(number): 最近第几场可分析对局，1 表示最近一场。
        '''
        replies = await self.handler.overstats_bridge.courtroom(player_id, index=max(1, int(index or 1)))
        for result in self._reply_results(event, replies):
            yield result

    @filter.llm_tool(name="ow_sameplay")
    async def ow_sameplay(self, event: AstrMessageEvent, player1_id: str, player2_id: str, limit: int = 20):
        '''查询两个守望先锋玩家的同玩对局列表。

        Args:
            player1_id(string): 第一个玩家 BattleTag。
            player2_id(string): 第二个玩家 BattleTag。
            limit(number): 返回最近多少场同玩对局。
        '''
        replies = await self.handler.overstats_bridge.sameplay_list(player1_id, player2_id, limit=limit or 20)
        self.handler.context_cache.set(
            context_key_from_event(event),
            {
                "overstats_context": "sameplay_list",
                "player1_bnet_id": player1_id,
                "player2_bnet_id": player2_id,
            },
        )
        for result in self._reply_results(event, replies):
            yield result

    @filter.llm_tool(name="ow_sameplay_courtroom")
    async def ow_sameplay_courtroom(self, event: AstrMessageEvent, player1_id: str, player2_id: str, index: int = 1):
        '''开庭分析两个玩家最近第 N 场同玩对局。

        Args:
            player1_id(string): 第一个玩家 BattleTag。
            player2_id(string): 第二个玩家 BattleTag。
            index(number): 同玩列表中的第几场，1 表示最近一场。
        '''
        replies = await self.handler.overstats_bridge.sameplay_detail(
            player1_id,
            player2_id,
            index=max(1, int(index or 1)),
            show_all_heroes=True,
            analyze=True,
        )
        for result in self._reply_results(event, replies):
            yield result

    @filter.llm_tool(name="ow_summary")
    async def ow_summary(self, event: AstrMessageEvent, player_id: str, scope: str = "today"):
        '''生成守望先锋玩家今日、昨日或本周总结图。

        Args:
            player_id(string): 玩家 BattleTag，例如 Player#12345。
            scope(string): 总结范围，today、yesterday 或 week。
        '''
        normalized_scope = str(scope or "today").lower()
        if normalized_scope not in {"today", "yesterday", "week"}:
            normalized_scope = "today"
        replies = await self.handler.overstats_bridge.summary(player_id, scope=normalized_scope)
        for result in self._reply_results(event, replies):
            yield result

    @filter.llm_tool(name="ow_strength")
    async def ow_strength(self, event: AstrMessageEvent, player_id: str, mode: str = "quick", limit: int = 12):
        '''查询守望先锋玩家快速或竞技强度趋势图。

        Args:
            player_id(string): 玩家 BattleTag，例如 Player#12345。
            mode(string): quick 表示快速，competitive 表示竞技。
            limit(number): 统计最近多少场。
        '''
        if str(mode or "").lower() in {"competitive", "ranked", "comp", "竞技"}:
            replies = await self.handler.overstats_bridge.competitive_strength(player_id, limit=limit or 12)
        else:
            replies = await self.handler.overstats_bridge.quick_strength(player_id, limit=limit or 12)
        for result in self._reply_results(event, replies):
            yield result

    @filter.llm_tool(name="ow_rank_history")
    async def ow_rank_history(self, event: AstrMessageEvent, player_id: str, start_season: int = 0, end_season: int = 0):
        '''查询守望先锋玩家段位历史图。

        Args:
            player_id(string): 玩家 BattleTag，例如 Player#12345。
            start_season(number): 开始赛季，可不填或填 0。
            end_season(number): 结束赛季，可不填或填 0。
        '''
        replies = await self.handler.overstats_bridge.rank_history(
            player_id,
            start_season=int(start_season or 0) or None,
            end_season=int(end_season or 0) or None,
        )
        for result in self._reply_results(event, replies):
            yield result

    @filter.llm_tool(name="ow_rank_leaderboard")
    async def ow_rank_leaderboard(self, event: AstrMessageEvent, province: str, role: str):
        '''查询守望先锋省份职责段位榜。

        Args:
            province(string): 省份，例如 北京。
            role(string): 职责，例如 输出、重装、支援、开放。
        '''
        replies = await self.handler.overstats_bridge.rank_leaderboard(province, role)
        for result in self._reply_results(event, replies):
            yield result

    @filter.llm_tool(name="ow_hero_leaderboard")
    async def ow_hero_leaderboard(self, event: AstrMessageEvent, province: str, hero: str, mode: str = "preset"):
        '''查询守望先锋省份英雄榜。

        Args:
            province(string): 省份，例如 北京。
            hero(string): 英雄名称，例如 猎空。
            mode(string): preset 表示预设职责，open 表示开放。
        '''
        replies = await self.handler.overstats_bridge.hero_leaderboard(province, hero, mode=mode or "preset")
        for result in self._reply_results(event, replies):
            yield result

    @filter.llm_tool(name="ow_hero_treemap")
    async def ow_hero_treemap(self, event: AstrMessageEvent, player_id: str, mode: str = "competitive", season: int = 0):
        '''查询守望先锋玩家英雄使用占比树图。

        Args:
            player_id(string): 玩家 BattleTag，例如 Player#12345。
            mode(string): competitive 表示竞技，quick 表示快速。
            season(number): 赛季编号，可不填或填 0。
        '''
        replies = await self.handler.overstats_bridge.hero_treemap(
            player_id,
            mode=mode or "competitive",
            season=int(season or 0) or None,
        )
        for result in self._reply_results(event, replies):
            yield result

    @filter.llm_tool(name="ow_hero_pick_rate")
    async def ow_hero_pick_rate(
        self,
        event: AstrMessageEvent,
        view: str = "ranking",
        mode: str = "quick",
        mmr: str = "all",
        hero: str = "",
        history_limit: int = 20,
    ):
        '''查询守望先锋英雄登场率排行或某英雄登场率历史。

        Args:
            view(string): ranking 表示排行，history 表示历史。
            mode(string): quick 表示快速，competitive 表示竞技。
            mmr(string): 段位，例如 all、Diamond、Master、Grandmaster。
            hero(string): 英雄名称；view 为 history 时必填。
            history_limit(number): 历史点数量。
        '''
        replies = await self.handler.overstats_bridge.hero_pick_rate(
            view=view or "ranking",
            mode=mode or "quick",
            mmr=mmr or "all",
            hero=hero or "",
            history_limit=history_limit or 20,
        )
        for result in self._reply_results(event, replies):
            yield result

    @filter.llm_tool(name="ow_hero_wiki")
    async def ow_hero_wiki(self, event: AstrMessageEvent, hero: str, question: str = ""):
        '''查询守望先锋英雄资料图，并可附带一个关于该英雄的问题。

        Args:
            hero(string): 英雄名称，例如 安娜。
            question(string): 关于该英雄的问题，可留空。
        '''
        replies = await self.handler.overstats_bridge.hero_wiki(hero, question=question or "")
        for result in self._reply_results(event, replies):
            yield result

    @filter.llm_tool(name="ow_shop")
    async def ow_shop(self, event: AstrMessageEvent):
        '''查询当前守望先锋商店图。'''
        replies = await self.handler.overstats_bridge.shop()
        for result in self._reply_results(event, replies):
            yield result

    @filter.llm_tool(name="ow_patch_notes")
    async def ow_patch_notes(self, event: AstrMessageEvent, patch_kind: str = "latest"):
        '''查询守望先锋补丁说明图。

        Args:
            patch_kind(string): latest、small 或 big。
        '''
        replies = await self.handler.overstats_bridge.patch_notes(patch_kind=patch_kind or "latest")
        for result in self._reply_results(event, replies):
            yield result

    @filter.llm_tool(name="ow_esports")
    async def ow_esports(self, event: AstrMessageEvent):
        '''查询守望先锋电竞赛程图。'''
        replies = await self.handler.overstats_bridge.esports()
        for result in self._reply_results(event, replies):
            yield result

    async def terminate(self):
        await self.handler.close()
