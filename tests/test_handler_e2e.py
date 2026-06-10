import asyncio
import tempfile
import unittest
from pathlib import Path

from owsearch.cache.context import ContextKey
from owsearch.commands.handler import OwCommandHandler
from owsearch.config import PluginConfig


class FakeOverstatsBridge:
    def __init__(self):
        self.bnet_id = ""
        self.player1 = ""
        self.player2 = ""
        self.index = 0
        self.show_all_heroes = False
        self.analyze = False
        self.scope = ""
        self.limit = 0
        self.province = ""
        self.role = ""
        self.hero = ""
        self.mode = ""
        self.view = ""
        self.mmr = ""
        self.question = ""
        self.history_limit = None
        self.patch_kind = ""
        self.start_season = None
        self.end_season = None

    async def courtroom(self, bnet_id, *, index=1):
        self.bnet_id = bnet_id
        self.index = index
        return [
            MatchReplyFactory.image("court-1"),
            MatchReplyFactory.image("court-2"),
            MatchReplyFactory.image("court-3"),
        ]

    async def sameplay_list(self, player1, player2, *, limit=20):
        self.player1 = player1
        self.player2 = player2
        self.limit = limit
        return [MatchReplyFactory.image("sameplay-list")]

    async def sameplay_detail(self, player1, player2, *, index=1, show_all_heroes=False, analyze=False):
        self.player1 = player1
        self.player2 = player2
        self.index = index
        self.show_all_heroes = show_all_heroes
        self.analyze = analyze
        return [MatchReplyFactory.image("sameplay-detail")]

    async def summary(self, bnet_id, *, scope="today"):
        self.bnet_id = bnet_id
        self.scope = scope
        return [MatchReplyFactory.image(f"summary-{scope}")]

    async def quick_strength(self, bnet_id, *, limit=12):
        self.bnet_id = bnet_id
        self.limit = limit
        return [MatchReplyFactory.image("quick-strength")]

    async def competitive_strength(self, bnet_id, *, limit=12):
        self.bnet_id = bnet_id
        self.limit = limit
        return [MatchReplyFactory.image("competitive-strength")]

    async def rank_history(self, bnet_id, *, start_season=None, end_season=None):
        self.bnet_id = bnet_id
        self.start_season = start_season
        self.end_season = end_season
        return [MatchReplyFactory.image("rank-history")]

    async def rank_leaderboard(self, province, role):
        self.province = province
        self.role = role
        return [MatchReplyFactory.image("rank-leaderboard")]

    async def hero_leaderboard(self, province, hero, *, mode="preset"):
        self.province = province
        self.hero = hero
        self.mode = mode
        return [MatchReplyFactory.image("hero-leaderboard")]

    async def hero_treemap(self, bnet_id, *, mode="competitive", season=None):
        self.bnet_id = bnet_id
        self.mode = mode
        self.start_season = season
        return [MatchReplyFactory.image("hero-treemap")]

    async def hero_pick_rate(self, *, view="ranking", mode="quick", mmr="all", hero="", history_limit=None):
        self.view = view
        self.mode = mode
        self.mmr = mmr
        self.hero = hero
        self.history_limit = history_limit
        return [MatchReplyFactory.image("hero-pick-rate")]

    async def hero_wiki(self, hero, *, question=""):
        self.hero = hero
        self.question = question
        return [MatchReplyFactory.image("hero-wiki")]

    async def shop(self):
        return [MatchReplyFactory.image("shop")]

    async def patch_notes(self, *, patch_kind="latest"):
        self.patch_kind = patch_kind
        return [MatchReplyFactory.image("patch-notes")]

    async def esports(self):
        return [MatchReplyFactory.image("esports")]

    async def identity_search(self, bnet_id, *, limit=10):
        self.bnet_id = bnet_id
        self.limit = limit
        from owsearch.models import ReplyItem

        return [ReplyItem.text(f"identity {bnet_id} {limit}")]

    async def close(self):
        return None


class MatchReplyFactory:
    @staticmethod
    def image(stem: str):
        from owsearch.models import ReplyItem

        temp_path = Path(tempfile.gettempdir()) / f"{stem}.png"
        temp_path.write_bytes(b"x" * 1200)
        return ReplyItem.image(str(temp_path), "image/png")


