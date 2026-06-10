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

    def test_sameplay_list(self):
        intent = parse_command("/ow 同玩 Alpha#12345 Bravo#67890 12")
        self.assertEqual(intent.name, "sameplay_list")
        self.assertEqual(intent.bnet_id, "Alpha#12345")
        self.assertEqual(intent.bnet_id2, "Bravo#67890")
        self.assertEqual(intent.limit, 12)

    def test_sameplay_detail(self):
        intent = parse_command("/ow 同玩详情 Alpha#12345 Bravo#67890 2**")
        self.assertEqual(intent.name, "sameplay_detail")
        self.assertEqual(intent.bnet_id, "Alpha#12345")
        self.assertEqual(intent.bnet_id2, "Bravo#67890")
        self.assertEqual(intent.index, 2)
        self.assertTrue(intent.show_all_heroes)
        self.assertTrue(intent.analyze)

    def test_sameplay_court(self):
        intent = parse_command("/ow 同玩开庭 Alpha#12345 Bravo#67890")
        self.assertEqual(intent.name, "sameplay_detail")
        self.assertEqual(intent.index, 1)
        self.assertTrue(intent.show_all_heroes)
        self.assertTrue(intent.analyze)

    def test_summary_today(self):
        intent = parse_command("/ow 总结 Player#12345")
        self.assertEqual(intent.name, "summary")
        self.assertEqual(intent.bnet_id, "Player#12345")
        self.assertEqual(intent.scope, "today")

    def test_summary_yesterday(self):
        intent = parse_command("/ow 昨日总结 Player#12345")
        self.assertEqual(intent.name, "summary")
        self.assertEqual(intent.bnet_id, "Player#12345")
        self.assertEqual(intent.scope, "yesterday")

    def test_summary_week(self):
        intent = parse_command("/ow summary Player#12345 week")
        self.assertEqual(intent.name, "summary")
        self.assertEqual(intent.bnet_id, "Player#12345")
        self.assertEqual(intent.scope, "week")

    def test_quick_strength(self):
        intent = parse_command("/ow 快速强度 Player#12345 12")
        self.assertEqual(intent.name, "quick_strength")
        self.assertEqual(intent.bnet_id, "Player#12345")
        self.assertEqual(intent.limit, 12)

    def test_competitive_strength(self):
        intent = parse_command("/ow 竞技强度 Player#12345 8")
        self.assertEqual(intent.name, "competitive_strength")
        self.assertEqual(intent.bnet_id, "Player#12345")
        self.assertEqual(intent.limit, 8)

    def test_rank_history(self):
        intent = parse_command("/ow 段位历史 Player#12345 15 22")
        self.assertEqual(intent.name, "rank_history")
        self.assertEqual(intent.bnet_id, "Player#12345")
        self.assertEqual(intent.start_season, 15)
        self.assertEqual(intent.end_season, 22)

    def test_rank_leaderboard(self):
        intent = parse_command("/ow 省榜 北京 输出")
        self.assertEqual(intent.name, "rank_leaderboard")
        self.assertEqual(intent.province, "北京")
        self.assertEqual(intent.role, "输出")

    def test_hero_leaderboard(self):
        intent = parse_command("/ow 英雄榜 北京 猎空 开放")
        self.assertEqual(intent.name, "hero_leaderboard")
        self.assertEqual(intent.province, "北京")
        self.assertEqual(intent.hero, "猎空")
        self.assertEqual(intent.mode, "开放")

    def test_hero_treemap(self):
        intent = parse_command("/ow 英雄占比 Player#12345 快速 22")
        self.assertEqual(intent.name, "hero_treemap")
        self.assertEqual(intent.bnet_id, "Player#12345")
        self.assertEqual(intent.mode, "quick")
        self.assertEqual(intent.start_season, 22)

    def test_hero_pick_rate_ranking(self):
        intent = parse_command("/ow 登场率 竞技 钻石")
        self.assertEqual(intent.name, "hero_pick_rate")
        self.assertEqual(intent.view, "ranking")
        self.assertEqual(intent.mode, "competitive")
        self.assertEqual(intent.mmr, "Diamond")

    def test_hero_pick_rate_history(self):
        intent = parse_command("/ow 登场率历史 安娜 竞技 钻石 18")
        self.assertEqual(intent.name, "hero_pick_rate")
        self.assertEqual(intent.view, "history")
        self.assertEqual(intent.hero, "安娜")
        self.assertEqual(intent.mode, "competitive")
        self.assertEqual(intent.mmr, "Diamond")
        self.assertEqual(intent.history_limit, 18)

    def test_hero_perk(self):
        intent = parse_command("/ow 威能 安娜")
        self.assertEqual(intent.name, "hero_perk")
        self.assertEqual(intent.hero, "安娜")

    def test_hero_wiki_question(self):
        intent = parse_command("/ow 英雄资料 安娜 技能冷却是多少")
        self.assertEqual(intent.name, "hero_wiki")
        self.assertEqual(intent.hero, "安娜")
        self.assertEqual(intent.question, "技能冷却是多少")

    def test_shop(self):
        intent = parse_command("/ow 商店")
        self.assertEqual(intent.name, "shop")

    def test_patch_notes(self):
        intent = parse_command("/ow 补丁 大补丁")
        self.assertEqual(intent.name, "patch_notes")
        self.assertEqual(intent.patch_kind, "big")

    def test_esports(self):
        intent = parse_command("/ow 电竞")
        self.assertEqual(intent.name, "esports")

    def test_identity_search(self):
        intent = parse_command("/ow 反查 123456789 10")
        self.assertEqual(intent.name, "identity_search")
        self.assertEqual(intent.bnet_id, "123456789")
        self.assertEqual(intent.limit, 10)

    def test_ow_guess_is_removed(self):
        intent = parse_command("/ow 猜 英雄图标")
        self.assertEqual(intent.name, "help")

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

    def test_debug_ai(self):
        intent = parse_command("/ow debug ai")
        self.assertEqual(intent.name, "debug_ai")

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
        intent = parse_command("/ow debug 图片 Player#12345 2")
        self.assertEqual(intent.name, "debug_render")
        self.assertEqual(intent.bnet_id, "Player#12345")
        self.assertEqual(intent.index, 2)

    def test_match_list_limit(self):
        intent = parse_command("/ow 战绩 Player#12345 12")
        self.assertEqual(intent.name, "match_list")
        self.assertEqual(intent.bnet_id, "Player#12345")
        self.assertEqual(intent.limit, 12)


if __name__ == "__main__":
    unittest.main()
