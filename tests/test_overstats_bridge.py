import unittest

from overstats.src.modules.errors import ModuleError
from owsearch.overstats_bridge import _module_error_to_owsearch


class OverstatsBridgeErrorTests(unittest.TestCase):
    def test_match_index_error_with_empty_matches_is_translated(self):
        exc = ModuleError(
            error="match_index_out_of_range",
            message="Match index out of range: 0",
            hint="Use an index from 0 to 0.",
            details={"index": 0, "match_count": 0},
        )

        translated = _module_error_to_owsearch(exc, requested_index=1)

        self.assertEqual(translated.code, "match_index_out_of_range")
        self.assertIn("没有找到可用的最近对局", translated.message)
        self.assertIn("0 条", translated.hint)

    def test_match_index_error_with_short_match_list_is_translated(self):
        exc = ModuleError(
            error="match_index_out_of_range",
            message="Match index out of range: 1",
            hint="Use an index from 0 to 0.",
            details={"index": 1, "match_count": 1},
        )

        translated = _module_error_to_owsearch(exc, requested_index=2)

        self.assertEqual(translated.code, "match_index_out_of_range")
        self.assertIn("只有 1 场", translated.message)
        self.assertIn("第 2 场", translated.message)


if __name__ == "__main__":
    unittest.main()
