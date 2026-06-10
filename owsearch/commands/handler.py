from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Awaitable, Callable, TypeVar

from ..cache import ContextCache, IdentityStore
from ..cache.context import ContextKey
from ..clients import DashenClient
from ..config import PluginConfig
from ..errors import OwSearchError
from ..models import MatchDetail, ReplyItem
from ..renderers import (
    render_all_players_image,
    render_analysis_image,
    render_match_detail_image,
    render_match_list_image,
    render_profile_image,
    cleanup_render_dir,
    save_image,
)
from ..renderers.fonts import font_diagnostics
from ..renderers.text_fallback import detail_text, match_list_text, profile_text
from ..router import parse_command
from ..router.intents import CommandIntent
from ..services.analysis import AnalysisService
from ..services.identity import IdentityService
from ..services.match import MatchService
from ..services.profile import ProfileService
from ..services.sample_data import build_sample_analysis, build_sample_match_detail
from ..utils.sanitize import redact
from .help import HELP_TEXT

T = TypeVar("T")


class OwCommandHandler:
    def __init__(self, config: PluginConfig, data_dir: Path) -> None:
        self.config = config
        self.data_dir = data_dir
        self.render_dir = data_dir / "renders"
        self.cache_dir = data_dir / "cache"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.client = DashenClient(config.dashen)
        self.context_cache = ContextCache()
        self.identity_store = IdentityStore(self.cache_dir / "identity_store.json")
        self.identity_service = IdentityService(self.client, self.identity_store)
        self.profile_service = ProfileService(self.client, self.identity_service)
        self.match_service = MatchService(self.client, self.identity_service, self.context_cache)
        self.analysis_service = AnalysisService(config.ai)

    async def close(self) -> None:
        await self.client.close()

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
        if intent.name == "debug_live":
            return await self._debug_live(intent, context_key)
        if intent.name == "debug_render":
            return await self._debug_render()
        return [ReplyItem.text(HELP_TEXT)]

    def _require_bnet(self, intent: CommandIntent) -> str:
        bnet_id = str(intent.bnet_id or "").strip()
        if not bnet_id:
            raise OwSearchError("缺少玩家守望 ID。", "示例：/ow 开庭 Player#12345", code="missing_bnet_id")
        return bnet_id

    def _save(self, image, prefix: str) -> ReplyItem:
        saved = save_image(image, self.render_dir, prefix=prefix, max_bytes=self.config.render.max_bytes)
        cleanup_render_dir(self.render_dir, max_files=self.config.render.max_render_files)
        return ReplyItem.image(str(saved.path), saved.media_type)

    async def _profile(self, intent: CommandIntent) -> list[ReplyItem]:
        bnet_id = self._require_bnet(intent)
        profile = await self.profile_service.get_profile(bnet_id, refresh=intent.refresh)
        try:
            image = render_profile_image(profile, font_paths=self.config.render.font_paths)
            return [self._save(image, "profile")]
        except Exception:
            return [ReplyItem.text(profile_text(profile))]

    async def _match_list(self, intent: CommandIntent, context_key: ContextKey) -> list[ReplyItem]:
        bnet_id = self._require_bnet(intent)
        result = await self.match_service.list_recent_matches(
            bnet_id,
            context_key=context_key,
            limit=intent.limit or self.config.default_match_limit,
            include_fight=self.config.dashen.include_fight,
        )
        try:
            image = render_match_list_image(result.identity, result.matches, font_paths=self.config.render.font_paths)
            return [self._save(image, "matches")]
        except Exception:
            return [ReplyItem.text(match_list_text(result.matches))]

    async def _match_detail(
        self,
        intent: CommandIntent,
        context_key: ContextKey,
        *,
        force_analysis: bool = False,
    ) -> list[ReplyItem]:
        detail = await self._resolve_detail(intent, context_key)
        show_all = bool(intent.show_all_heroes or force_analysis)
        analyze = bool(intent.analyze or force_analysis)
        replies: list[ReplyItem] = []
        try:
            replies.append(self._save(render_match_detail_image(detail, font_paths=self.config.render.font_paths), "match_detail"))
            if show_all and detail.match_kind != "fight":
                replies.append(self._save(render_all_players_image(detail, font_paths=self.config.render.font_paths), "match_players"))
            if analyze:
                analysis = await self.analysis_service.analyze(detail)
                replies.append(
                    self._save(
                        render_analysis_image(detail, analysis, font_paths=self.config.render.font_paths),
                        "match_analysis",
                    )
                )
            if analyze and detail.match_kind == "fight":
                replies.append(ReplyItem.text("角斗对局暂不支持全员数据，AI 只能基于主战绩摘要分析。"))
            return replies
        except Exception:
            return [ReplyItem.text(detail_text(detail))]

    async def _resolve_detail(self, intent: CommandIntent, context_key: ContextKey) -> MatchDetail:
        if intent.bnet_id:
            return await self.match_service.detail_for_bnet_selector(
                intent.bnet_id,
                index=intent.index,
                selector=intent.selector,
                include_fight=self.config.dashen.include_fight,
            )
        if intent.index is not None:
            return await self.match_service.detail_by_context_index(context_key, intent.index)
        raise OwSearchError("缺少单局选择。", "示例：/ow 详情 1 或 /ow 详情 Player#12345 1", code="missing_match_selector")

    async def _courtroom(self, intent: CommandIntent, context_key: ContextKey) -> list[ReplyItem]:
        bnet_id = self._require_bnet(intent)
        detail = await self.match_service.latest_analyzable_detail(bnet_id, context_key=context_key)
        analysis = await self.analysis_service.analyze(detail)
        try:
            return [
                self._save(render_match_detail_image(detail, font_paths=self.config.render.font_paths), "court_result"),
                self._save(render_all_players_image(detail, font_paths=self.config.render.font_paths), "court_players"),
                self._save(render_analysis_image(detail, analysis, font_paths=self.config.render.font_paths), "court_analysis"),
            ]
        except Exception:
            return [ReplyItem.text(detail_text(detail))]

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

        if self.config.ai.ready:
            analysis, ai_ok = await timed("AI analysis", lambda: self.analysis_service.analyze(detail))
            if analysis is not None:
                lines.append(f"AI：{'成功' if analysis.ok else '失败'} / model={analysis.model or '-'}")
            if not ai_ok:
                lines.append("AI 阶段失败不影响 Dashen 数据链路。")
        else:
            lines.append("[SKIP] AI analysis: 未启用或未配置")

        lines.append(f"总耗时：{int((perf_counter() - total_started) * 1000)} ms")
        return [ReplyItem.text("\n".join(lines))]

    async def _debug_render(self) -> list[ReplyItem]:
        detail = build_sample_match_detail()
        analysis = build_sample_analysis()
        return [
            self._save(render_match_detail_image(detail, font_paths=self.config.render.font_paths), "debug_result"),
            self._save(render_all_players_image(detail, font_paths=self.config.render.font_paths), "debug_players"),
            self._save(render_analysis_image(detail, analysis, font_paths=self.config.render.font_paths), "debug_analysis"),
        ]

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
            f"图片上限：{self.config.render.max_bytes} bytes",
            f"图片保留：{self.config.render.max_render_files} 张",
            f"中文字体：{'已找到' if fonts['cjk_ready'] else '未确认'}",
            f"常规字体：{fonts['regular'] or '-'}",
            f"粗体字体：{fonts['bold'] or '-'}",
        ]
        return "\n".join(lines)
