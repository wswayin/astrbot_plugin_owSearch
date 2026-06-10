from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from ..config import AiConfig
from ..models import MatchDetail, pick
from .match_utils import extract_player_rows, focus_player_row, summarize_match_for_text


@dataclass(frozen=True)
class AnalysisResult:
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    fallback_text: str = ""
    model: str = ""


def _chat_completion_url(base_url: str) -> str:
    base = str(base_url or "").rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _infer_model(config: AiConfig) -> str:
    if config.model:
        return config.model
    normalized = config.base_url.lower()
    if "deepseek" in normalized:
        return "deepseek-chat"
    if "googleapis.com" in normalized:
        return "gemini-3.1-flash-lite-preview"
    return "gpt-4o-mini"


def _clean_llm_text(text: Any) -> str:
    cleaned = str(text or "")
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"^```json\s*", "", cleaned.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    return cleaned


def _parse_json(text: Any) -> dict[str, Any] | None:
    cleaned = _clean_llm_text(text)
    candidates = [cleaned]
    candidates.extend(re.findall(r"\{.*\}", cleaned, flags=re.DOTALL))
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _extract_message(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                return str(message.get("content") or "")
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_message(data)
    return ""


def _build_prompt(detail: MatchDetail) -> str:
    rows = extract_player_rows(detail)
    focus = focus_player_row(detail, rows) or {}
    compact_rows = []
    for row in rows:
        compact_rows.append(
            {
                "side": row.get("side"),
                "name": row.get("name"),
                "role": row.get("role_type"),
                "hero": row.get("hero_name") or row.get("hero_guid"),
                "k": row.get("kill"),
                "a": row.get("assist"),
                "d": row.get("death"),
                "damage": row.get("hero_damage"),
                "healing": row.get("cure"),
                "mitigation": row.get("resist_damage"),
                "rank": row.get("rank_label"),
            }
        )
    return f"""
{detail.identity.full_id} 是本次查询的焦点玩家。

人格要求：
{detail.identity.full_id} 不一定打得好。请客观评价，必要时可以直接批评，但不要编造数据里没有的信息。

输出要求：
只输出合法 JSON，不要 Markdown，不要解释。字段必须是：
{{
  "score": "S/A/B/C/D",
  "verdict": "一句话判决",
  "highlights": ["最多3条亮点"],
  "problems": ["最多3条问题"],
  "advice": ["最多3条建议"],
  "meme_line": "一句短锐评"
}}

比赛摘要：
{summarize_match_for_text(detail)}

焦点玩家行：
{json.dumps(focus, ensure_ascii=False)}

全员数据：
{json.dumps(compact_rows, ensure_ascii=False)}
""".strip()


class AnalysisService:
    def __init__(self, config: AiConfig) -> None:
        self.config = config

    async def analyze(self, detail: MatchDetail) -> AnalysisResult:
        if not self.config.ready:
            return AnalysisResult(
                ok=False,
                fallback_text="AI 分析未启用或未配置 base_url / api_key。",
                model=_infer_model(self.config),
            )
        model = _infer_model(self.config)
        prompt = f"{self.config.persona_prompt.strip()}\n\n{_build_prompt(detail)}"
        payload = {
            "model": model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=float(self.config.timeout_seconds)) as client:
                response = await client.post(_chat_completion_url(self.config.base_url), json=payload, headers=headers)
                response.raise_for_status()
                raw = response.json()
        except Exception as exc:
            return AnalysisResult(ok=False, fallback_text=f"AI 分析生成失败：{type(exc).__name__}: {exc}", model=model)
        parsed = _parse_json(_extract_message(raw))
        if not parsed:
            return AnalysisResult(ok=False, fallback_text=f"AI 返回内容不是合法 JSON。模型：{model}", model=model)
        parsed.setdefault("score", "B")
        parsed.setdefault("verdict", pick(parsed, "general_summary", "summary", default="本局表现需要结合全员数据判断。"))
        parsed.setdefault("highlights", [])
        parsed.setdefault("problems", [])
        parsed.setdefault("advice", [])
        parsed.setdefault("meme_line", "")
        return AnalysisResult(ok=True, data=parsed, model=model)
