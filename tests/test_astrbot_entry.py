import asyncio
import importlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest


class FakeStar:
    def __init__(self, context):
        self.context = context


class FakeFilter:
    @staticmethod
    def command(name, alias=None):
        def decorator(func):
            func._astrbot_command = name
            func._astrbot_alias = set(alias or [])
            return func

        return decorator


def fake_register(name, author, desc, version):
    def decorator(cls):
        cls._astrbot_register = {
            "name": name,
            "author": author,
            "desc": desc,
            "version": version,
        }
        return cls

    return decorator


class FakeEvent:
    message_str = "/ow"

    def plain_result(self, text):
        return ("text", text)

    def image_result(self, path):
        return ("image", path)


class AstrBotEntryTests(unittest.TestCase):
    def setUp(self):
        self.original_modules = {name: sys.modules.get(name) for name in list(sys.modules) if name.startswith("astrbot")}
        event_mod = types.ModuleType("astrbot.api.event")
        event_mod.AstrMessageEvent = FakeEvent
        event_mod.filter = FakeFilter
        star_mod = types.ModuleType("astrbot.api.star")
        star_mod.Context = object
        star_mod.Star = FakeStar
        star_mod.register = fake_register
        sys.modules["astrbot"] = types.ModuleType("astrbot")
        sys.modules["astrbot.api"] = types.ModuleType("astrbot.api")
        sys.modules["astrbot.api.event"] = event_mod
        sys.modules["astrbot.api.star"] = star_mod
        sys.modules.pop("main", None)

    def tearDown(self):
        sys.modules.pop("main", None)
        for name in list(sys.modules):
            if name.startswith("astrbot"):
                sys.modules.pop(name, None)
        for name, module in self.original_modules.items():
            if module is not None:
                sys.modules[name] = module

    def test_main_registers_ow_command_alias(self):
        main = importlib.import_module("main")
        self.assertEqual(main.OwSearchPlugin._astrbot_register["name"], "astrbot_plugin_owSearch")
        self.assertEqual(main.OwSearchPlugin.ow._astrbot_command, "ow")
        self.assertIn("守望", main.OwSearchPlugin.ow._astrbot_alias)

    def test_main_imports_when_plugin_root_is_not_on_sys_path(self):
        root = Path.cwd().resolve()
        saved_path = list(sys.path)
        sys.modules.pop("main", None)
        try:
            sys.path = [entry for entry in sys.path if entry and Path(entry).resolve() != root]
            spec = importlib.util.spec_from_file_location("main", root / "main.py")
            self.assertIsNotNone(spec)
            module = importlib.util.module_from_spec(spec)
            sys.modules["main"] = module
            spec.loader.exec_module(module)
            self.assertEqual(module.OwSearchPlugin._astrbot_register["name"], "astrbot_plugin_owSearch")
            self.assertIn(str(root), sys.path)
        finally:
            sys.path = saved_path
            sys.modules.pop("main", None)

    def test_plugin_help_reply(self):
        async def run():
            main = importlib.import_module("main")
            with tempfile.TemporaryDirectory() as temp_dir:
                plugin = main.OwSearchPlugin(context=object(), config={"storage_dir": temp_dir})
                try:
                    replies = []
                    async for item in plugin.ow(FakeEvent()):
                        replies.append(item)
                    self.assertEqual(replies[0][0], "text")
                    self.assertIn("守望查询", replies[0][1])
                finally:
                    await plugin.terminate()

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