class HandlerE2ETests(unittest.TestCase):
    def test_courtroom_returns_three_images(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle(
                        "/ow 开庭 Player#12345 2",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual(fake_bridge.bnet_id, "Player#12345")
                self.assertEqual(fake_bridge.index, 2)
                self.assertEqual([reply.kind for reply in replies], ["image", "image", "image"])
                for reply in replies:
                    path = Path(reply.path)
                    self.assertTrue(path.exists())
                    self.assertGreater(path.stat().st_size, 1000)

        asyncio.run(run())

    def test_sameplay_list_context_and_shortcut(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                context_key = ContextKey(platform="test", session="room", user="user")
                try:
                    list_replies = await handler.handle("/ow 同玩 Alpha#12345 Bravo#67890 8", context_key)
                    detail_replies = await handler.handle("/ow 1**", context_key)
                finally:
                    await handler.close()

                self.assertEqual([reply.kind for reply in list_replies], ["image"])
                self.assertEqual([reply.kind for reply in detail_replies], ["image"])
                self.assertEqual(fake_bridge.player1, "Alpha#12345")
                self.assertEqual(fake_bridge.player2, "Bravo#67890")
                self.assertEqual(fake_bridge.index, 1)
                self.assertTrue(fake_bridge.show_all_heroes)
                self.assertTrue(fake_bridge.analyze)

        asyncio.run(run())

    def test_summary_uses_scope(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle(
                        "/ow 周报 Player#12345",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual(fake_bridge.bnet_id, "Player#12345")
                self.assertEqual(fake_bridge.scope, "week")
                self.assertEqual([reply.kind for reply in replies], ["image"])

        asyncio.run(run())

    def test_quick_strength_uses_limit(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle(
                        "/ow 快速强度 Player#12345 9",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual(fake_bridge.bnet_id, "Player#12345")
                self.assertEqual(fake_bridge.limit, 9)
                self.assertEqual([reply.kind for reply in replies], ["image"])

        asyncio.run(run())

    def test_competitive_strength_uses_limit(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle(
                        "/ow 竞技强度 Player#12345 7",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual(fake_bridge.bnet_id, "Player#12345")
                self.assertEqual(fake_bridge.limit, 7)
                self.assertEqual([reply.kind for reply in replies], ["image"])

        asyncio.run(run())

    def test_rank_history_uses_seasons(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle(
                        "/ow 段位历史 Player#12345 15 22",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual(fake_bridge.bnet_id, "Player#12345")
                self.assertEqual(fake_bridge.start_season, 15)
                self.assertEqual(fake_bridge.end_season, 22)
                self.assertEqual([reply.kind for reply in replies], ["image"])

        asyncio.run(run())

    def test_rank_leaderboard_uses_filters(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle(
                        "/ow 省榜 北京 输出",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual(fake_bridge.province, "北京")
                self.assertEqual(fake_bridge.role, "输出")
                self.assertEqual([reply.kind for reply in replies], ["image"])

        asyncio.run(run())

    def test_hero_leaderboard_uses_filters(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle(
                        "/ow 英雄榜 北京 猎空 开放",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual(fake_bridge.province, "北京")
                self.assertEqual(fake_bridge.hero, "猎空")
                self.assertEqual(fake_bridge.mode, "开放")
                self.assertEqual([reply.kind for reply in replies], ["image"])

        asyncio.run(run())

    def test_hero_treemap_uses_filters(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle(
                        "/ow 英雄占比 Player#12345 快速 22",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual(fake_bridge.bnet_id, "Player#12345")
                self.assertEqual(fake_bridge.mode, "quick")
                self.assertEqual(fake_bridge.start_season, 22)
                self.assertEqual([reply.kind for reply in replies], ["image"])

        asyncio.run(run())

    def test_hero_pick_rate_ranking_uses_filters(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle(
                        "/ow 登场率 竞技 钻石",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual(fake_bridge.view, "ranking")
                self.assertEqual(fake_bridge.mode, "competitive")
                self.assertEqual(fake_bridge.mmr, "Diamond")
                self.assertEqual([reply.kind for reply in replies], ["image"])

        asyncio.run(run())

    def test_hero_pick_rate_history_uses_filters(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle(
                        "/ow 登场率历史 安娜 竞技 钻石 18",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual(fake_bridge.view, "history")
                self.assertEqual(fake_bridge.hero, "安娜")
                self.assertEqual(fake_bridge.mode, "competitive")
                self.assertEqual(fake_bridge.mmr, "Diamond")
                self.assertEqual(fake_bridge.history_limit, 18)
                self.assertEqual([reply.kind for reply in replies], ["image"])

        asyncio.run(run())

    def test_hero_perk_is_removed(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle(
                        "/ow 威能 安娜",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual([reply.kind for reply in replies], ["text"])
                self.assertIn("守望查询", replies[0].content)

        asyncio.run(run())

    def test_hero_wiki_uses_question(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle(
                        "/ow 英雄资料 安娜 技能冷却是多少",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual(fake_bridge.hero, "安娜")
                self.assertEqual(fake_bridge.question, "技能冷却是多少")
                self.assertEqual([reply.kind for reply in replies], ["image"])

        asyncio.run(run())

    def test_shop_returns_image(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle(
                        "/ow 商店",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual([reply.kind for reply in replies], ["image"])

        asyncio.run(run())

    def test_patch_notes_uses_kind(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle(
                        "/ow 补丁 小补丁",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual(fake_bridge.patch_kind, "small")
                self.assertEqual([reply.kind for reply in replies], ["image"])

        asyncio.run(run())

    def test_esports_returns_image(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle(
                        "/ow 电竞",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual([reply.kind for reply in replies], ["image"])

        asyncio.run(run())

    def test_identity_search_uses_limit(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle(
                        "/ow 反查 123456789 10",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual(fake_bridge.bnet_id, "123456789")
                self.assertEqual(fake_bridge.limit, 10)
                self.assertEqual(replies[0].kind, "text")

        asyncio.run(run())

    def test_ow_guess_is_removed(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle(
                        "/ow 猜 英雄图标",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual([reply.kind for reply in replies], ["text"])
                self.assertIn("守望查询", replies[0].content)

        asyncio.run(run())

    def test_debug_config_does_not_leak_secret_values(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                config = PluginConfig.from_mapping(
                    {
                        "dashen": {"role_id": 123, "token": "secret-token"},
                        "ai": {"enabled": True, "base_url": "https://example.com/v1", "api_key": "secret-key"},
                        "ow_esports_api_key": "secret-esports-key",
                    }
                )
                handler = OwCommandHandler(config, Path(temp_dir))
                try:
                    replies = await handler.handle("/ow debug 配置", ContextKey("test", "room", "user"))
                finally:
                    await handler.close()
                text = replies[0].content
                self.assertIn("Dashen token：已填", text)
                self.assertIn("AI：已启用", text)
                self.assertIn("电竞 API key：已填", text)
                self.assertIn("图片保留：300 张", text)
                self.assertIn("正式图片渲染：Overstats 原版", text)
                self.assertIn("debug 图片：Overstats 原版开庭渲染", text)
                self.assertNotIn("secret-token", text)
                self.assertNotIn("secret-key", text)
                self.assertNotIn("secret-esports-key", text)

        asyncio.run(run())

    def test_debug_ai_does_not_leak_secret_values(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                config = PluginConfig.from_mapping(
                    {
                        "ai": {
                            "enabled": True,
                            "base_url": "https://api.deepseek.com/v1",
                            "api_key": "secret-key",
                            "model": "deepseek-chat",
                        },
                    }
                )
                handler = OwCommandHandler(config, Path(temp_dir))
                try:
                    replies = await handler.handle("/ow debug ai", ContextKey("test", "room", "user"))
                finally:
                    await handler.close()
                text = replies[0].content
                self.assertIn("OW AI 配置检查", text)
                self.assertIn("provider：DeepSeek-compatible", text)
                self.assertIn("api_key：已填", text)
                self.assertIn("可用状态：可用", text)
                self.assertNotIn("secret-key", text)

        asyncio.run(run())

    def test_debug_render_uses_overstats_courtroom(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                fake_bridge = FakeOverstatsBridge()
                handler.overstats_bridge = fake_bridge
                try:
                    replies = await handler.handle("/ow debug 图片 Player#12345 2", ContextKey("test", "room", "user"))
                finally:
                    await handler.close()

                self.assertEqual(fake_bridge.bnet_id, "Player#12345")
                self.assertEqual(fake_bridge.index, 2)
                self.assertEqual([reply.kind for reply in replies], ["image", "image", "image"])
                for reply in replies:
                    path = Path(reply.path)
                    self.assertTrue(path.exists())
                    self.assertGreater(path.stat().st_size, 1000)

        asyncio.run(run())

    def test_debug_render_requires_player_id(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                try:
                    replies = await handler.handle("/ow debug 图片", ContextKey("test", "room", "user"))
                finally:
                    await handler.close()

                self.assertEqual(replies[0].kind, "text")
                self.assertIn("缺少玩家守望 ID", replies[0].content)

        asyncio.run(run())

    def test_debug_live_without_config_reports_stage_failure(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                try:
                    replies = await handler.handle("/ow debug 接口 Player#12345 5", ContextKey("test", "room", "user"))
                finally:
                    await handler.close()
                self.assertEqual(replies[0].kind, "text")
                self.assertIn("[FAIL] searchBnetAccount", replies[0].content)
                self.assertIn("Dashen", replies[0].content)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
