from __future__ import annotations

from pathlib import Path

try:
    from astrbot.api.event import AstrMessageEvent, filter
except ImportError:
    from astrbot.api.event import AstrBotEvent as AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from owsearch.commands.handler import OwCommandHandler
from owsearch.commands.reply_adapter import context_key_from_event, message_text_from_event
from owsearch.config import PluginConfig
from owsearch.models import ReplyItem


@register("astrbot_plugin_owSearch", "codex", "Overwatch player and match search through Dashen data.", "0.1.0")
class OwSearchPlugin(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.plugin_config = PluginConfig.from_mapping(config or {})
        plugin_root = Path(__file__).resolve().parent
        data_dir = self.plugin_config.resolve_storage_dir(plugin_root)
        self.handler = OwCommandHandler(self.plugin_config, data_dir)

    @filter.command("ow", alias={"守望"})
    async def ow(self, event: AstrMessageEvent):
        message = message_text_from_event(event)
        context_key = context_key_from_event(event)
        replies = await self.handler.handle(message, context_key)
        for reply in replies:
            yield self._to_astrbot_result(event, reply)

    def _to_astrbot_result(self, event: AstrBotEvent, reply: ReplyItem):
        if reply.kind == "image" and reply.path:
            return event.image_result(reply.path)
        return event.plain_result(reply.content)

    async def terminate(self):
        await self.handler.close()
