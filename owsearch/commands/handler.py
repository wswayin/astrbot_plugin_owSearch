from __future__ import annotations

import inspect
from pathlib import Path
from time import perf_counter
from typing import Awaitable, Callable, TypeVar

from ..cache import ContextCache, IdentityStore
from ..cache.context import ContextKey
from ..clients import DashenClient
from ..config import PluginConfig
from ..errors import OwSearchError
from ..models import ReplyItem
from ..overstats_bridge import OverstatsBridge
from ..renderers.fonts import font_diagnostics
from ..router import parse_command
from ..router.intents import CommandIntent
from ..services.identity import IdentityService
from ..services.match import MatchService
from ..utils.sanitize import redact
from .help import HELP_TEXT

T = TypeVar("T")


class OwCommandHandler:
    def __init__(self, config: PluginConfig, data_dir: Path) -> None:
        self.config = config
        self.data_dir = data_dir
        self.cache_dir = data_dir / "cache"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.client = DashenClient(config.dashen)
        self.context_cache = ContextCache()
        self.identity_store = IdentityStore(self.cache_dir / "identity_store.json")
        self.identity_service = IdentityService(self.client, self.identity_store)
        self.match_service = MatchService(self.client, self.identity_service, self.context_cache)
        self.overstats_bridge = OverstatsBridge(config, data_dir)
        self._owned_overstats_bridge = self.overstats_bridge

    async def close(self) -> None:
        await self.client.close()
        await self._close_optional_bridge(self.overstats_bridge)
        if self._owned_overstats_bridge is not self.overstats_bridge:
            await self._close_optional_bridge(self._owned_overstats_bridge)

    async def _close_optional_bridge(self, bridge) -> None:
        close = getattr(bridge, "close", None)
        if close is None:
            return
        result = close()
        if inspect.isawaitable(result):
            await result

    async def handle(self, message: str, context_key: ContextKey) -> list[ReplyItem]:
        intent = parse_command(message)
        try:
            return await self._handle_intent(intent, context_key)
        except OwSearchError as exc:
            return [ReplyItem.text(str(exc))]
        except Exception as exc:
            if self.config.debug:
                return [ReplyItem.text(f"查询失败：{type(exc).__name__}: {exc}")]
            return [ReplyItem.text("查询失败，可能是大神接口暂时不可用或配置有误。")]

    async def _handle_intent(self, intent: CommandIntent, context_key: ContextKey) -> list[ReplyItem]:
        if intent.name == "help":
            return [ReplyItem.text(HELP_TEXT)]
        if intent.name == "profile":
            return await self._profile(intent)
        if intent.name == "match_list":
            return await self._match_list(intent, context_key)
        if intent.name == "match_detail":
            return await self._match_detail(intent, context_key)
        if intent.name == "sameplay_list":
            return await self._sameplay_list(intent, context_key)
        if intent.name == "sameplay_detail":
            return await self._sameplay_detail(intent, context_key)
        if intent.name == "summary":
            return await self._summary(intent)
        if intent.name == "quick_strength":
            return await self._quick_strength(intent)
        if intent.name == "competitive_strength":
            return await self._competitive_strength(intent)
        if intent.name == "rank_history":
            return await self._rank_history(intent)
        if intent.name == "rank_leaderboard":
            return await self._rank_leaderboard(intent)
        if intent.name == "hero_leaderboard":
            return await self._hero_leaderboard(intent)
        if intent.name == "hero_treemap":
            return await self._hero_treemap(intent)
        if intent.name == "hero_pick_rate":
            return await self._hero_pick_rate(intent)
        if intent.name == "hero_perk":
            return await self._hero_perk(intent)
        if intent.name == "hero_wiki":
            return await self._hero_wiki(intent)
        if intent.name == "shop":
            return await self._shop()
        if intent.name == "patch_notes":
            return await self._patch_notes(intent)
        if intent.name == "esports":
            return await self._esports()
        if intent.name == "identity_search":
            return await self._identity_search(intent)
        if intent.name == "analysis":
            return await self._match_detail(intent, context_key, force_analysis=True)
        if intent.name == "courtroom":
            return await self._courtroom(intent, context_key)
        if intent.name == "refresh":
            return await self._refresh(intent)
        if intent.name == "debug_matches":
            return await self._debug_matches(intent, context_key)
        if intent.name == "debug_config":
            return [ReplyItem.text(self._debug_config_text())]
        if intent.name == "debug_ai":
            return [ReplyItem.text(self._debug_ai_text())]
        if intent.name == "debug_live":
            return await self._debug_live(intent, context_key)
        if intent.name == "debug_render":
            return await self._debug_render(intent)
        return [ReplyItem.text(HELP_TEXT)]

    def _require_bnet(self, intent: CommandIntent) -> str:
        bnet_id = str(intent.bnet_id or "").strip()
        if not bnet_id:
            raise OwSearchError("缺少玩家守望 ID。", "示例：/ow 开庭 Player#12345", code="missing_bnet_id")
        return bnet_id

    def _require_bnet_pair(self, intent: CommandIntent) -> tuple[str, str]:
        player1 = str(intent.bnet_id or "").strip()
        player2 = str(intent.bnet_id2 or "").strip()
        if not player1 or not player2:
            raise OwSearchError("缺少同玩玩家守望 ID。", "示例：/ow 同玩 PlayerA#12345 PlayerB#67890", code="missing_bnet_pair")
        return player1, player2

    def _require_province_role(self, intent: CommandIntent) -> tuple[str, str]:
        province = str(intent.province or "").strip()
        role = str(intent.role or "").strip()
        if not province or not role:
            raise OwSearchError("缺少省榜查询参数。", "示例：/ow 省榜 北京 输出", code="missing_leaderboard_args")
        return province, role

    def _require_province_hero(self, intent: CommandIntent) -> tuple[str, str]:
        province = str(intent.province or "").strip()
        hero = str(intent.hero or "").strip()
        if not province or not hero:
            raise OwSearchError("缺少英雄榜查询参数。", "示例：/ow 英雄榜 北京 猎空 预设", code="missing_hero_leaderboard_args")
        return province, hero

    def _require_hero(self, intent: CommandIntent, *, example: str) -> str:
        hero = str(intent.hero or "").strip()
        if not hero:
            raise OwSearchError("缺少英雄名称。", example, code="missing_hero")
        return hero

    async def _profile(self, intent: CommandIntent) -> list[ReplyItem]:
        bnet_id = self._require_bnet(intent)
        return await self.overstats_bridge.profile(bnet_id)

    async def _match_list(self, intent: CommandIntent, context_key: ContextKey) -> list[ReplyItem]:
        bnet_id = self._require_bnet(intent)
        self.context_cache.set(context_key, {"overstats_context": "match_list", "bnet_id": bnet_id})
        return await self.overstats_bridge.match_list(
            bnet_id,
            limit=intent.limit or self.config.default_match_limit,
            include_fight=self.config.dashen.include_fight,
        )

    async def _match_detail(
        self,
        intent: CommandIntent,
        context_key: ContextKey,
        *,
        force_analysis: bool = False,
    ) -> list[ReplyItem]:
        show_all = bool(intent.show_all_heroes or force_analysis)
        analyze = bool(intent.analyze or force_analysis)
        if intent.bnet_id:
            return await self.overstats_bridge.match_detail(
                intent.bnet_id,
                index=intent.index or 1,
                show_all_heroes=show_all,
                analyze=analyze,
                include_fight=self.config.dashen.include_fight,
            )
        if intent.index is not None:
            context = self.context_cache.get(context_key) or {}
            context_type = str(context.get("overstats_context") or "")
            if context_type == "sameplay_list":
                player1 = str(context.get("player1_bnet_id") or "").strip()
                player2 = str(context.get("player2_bnet_id") or "").strip()
                if player1 and player2:
                    return await self.overstats_bridge.sameplay_detail(
                        player1,
                        player2,
                        index=intent.index,
                        show_all_heroes=show_all,
                        analyze=analyze,
                    )
            bnet_id = str(context.get("bnet_id") or "").strip() if context_type else ""
            if context_type == "match_list" and bnet_id:
                return await self.overstats_bridge.match_detail(
                    bnet_id,
                    index=intent.index,
                    show_all_heroes=show_all,
                    analyze=analyze,
                    include_fight=self.config.dashen.include_fight,
                )
        raise OwSearchError(
            "当前没有可用的 Overstats 对局上下文。",
            "请先发送 /ow 战绩 Player#12345 建立列表上下文，或直接使用 /ow 详情 Player#12345 1。",
            code="missing_overstats_context",
        )

    async def _sameplay_list(self, intent: CommandIntent, context_key: ContextKey) -> list[ReplyItem]:
        player1, player2 = self._require_bnet_pair(intent)
        self.context_cache.set(
            context_key,
            {
                "overstats_context": "sameplay_list",
                "player1_bnet_id": player1,
                "player2_bnet_id": player2,
            },
        )
        return await self.overstats_bridge.sameplay_list(player1, player2, limit=intent.limit or 20)

    async def _sameplay_detail(self, intent: CommandIntent, context_key: ContextKey) -> list[ReplyItem]:
        player1, player2 = self._require_bnet_pair(intent)
        return await self.overstats_bridge.sameplay_detail(
            player1,
            player2,
            index=intent.index or 1,
            show_all_heroes=intent.show_all_heroes,
            analyze=intent.analyze,
        )

    async def _summary(self, intent: CommandIntent) -> list[ReplyItem]:
        bnet_id = self._require_bnet(intent)
        return await self.overstats_bridge.summary(bnet_id, scope=intent.scope or "today")

    async def _quick_strength(self, intent: CommandIntent) -> list[ReplyItem]:
        bnet_id = self._require_bnet(intent)
        return await self.overstats_bridge.quick_strength(bnet_id, limit=intent.limit or 12)

    async def _competitive_strength(self, intent: CommandIntent) -> list[ReplyItem]:
        bnet_id = self._require_bnet(intent)
        return await self.overstats_bridge.competitive_strength(bnet_id, limit=intent.limit or 12)

    async def _rank_history(self, intent: CommandIntent) -> list[ReplyItem]:
        bnet_id = self._require_bnet(intent)
        return await self.overstats_bridge.rank_history(
            bnet_id,
            start_season=intent.start_season,
            end_season=intent.end_season,
        )

    async def _rank_leaderboard(self, intent: CommandIntent) -> list[ReplyItem]:
        province, role = self._require_province_role(intent)
        return await self.overstats_bridge.rank_leaderboard(province, role)

    async def _hero_leaderboard(self, intent: CommandIntent) -> list[ReplyItem]:
        province, hero = self._require_province_hero(intent)
        return await self.overstats_bridge.hero_leaderboard(province, hero, mode=intent.mode or "preset")

    async def _hero_treemap(self, intent: CommandIntent) -> list[ReplyItem]:
        bnet_id = self._require_bnet(intent)
        return await self.overstats_bridge.hero_treemap(
            bnet_id,
            mode=intent.mode or "competitive",
            season=intent.start_season,
        )

    async def _hero_pick_rate(self, intent: CommandIntent) -> list[ReplyItem]:
        hero = ""
        if (intent.view or "ranking") == "history":
            hero = self._require_hero(intent, example="示例：/ow 登场率历史 安娜 竞技 钻石")
        return await self.overstats_bridge.hero_pick_rate(
            view=intent.view or "ranking",
            mode=intent.mode or "quick",
            mmr=intent.mmr or "all",
            hero=hero,
            history_limit=intent.history_limit,
        )

    async def _hero_perk(self, intent: CommandIntent) -> list[ReplyItem]:
        hero = self._require_hero(intent, example="示例：/ow 威能 安娜")
        return await self.overstats_bridge.hero_perk(hero)

    async def _hero_wiki(self, intent: CommandIntent) -> list[ReplyItem]:
        hero = self._require_hero(intent, example="示例：/ow 英雄资料 安娜")
        return await self.overstats_bridge.hero_wiki(hero, question=intent.question)

    async def _shop(self) -> list[ReplyItem]:
        return await self.overstats_bridge.shop()

    async def _patch_notes(self, intent: CommandIntent) -> list[ReplyItem]:
        return await self.overstats_bridge.patch_notes(patch_kind=intent.patch_kind or "latest")

    async def _esports(self) -> list[ReplyItem]:
        return await self.overstats_bridge.esports()

    async def _identity_search(self, intent: CommandIntent) -> list[ReplyItem]:
        bnet_id = str(intent.bnet_id or "").strip()
        if not bnet_id:
            raise OwSearchError("缺少 bnet_id。", "示例：/ow 反查 123456789", code="missing_bnet_id")
        return await self.overstats_bridge.identity_search(bnet_id, limit=intent.limit or 10)

    async def _courtroom(self, intent: CommandIntent, context_key: ContextKey) -> list[ReplyItem]:
        bnet_id = self._require_bnet(intent)
        return await self.overstats_bridge.courtroom(bnet_id, index=intent.index or 1)

    async def _refresh(self, intent: CommandIntent) -> list[ReplyItem]:
        bnet_id = self._require_bnet(intent)
        self.identity_service.clear(bnet_id)
        identity = await self.identity_service.resolve_bnet(bnet_id, refresh=True)
        return [ReplyItem.text(f"已刷新玩家缓存：{identity.full_id}")]

    async def _debug_matches(self, intent: CommandIntent, context_key: ContextKey) -> list[ReplyItem]:
        bnet_id = self._require_bnet(intent)
        result = await self.match_service.list_recent_matches(
            bnet_id,
            context_key=context_key,
            limit=intent.limit or self.config.default_match_limit,
            include_fight=self.config.dashen.include_fight,
        )
        payload = {
            "identity": result.identity.to_cache(),
            "count": len(result.matches),
            "matches": [match.raw for match in result.matches[:3]],
        }
        return [ReplyItem.text(str(redact(payload)))]

    async def _debug_live(self, intent: CommandIntent, context_key: ContextKey) -> list[ReplyItem]:
        bnet_id = self._require_bnet(intent)
        limit = intent.limit or 5
        lines = ["OW Dashen 联调："]
        total_started = perf_counter()

        async def timed(label: str, factory: Callable[[], Awaitable[T]]) -> tuple[T | None, bool]:
            started = perf_counter()
            try:
                value = await factory()
            except Exception as exc:
                elapsed_ms = int((perf_counter() - started) * 1000)
                lines.append(f"[FAIL] {label}: {elapsed_ms} ms, {type(exc).__name__}: {exc}")
                return None, False
            elapsed_ms = int((perf_counter() - started) * 1000)
            lines.append(f"[OK] {label}: {elapsed_ms} ms")
            return value, True

        identity, ok = await timed("searchBnetAccount", lambda: self.identity_service.resolve_bnet(bnet_id, refresh=True))
        if not ok or identity is None:
            lines.append(f"总耗时：{int((perf_counter() - total_started) * 1000)} ms")
            return [ReplyItem.text("\n".join(lines))]
        lines.append(f"玩家：{identity.full_id} / bnetId={identity.bnet_id or '-'} / customerToken=已获取")

        match_result, ok = await timed(
            "queryMatchList",
            lambda: self.match_service.list_recent_matches(
                identity.full_id or bnet_id,
                context_key=context_key,
                limit=limit,
                include_fight=self.config.dashen.include_fight,
            ),
        )
        if not ok or match_result is None:
            lines.append(f"总耗时：{int((perf_counter() - total_started) * 1000)} ms")
            return [ReplyItem.text("\n".join(lines))]

        lines.append(f"最近对局：{len(match_result.matches)} 条")
        if not match_result.matches:
            lines.append("没有可用于详情测试的对局。")
            lines.append(f"总耗时：{int((perf_counter() - total_started) * 1000)} ms")
            return [ReplyItem.text("\n".join(lines))]

        first = match_result.matches[0]
        lines.append(
            "第一局："
            f"{first.mode_label} / {first.result_label} / {first.begin_text} / "
            f"matchId={first.match_id or '-'}"
        )

        detail, ok = await timed(
            "queryMatchInfo",
            lambda: self.match_service.detail_by_index(match_result.identity, match_result.raw_matches, 1),
        )
        if not ok or detail is None:
            lines.append(f"总耗时：{int((perf_counter() - total_started) * 1000)} ms")
            return [ReplyItem.text("\n".join(lines))]
        lines.append(f"详情：match_kind={detail.match_kind} / data_keys={len(detail.data.keys())}")

        lines.append(
            "AI：正式分析由 Overstats 原版 _build_ai_analysis 与 render_analysis_report 处理；"
            f"当前配置 {'已就绪' if self.config.ai.ready else '未就绪'}。"
        )

        lines.append(f"总耗时：{int((perf_counter() - total_started) * 1000)} ms")
        return [ReplyItem.text("\n".join(lines))]

    async def _debug_render(self, intent: CommandIntent) -> list[ReplyItem]:
        bnet_id = self._require_bnet(intent)
        return await self.overstats_bridge.courtroom(bnet_id, index=intent.index or 1)

    def _debug_config_text(self) -> str:
        dashen = self.config.dashen
        ai = self.config.ai
        fonts = font_diagnostics(self.config.render.font_paths)
        lines = [
            "OW 查询配置检查：",
            f"Dashen role_id：{'已填' if dashen.role_id > 0 else '未填'}",
            f"Dashen token：{'已填' if dashen.token else '未填'}",
            f"Dashen dts/server：{dashen.dts}/{dashen.server}",
            f"Dashen 并发：{dashen.max_concurrent_requests}",
            f"包含角斗列表：{'是' if dashen.include_fight else '否'}",
            f"AI：{'已启用' if ai.ready else '未启用或未配置'}",
            f"AI base_url：{'已填' if ai.base_url else '未填'}",
            f"AI model：{ai.model or '自动推断'}",
            "AI 提示词：Overstats 原版",
            "AI 图片布局：Overstats 原版 render_analysis_report",
            f"电竞 API key：{'已填' if self.config.ow_esports_api_key else '未填'}",
            f"图片上限：{self.config.render.max_bytes} bytes",
            f"图片保留：{self.config.render.max_render_files} 张",
            "正式图片渲染：Overstats 原版",
            "debug 图片：Overstats 原版开庭渲染",
            f"中文字体：{'已找到' if fonts['cjk_ready'] else '未确认'}",
            f"常规字体：{fonts['regular'] or '-'}",
            f"粗体字体：{fonts['bold'] or '-'}",
        ]
        return "\n".join(lines)

    def _debug_ai_text(self) -> str:
        ai = self.config.ai
        model = ai.model or "自动推断"
        base_url = str(ai.base_url or "").strip()
        provider = "未配置"
        lowered = base_url.lower()
        if "deepseek" in lowered:
            provider = "DeepSeek-compatible"
        elif "googleapis.com" in lowered or "generativelanguage" in lowered:
            provider = "Google-compatible"
        elif base_url:
            provider = "OpenAI-compatible"
        lines = [
            "OW AI 配置检查：",
            f"启用状态：{'已启用' if ai.enabled else '未启用'}",
            f"base_url：{'已填' if base_url else '未填'}",
            f"api_key：{'已填' if ai.api_key else '未填'}",
            f"provider：{provider}",
            f"model：{model}",
            f"timeout：{ai.timeout_seconds} 秒",
            "提示词：Overstats 原版 _build_ai_analysis",
            "图片布局：Overstats 原版 render_analysis_report",
            f"可用状态：{'可用' if ai.ready else '不可用'}",
        ]
        return "\n".join(lines)
