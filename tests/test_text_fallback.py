import unittest

from owsearch.models import MatchSummary
from owsearch.renderers.text_fallback import match_list_text


class TextFallbackTests(unittest.TestCase):
    def test_match_list_text(self):
        summary = MatchSummary(
            match_id="m1",
            result=1,
            game_mode="SportPreset",
            team_score=3,
            opponent_score=1,
            kill=10,
            assist=4,
            death=2,
        )
        text = match_list_text([summary])
        self.assertIn("胜利", text)
        self.assertIn("10/4/2", text)


if __name__ == "__main__":
    unittest.main()
