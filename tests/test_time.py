import unittest

from owsearch.utils.time import format_timestamp


class TimeTests(unittest.TestCase):
    def test_format_timestamp_without_system_tzdata(self):
        self.assertRegex(format_timestamp(1777212060658), r"\d{2}-\d{2} \d{2}:\d{2}")


if __name__ == "__main__":
    unittest.main()
