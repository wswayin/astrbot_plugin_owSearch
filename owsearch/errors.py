from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OwSearchError(Exception):
    message: str
    hint: str = ""
    code: str = "owsearch_error"
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        if self.hint:
            return f"{self.message}\n{self.hint}"
        return self.message


class ConfigError(OwSearchError):
    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message=message, hint=hint, code="config_error")


class DashenApiError(OwSearchError):
    def __init__(self, message: str, *, code: str = "dashen_api_error", hint: str = "", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, hint=hint, code=code, details=details or {})


class NotFoundError(OwSearchError):
    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message=message, hint=hint, code="not_found")


class RenderError(OwSearchError):
    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message=message, hint=hint, code="render_error")
