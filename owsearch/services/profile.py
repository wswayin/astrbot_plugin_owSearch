from __future__ import annotations

import asyncio
from typing import Any

from ..clients.dashen import DashenClient
from ..models import PlayerIdentity, PlayerProfile, RoleStat
from .identity import IdentityService


def _data(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("data", payload)
    return value if isinstance(value, dict) else {}


class ProfileService:
    def __init__(self, client: DashenClient, identity: IdentityService) -> None:
        self.client = client
        self.identity = identity

    async def get_profile(self, bnet_id: str, *, refresh: bool = False) -> PlayerProfile:
        player = await self.identity.resolve_bnet(bnet_id, refresh=refresh)
        card_task = self.client.query_card(player.customer_token)
        count_task = self.client.query_count_info(player.customer_token, "sport")
        card_payload, count_payload = await asyncio.gather(card_task, count_task)
        merged_identity = self._merge_card(player, _data(card_payload))
        count_data = _data(count_payload)
        guide = count_data.get("guideCountData") or []
        role_stats = [RoleStat.from_payload(item) for item in guide if isinstance(item, dict)]
        summary = count_data.get("presetsSummaryData") if isinstance(count_data.get("presetsSummaryData"), dict) else {}
        return PlayerProfile(
            identity=merged_identity,
            role_stats=role_stats,
            summary=dict(summary or {}),
            card_raw=card_payload,
            count_raw=count_payload,
        )

    @staticmethod
    def _merge_card(player: PlayerIdentity, card: dict[str, Any]) -> PlayerIdentity:
        if not card:
            return player
        return PlayerIdentity(
            query=player.query,
            full_id=str(card.get("name") or player.full_id),
            bnet_id=str(card.get("bnetId") or player.bnet_id),
            customer_token=str(card.get("customerToken") or player.customer_token),
            icon=str(card.get("icon") or player.icon),
            title=str(card.get("title") or player.title),
            level=int(card.get("level") or player.level or 0),
            game_time=str(card.get("gameTime") or player.game_time),
            raw={**player.raw, **card},
        )
