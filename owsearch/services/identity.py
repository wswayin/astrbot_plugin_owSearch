from __future__ import annotations

from ..cache.identity_store import IdentityStore
from ..clients.dashen import DashenClient
from ..errors import NotFoundError
from ..models import PlayerIdentity


class IdentityService:
    def __init__(self, client: DashenClient, store: IdentityStore) -> None:
        self.client = client
        self.store = store

    async def resolve_bnet(self, bnet_id: str, *, refresh: bool = False) -> PlayerIdentity:
        query = str(bnet_id or "").replace("＃", "#").strip()
        if not query:
            raise NotFoundError("缺少玩家守望 ID。", "示例：/ow 开庭 Player#12345")
        if not refresh:
            cached = self.store.get(query)
            if cached and cached.customer_token:
                return cached
        payload = await self.client.search_bnet_account(query)
        identity = PlayerIdentity.from_search_payload(query, payload)
        if not identity.customer_token:
            raise NotFoundError(
                f"没有找到玩家：{query}",
                "请确认大小写和 # 后数字，且玩家公开战绩可被大神查询到。",
            )
        self.store.put(identity)
        return identity

    def clear(self, bnet_id: str) -> None:
        self.store.clear(bnet_id)
