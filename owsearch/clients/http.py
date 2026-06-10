from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ..errors import DashenApiError


def _response_snippet(response: httpx.Response | None, limit: int = 240) -> str:
    if response is None:
        return ""
    text = str(response.text or "").replace("\n", " ").strip()
    return text[:limit]


def _http_hint(status_code: int) -> str:
    if status_code in {401, 403}:
        return "请检查 dashen.token、dashen.role_id、server、dts 是否仍然有效，token 可能已过期。"
    if status_code == 429:
        return "Dashen 接口触发限流，请降低并发或稍后重试。"
    if 500 <= status_code < 600:
        return "Dashen 上游服务异常，可以稍后重试。"
    return ""


class HttpJsonClient:
    def __init__(self, *, timeout_seconds: int = 20, max_concurrent_requests: int = 2) -> None:
        self.timeout = httpx.Timeout(float(timeout_seconds))
        self._client = httpx.AsyncClient(timeout=self.timeout)
        self._semaphore = asyncio.Semaphore(max(1, int(max_concurrent_requests)))

    async def close(self) -> None:
        await self._client.aclose()

    async def request_json(self, method: str, url: str, *, retries: int = 1, **kwargs: Any) -> dict[str, Any]:
        last_exc: Exception | None = None
        attempts = max(1, int(retries) + 1)
        for attempt in range(attempts):
            try:
                async with self._semaphore:
                    response = await self._client.request(method, url, **kwargs)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise DashenApiError("Dashen 返回了无法识别的数据。", code="invalid_payload")
                return payload
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response is not None else 0
                raise DashenApiError(
                    f"Dashen 请求失败：HTTP {status}",
                    code="http_error",
                    hint=_http_hint(status),
                    details={"status_code": status, "body": _response_snippet(exc.response)},
                ) from exc
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                if attempt + 1 >= attempts:
                    break
                await asyncio.sleep(0.4 * (attempt + 1))
            except ValueError as exc:
                raise DashenApiError(
                    "Dashen 返回的不是 JSON。",
                    code="invalid_json",
                    hint="可能是上游返回了错误页、网关页或登录拦截页。",
                ) from exc
        raise DashenApiError(
            f"Dashen 请求超时或网络失败：{type(last_exc).__name__}",
            code="network_error",
            hint="请检查网络、代理、服务器到 datamsapi.ds.163.com 的连通性，或调高 dashen.timeout_seconds。",
        ) from last_exc
