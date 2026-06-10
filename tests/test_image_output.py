import tempfile
import unittest
from pathlib import Path

from PIL import Image

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


if __name__ == "__main__":
    unittest.main()
