from __future__ import annotations

from typing import Any

SENSITIVE_KEYS = {
    "token",
    "customer_token",
    "customertoken",
    "api_key",
    "apikey",
    "authorization",
    "gl-bigdata-auth-token",
    "cookie",
}


def mask_value(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= 8:
        return "***"
    return f"{text[:4]}...{text[-4:]}"


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower().replace("-", "_") in SENSITIVE_KEYS or key_text.lower() in SENSITIVE_KEYS:
                result[key] = mask_value(item)
            else:
                result[key] = redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value
