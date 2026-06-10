import asyncio
import base64
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from owsearch.overstats_bridge import OverstatsBridge
from owsearch.errors import OwSearchError
from owsearch.renderers.image_output import ImageFile
from overstats.src.modules.errors import ModuleError


class FakeGuessModule:
    async def query_guess_replies(self, query):
        return types.SimpleNamespace(
            replies=[
                {"type": "text", "data": "猜一下"},
                {
                    "type": "audio",
                    "media_type": "audio/ogg",
                    "base64": base64.b64encode(b"audio").decode("ascii"),
                },
            ]
        )


class MissingAssetGuessModule:
    async def query_guess_replies(self, query):
        raise ModuleError(
            error="ow_guess_type_unavailable",
            message="Question type requires the optional OW guess asset pack: map_music",
            status_code=400,
            details={
                "question_type": "map_music",
                "reason": "local_asset_pack_missing",
                "path": "missing/path",
            },
        )


class OverstatsBridgeAudioTests(unittest.TestCase):
    def test_guess_audio_reply_is_converted_to_wav_reply_item(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                bridge = object.__new__(OverstatsBridge)
                bridge.guess_module = FakeGuessModule()
                bridge.render_dir = root
                bridge.config = types.SimpleNamespace(render=types.SimpleNamespace(max_render_files=300))

                def fake_convert(data, output_dir, *, prefix, media_type):
                    self.assertEqual(data, b"audio")
                    self.assertEqual(media_type, "audio/ogg")
                    path = Path(output_dir) / f"{prefix}.wav"
                    path.write_bytes(b"RIFF" + b"x" * 80)
                    return ImageFile(path=path, media_type="audio/wav")

                with patch("owsearch.overstats_bridge.convert_audio_bytes_to_wav", side_effect=fake_convert):
                    replies = await bridge.guess("地图音乐")

                self.assertEqual([reply.kind for reply in replies], ["text", "audio"])
                self.assertEqual(replies[1].media_type, "audio/wav")
                self.assertTrue(Path(replies[1].path).exists())

        asyncio.run(run())

    def test_guess_missing_asset_pack_returns_actionable_hint(self):
        async def run():
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir) / "ow_guess_assets"
                bridge = object.__new__(OverstatsBridge)
                bridge.guess_module = MissingAssetGuessModule()
                bridge.guess_asset_root = root

                with self.assertRaises(OwSearchError) as raised:
                    await bridge.guess("地图音乐")

                text = str(raised.exception)
                self.assertIn("OW 猜题资源包未安装", text)
                self.assertIn(str(root), text)
                self.assertIn("ow_guess.asset_root", text)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
