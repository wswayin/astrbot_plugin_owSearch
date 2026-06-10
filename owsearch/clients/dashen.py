from __future__ import annotations

from typing import Any

from ..config import DashenConfig
from ..constants import (
    DASHEN_CUSTOMER_API_BASE,
    DASHEN_SEARCH_BNET_ACCOUNT_URL,
)
from ..errors import DashenApiError
from .http import HttpJsonClient


def _season_params(season: int | None) -> dict[str, int]:
    return {} if season is None else {"season": int(season)}


def _payload_hint(message: str, code: Any) -> str:
    text = f"{message} {code}".lower()
    if any(key in text for key in ("token", "auth", "unauthorized", "forbidden", "登录", "鉴权", "权限")):
        return "请检查 Dashen token/role_id 是否过期或填错。"
    if any(key in text for key in ("not found", "不存在", "未找到", "无数据")):
        return "请确认 BattleTag 是否正确，玩家是否公开战绩，或稍后刷新缓存重试。"
    if any(key in text for key in ("limit", "rate", "频繁", "限流")):
        return "Dashen 接口可能限流，请稍后重试或降低并发。"
    return ""


class DashenClient:
    def __init__(self, config: DashenConfig) -> None:
        self.config = config
        self.http = HttpJsonClient(
            timeout_seconds=config.timeout_seconds,
            max_concurrent_requests=config.max_concurrent_requests,
        )

    async def close(self) -> None:
        await self.http.close()

    def _common_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json, text/plain, */*",
            "GL-ClientType": self.config.client_type,
            "Origin": self.config.origin,
            "Referer": self.config.referer,
            "User-Agent": self.config.user_agent,
        }

    def _auth_headers(self) -> dict[str, str]:
        headers = self._common_headers()
        headers.update(
            {
                "GL-Bigdata-Auth-Token": self.config.token,
                "GL-Bigdata-Dts": str(self.config.dts),
                "GL-Bigdata-Role-Id": str(self.config.role_id),
                "GL-Bigdata-Server": str(self.config.server),
            }
        )
        return headers

    @staticmethod
    def _ensure_ok(payload: dict[str, Any], *, operation: str) -> dict[str, Any]:
        code = payload.get("code")
        success = payload.get("success")
        if (code not in (None, 0, "0")) or (success is False):
            message = payload.get("message") or payload.get("msg") or f"{operation} 失败。"
            raise DashenApiError(
                str(message),
                code=f"dashen_{operation}_failed",
                hint=_payload_hint(str(message), code),
                details={"operation": operation, "upstream_code": code},
            )
        return payload

    async def search_bnet_account(self, bnet: str) -> dict[str, Any]:
        self.config.validate()
        normalized = str(bnet or "").replace("＃", "#").strip()
        payload = {
            "token": self.config.token,
            "roleId": self.config.role_id,
            "dts": self.config.dts,
            "server": self.config.server,
            "name": normalized,
        }
        result = await self.http.request_json(
            "POST",
            DASHEN_SEARCH_BNET_ACCOUNT_URL,
            headers={**self._common_headers(), "Content-Type": "application/json;charset=UTF-8"},
            json=payload,
            retries=1,
        )
        return self._ensure_ok(result, operation="search_bnet_account")

    async def query_card(self, customer_token: str) -> dict[str, Any]:
        return await self._get_customer("queryCard", {"token": customer_token}, operation="query_card")

    async def query_count_info(self, customer_token: str, game_mode: str, season: int | None = None) -> dict[str, Any]:
        params = {"gameMode": game_mode, "token": customer_token, **_season_params(season)}
        return await self._get_customer("queryCountInfo", params, operation="query_count_info")

    async def query_match_list(
        self,
        customer_token: str,
        game_mode: str,
        *,
        page: int = 1,
        season: int | None = None,
    ) -> dict[str, Any]:
        params = {
            "token": customer_token,
            "gameMode": game_mode,
            "page": max(1, int(page)),
            **_season_params(season),
        }
        return await self._get_customer("queryMatchList", params, operation="query_match_list")

    async def query_match_info(self, customer_token: str, match_id: str) -> dict[str, Any]:
        params = {"matchId": str(match_id), "token": customer_token}
        return await self._get_customer("queryMatchInfo", params, operation="query_match_info")

    async def fight_query_match_list(
        self,
        customer_token: str,
        game_mode: str,
        *,
        page: int = 1,
        season: int | None = None,
    ) -> dict[str, Any]:
        params = {
            "token": customer_token,
            "gameMode": game_mode,
            "page": max(1, int(page)),
            **_season_params(season),
        }
        return await self._get_customer("fight/queryMatchList", params, operation="fight_query_match_list")

    async def fight_query_match_info(self, customer_token: str, match_id: str) -> dict[str, Any]:
        params = {"matchId": str(match_id), "token": customer_token}
        return await self._get_customer("fight/queryMatchInfo", params, operation="fight_query_match_info")

    async def _get_customer(self, path: str, params: dict[str, Any], *, operation: str) -> dict[str, Any]:
        self.config.validate()
        result = await self.http.request_json(
            "GET",
            f"{DASHEN_CUSTOMER_API_BASE}/{path}",
            headers=self._auth_headers(),
            params=params,
            retries=1,
        )
        return self._ensure_ok(result, operation=operation)
