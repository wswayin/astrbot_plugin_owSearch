import asyncio
import unittest

import httpx

from overstats.src.modules.dashen_match import service as match_service
from overstats.src.modules.dashen_match.render import _load_ow_config, _resolve_player_hero
from overstats.src.modules.dashen_match.service import DashenMatchModule


class FakeDashenApiClient:
    def __init__(self):
        self.icon_urls = []

    async def get_icon(self, url: str) -> bytes:
        self.icon_urls.append(url)
        return b"image"


class OverstatsMatchRuntimeTests(unittest.TestCase):
    def test_prefetch_match_render_images_collects_current_match_assets(self):
        async def run():
            config = _load_ow_config()
            map_info = next(item for item in config["mapList"] if item.get("icon"))
            hero_id, perks = next(
                (hero_id, perks)
                for hero_id, perks in config["heroPerkList"].items()
                if isinstance(perks, list) and perks and perks[0].get("icon")
            )
            hero_info = next(item for item in config["heroList"] if item.get("id") == hero_id)
            perk_info = perks[0]
            hero_url = hero_info.get("smallIconUrl") or hero_info.get("icon")
            fake_client = FakeDashenApiClient()
            module = DashenMatchModule(api_client=fake_client)
            player = {
                "name": "Player#12345",
                "avatar": "https://example.com/avatar.png",
                "perks": [{"id": perk_info["id"]}],
            }

            await module._prefetch_match_render_images(
                {
                    "mapGuid": map_info["guid"],
                    "teammateList": [player],
                    "enemyList": [],
                }
            )

            self.assertEqual(_resolve_player_hero(config, player).get("heroGuid"), hero_info["heroGuid"])
            self.assertIn(map_info["icon"], fake_client.icon_urls)
            self.assertIn(hero_url, fake_client.icon_urls)
            self.assertIn(perk_info["icon"], fake_client.icon_urls)
            self.assertIn("https://example.com/avatar.png", fake_client.icon_urls)

        asyncio.run(run())

    def test_openai_compatible_retries_transient_503(self):
        async def run():
            module = DashenMatchModule(api_client=FakeDashenApiClient())
            request = httpx.Request("POST", "https://ai.example.com/v1/chat/completions")

            class FakeClient:
                def __init__(self):
                    self.calls = 0

                async def post(self, url, json, headers):
                    self.calls += 1
                    if self.calls < 3:
                        return httpx.Response(
                            503,
                            json={"error": {"message": "system cpu overloaded"}},
                            request=request,
                        )
                    return httpx.Response(200, json={"ok": True}, request=request)

            fake_client = FakeClient()

            class FakeClientContext:
                async def __aenter__(self):
                    return fake_client

                async def __aexit__(self, exc_type, exc, tb):
                    return False

            async def fake_sleep(_delay):
                return None

            original_factory = match_service.build_analysis_async_client
            original_sleep = match_service.asyncio.sleep
            match_service.build_analysis_async_client = lambda **_kwargs: FakeClientContext()
            match_service.asyncio.sleep = fake_sleep
            try:
                payload = await module._call_openai_compatible(
                    "https://ai.example.com/v1/chat/completions",
                    "secret-key",
                    {"model": "test", "messages": []},
                )
            finally:
                match_service.build_analysis_async_client = original_factory
                match_service.asyncio.sleep = original_sleep

            self.assertEqual(payload, {"ok": True})
            self.assertEqual(fake_client.calls, 3)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
