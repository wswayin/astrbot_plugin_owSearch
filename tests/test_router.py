import unittest

from owsearch.router import parse_command


class RouterTests(unittest.TestCase):
    def test_courtroom(self):
        intent = parse_command("/ow 开庭 Player#12345")
        self.assertEqual(intent.name, "courtroom")
        self.assertEqual(intent.bnet_id, "Player#12345")
        self.assertEqual(intent.index, 1)
        self.assertTrue(intent.analyze)

    def test_courtroom_index(self):
        intent = parse_command("/ow 开庭 Player#12345 2")
        self.assertEqual(intent.name, "courtroom")
        self.assertEqual(intent.bnet_id, "Player#12345")
        self.assertEqual(intent.index, 2)
        self.assertTrue(intent.show_all_heroes)
        self.assertTrue(intent.analyze)

    def test_courtroom_direct_command(self):
        intent = parse_command("/开庭 Player#12345 3")
        self.assertEqual(intent.name, "courtroom")
        self.assertEqual(intent.bnet_id, "Player#12345")
        self.assertEqual(intent.index, 3)

    def test_analysis_with_player_aliases_courtroom(self):
        intent = parse_command("/ow 分析 Player#12345 2")
        self.assertEqual(intent.name, "courtroom")
        self.assertEqual(intent.bnet_id, "Player#12345")
        self.assertEqual(intent.index, 2)

    def test_context_detail_index(self):
        intent = parse_command("/ow 详情 2")
        self.assertEqual(intent.name, "match_detail")
        self.assertEqual(intent.index, 2)
        self.assertEqual(intent.bnet_id, "")

    def test_analysis_index(self):
        intent = parse_command("/ow 分析 1")
        self.assertEqual(intent.name, "analysis")
        self.assertEqual(intent.index, 1)
        self.assertTrue(intent.show_all_heroes)
        self.assertTrue(intent.analyze)

    def test_shortcut_index(self):
        intent = parse_command("/ow 3**")
        self.assertEqual(intent.name, "match_detail")
        self.assertEqual(intent.index, 3)
        self.assertTrue(intent.show_all_heroes)
        self.assertTrue(intent.analyze)

    def test_debug_config(self):
        intent = parse_command("/ow debug 配置")
        self.assertEqual(intent.name, "debug_config")

    def test_debug_matches_limit(self):
        intent = parse_command("/ow debug 战绩 Player#12345 5")
        self.assertEqual(intent.name, "debug_matches")
        self.assertEqual(intent.bnet_id, "Player#12345")
        self.assertEqual(intent.limit, 5)

    def test_debug_live_limit(self):
        intent = parse_command("/ow debug 接口 Player#12345 4")
        self.assertEqual(intent.name, "debug_live")
        self.assertEqual(intent.bnet_id, "Player#12345")
        self.assertEqual(intent.limit, 4)

    def test_debug_render(self):
        intent = parse_command("/ow debug 图片")
        self.assertEqual(intent.name, "debug_render")

    def test_match_list_limit(self):
        intent = parse_command("/ow 战绩 Player#12345 12")
        self.assertEqual(intent.name, "match_list")
        self.assertEqual(intent.bnet_id, "Player#12345")
        self.assertEqual(intent.limit, 12)


if __name__ == "__main__":
    unittest.main()
