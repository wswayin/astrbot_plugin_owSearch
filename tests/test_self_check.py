import asyncio
import unittest
from pathlib import Path

from owsearch.self_check import run_self_check


class SelfCheckTests(unittest.TestCase):
    def test_self_check_passes(self):
        async def run():
            report = await run_self_check(Path.cwd())
            self.assertTrue(report.ok, report.to_text())

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
