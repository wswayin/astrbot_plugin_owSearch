import asyncio
import tempfile
import unittest
from pathlib import Path

from owsearch.cache.context import ContextKey
from owsearch.commands.handler import OwCommandHandler
from owsearch.config import PluginConfig
from owsearch.models import MatchDetail, MatchSummary, PlayerIdentity
from owsearch.services.analysis import AnalysisResult


def sample_detail() -> MatchDetail:
    identity = PlayerIdentity(
        query="Player#12345",
        full_id="Player#12345",
        bnet_id="12345",
        customer_token="customer-token",
    )
    source_match = {
        "matchId": "match-1",
        "matchRet": 1,
        "gameMode": "SportPreset",
        "beginTs": 1777212060658,
        "teamScore": 3,
        "opponentScore": 1,
        "kill": 21,
        "assist": 8,
        "death": 3,
        "heroDamage": 12800,
        "cure": 0,
        "resistDamage": 1200,
        "roleType": "dps",
    }
    payload = {
        "code": 0,
        "success": True,
        "data": {
            "matchRet": 1,
            "mapGuid": "map-1",
            "gameTimeSec": 955,
            "startTime": 1777212060,
            "teamScore": 3,
            "opponentScore": 1,
            "teammateList": [
                {
                    "name": "Player#12345",
                    "bnetId": "12345",
                    "roleType": "dps",
                    "kill": 21,
                    "assist": 8,
                    "death": 3,
                    "heroDamage": 12800,
                    "cure": 0,
                    "resistDamage": 1200,
                    "finalHit": 7,
                    "damageTaken": 4300,
                    "healingTaken": 2900,
                    "rankInfo": {"rank_name": "Diamond", "rank_sub_tier": 2},
                },
                {
                    "name": "Tank#1111",
                    "bnetId": "1111",
                    "roleType": "tank",
                    "kill": 12,
                    "assist": 13,
                    "death": 4,
                    "heroDamage": 7600,
                    "cure": 0,
                    "resistDamage": 15400,
                },
            ],
            "enemyList": [
                {
                    "name": "Enemy#9999",
                    "bnetId": "9999",
                    "roleType": "dps",
                    "kill": 16,
                    "assist": 3,
                    "death": 8,
                    "heroDamage": 10100,
                    "cure": 0,
                    "resistDamage": 300,
                }
            ],
        },
    }
    return MatchDetail(
        identity=identity,
        summary=MatchSummary.from_payload(source_match),
        payload=payload,
        source_match=source_match,
        match_kind="normal",
    )


class FakeMatchService:
    async def latest_analyzable_detail(self, bnet_id, *, context_key=None):
        self.bnet_id = bnet_id
        self.context_key = context_key
        return sample_detail()


class FakeAnalysisService:
    async def analyze(self, detail):
        return AnalysisResult(
            ok=True,
            model="fake-model",
            data={
                "score": "A",
                "verdict": "焦点玩家输出稳定，死亡控制不错。",
                "highlights": ["击杀效率高", "死亡少"],
                "problems": ["承伤偏高"],
                "advice": ["继续保持站位纪律"],
                "meme_line": "man! what can i say, mamba out。",
            },
        )


class HandlerE2ETests(unittest.TestCase):
    def test_courtroom_returns_three_images(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                handler.match_service = FakeMatchService()
                handler.analysis_service = FakeAnalysisService()
                try:
                    replies = await handler.handle(
                        "/ow 开庭 Player#12345",
                        ContextKey(platform="test", session="room", user="user"),
                    )
                finally:
                    await handler.close()

                self.assertEqual([reply.kind for reply in replies], ["image", "image", "image"])
                for reply in replies:
                    path = Path(reply.path)
                    self.assertTrue(path.exists())
                    self.assertGreater(path.stat().st_size, 1000)

        asyncio.run(run())

    def test_debug_config_does_not_leak_secret_values(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                config = PluginConfig.from_mapping(
                    {
                        "dashen": {"role_id": 123, "token": "secret-token"},
                        "ai": {"enabled": True, "base_url": "https://example.com/v1", "api_key": "secret-key"},
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
                self.assertIn("图片保留：300 张", text)
                self.assertNotIn("secret-token", text)
                self.assertNotIn("secret-key", text)

        asyncio.run(run())

    def test_debug_render_returns_three_images(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                handler = OwCommandHandler(PluginConfig.from_mapping({}), Path(temp_dir))
                try:
                    replies = await handler.handle("/ow debug 图片", ContextKey("test", "room", "user"))
                finally:
                    await handler.close()

                self.assertEqual([reply.kind for reply in replies], ["image", "image", "image"])
                for reply in replies:
                    path = Path(reply.path)
                    self.assertTrue(path.exists())
                    self.assertGreater(path.stat().st_size, 1000)

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
