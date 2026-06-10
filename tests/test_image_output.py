import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from owsearch.renderers.audio_output import convert_audio_bytes_to_wav, convert_audio_file_to_wav
from owsearch.renderers.image_output import cleanup_render_dir, save_image


class ImageOutputTests(unittest.TestCase):
    def test_cleanup_render_dir_keeps_newest_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for idx in range(25):
                path = root / f"old_{idx:02d}.png"
                path.write_bytes(b"x")
            removed = cleanup_render_dir(root, max_files=20)
            self.assertEqual(removed, 5)
            self.assertEqual(len(list(root.glob("*.png"))), 20)

    def test_save_image_writes_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image = Image.new("RGB", (80, 40), (20, 30, 40))
            saved = save_image(image, Path(temp_dir), prefix="unit", max_bytes=5 * 1024 * 1024)
            self.assertTrue(saved.path.exists())
            self.assertEqual(saved.media_type, "image/png")

    def test_convert_audio_file_to_wav_runs_ffmpeg(self):
        def fake_run(command, **kwargs):
            Path(command[-1]).write_bytes(b"RIFF" + b"x" * 80)
            return types.SimpleNamespace(returncode=0, stderr="", stdout="")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.ogg"
            source.write_bytes(b"ogg")
            with patch("owsearch.renderers.audio_output._resolve_ffmpeg_executable", return_value="ffmpeg"):
                with patch("owsearch.renderers.audio_output.subprocess.run", side_effect=fake_run) as run:
                    saved = convert_audio_file_to_wav(source, root, prefix="unit")

            command = run.call_args.args[0]
            self.assertEqual(saved.media_type, "audio/wav")
            self.assertEqual(saved.path.suffix, ".wav")
            self.assertTrue(saved.path.exists())
            self.assertIn("-ac", command)
            self.assertIn("1", command)
            self.assertIn("-ar", command)
            self.assertIn("16000", command)

    def test_convert_audio_bytes_to_wav_removes_source_and_keeps_output(self):
        def fake_run(command, **kwargs):
            Path(command[-1]).write_bytes(b"RIFF" + b"x" * 80)
            return types.SimpleNamespace(returncode=0, stderr="", stdout="")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with patch("owsearch.renderers.audio_output._resolve_ffmpeg_executable", return_value="ffmpeg"):
                with patch("owsearch.renderers.audio_output.subprocess.run", side_effect=fake_run):
                    saved = convert_audio_bytes_to_wav(b"audio", root, prefix="unit", media_type="audio/ogg")

            self.assertTrue(saved.path.exists())
            self.assertEqual(saved.media_type, "audio/wav")
            self.assertEqual(len(list(root.glob("*_source_*.ogg"))), 0)


if __name__ == "__main__":
    unittest.main()
