"""구조화 로깅 (백엔드 문서 §8.3).

JSON 한 줄. 필수 필드는 시각·수준·요청 ID·경로·메서드·상태·소요시간·행위자·이벤트다.

**마스킹은 로거 필터가 자동 수행한다.** 호출부의 주의에 의존하지 않는다 — 주의는
언젠가 빠지고, 빠진 그 한 줄이 전화번호를 CloudWatch에 영구히 남긴다.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from typing import Any, Final

from chalicelib.config.settings import settings
from chalicelib.core.context import current_or_none
from chalicelib.core.timeutil import format_rfc3339, now_utc

#: 값을 통째로 지우는 키. 부분 마스킹조차 하지 않는다.
REDACTED_KEYS: Final = frozenset(
    {
        "password",
        "current_password",
        "new_password",
        "initial_password",
        "password_hash",
        "token",
        "jwt",
        "authorization",
        "cookie",
        "set-cookie",
        "secret",
        "jwt_secret",
        "p256dh",
        "auth",
        "endpoint",
        "vapid_private_key",
        "body",
        "raw_body",
        "image_bytes",
    }
)

#: 부분 마스킹 대상 키
PHONE_KEYS: Final = frozenset({"phone", "phone_number", "throttle_key", "curator_phone"})

REDACTION: Final = "[redacted]"

#: 본문 어디에 섞여 있든 잡는다. 하이픈 유무를 모두 포함한다.
_PHONE_IN_TEXT: Final = re.compile(r"01\d[-\s]?\d{3,4}[-\s]?(\d{4})")
_MAX_VALUE_LENGTH: Final = 512


def _mask_phone_text(value: str) -> str:
    return _PHONE_IN_TEXT.sub(lambda m: f"010-****-{m.group(1)}", value)


def _scrub(key: str | None, value: Any, depth: int = 0) -> Any:
    """키 이름과 값 모양을 함께 본다. 어느 한쪽만 보면 반드시 새는 경로가 남는다."""
    if depth > 4:
        return "[truncated]"

    lowered = key.lower() if key else ""
    if lowered in REDACTED_KEYS:
        return REDACTION

    if isinstance(value, dict):
        return {str(k): _scrub(str(k), v, depth + 1) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [_scrub(key, item, depth + 1) for item in value]
    if isinstance(value, bytes | bytearray | memoryview):
        return f"[binary {len(value)} bytes]"
    if isinstance(value, str):
        masked = _mask_phone_text(value)
        if lowered in PHONE_KEYS:
            masked = _mask_phone_text(masked if masked != value else value)
            if masked == value:
                # 이미 정규화된 숫자열이라 정규식이 잡지 못한 경우
                masked = f"{value[:3]}-****-{value[-4:]}" if len(value) >= 7 else REDACTION
        if len(masked) > _MAX_VALUE_LENGTH:
            return masked[:_MAX_VALUE_LENGTH] + "…"
        return masked
    return value


class SensitiveDataFilter(logging.Filter):
    """모든 레코드를 통과시키되 내용은 걸러 낸다."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _scrub(None, record.getMessage())
        record.args = None
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            record.fields = _scrub(None, fields)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        context = current_or_none()
        payload: dict[str, Any] = {
            "time": format_rfc3339(now_utc()),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.name),
            "message": record.getMessage(),
            "request_id": context.request_id if context else None,
            "method": context.method if context else None,
            "path": context.path if context else None,
            "actor_id": str(context.actor_id) if context and context.actor_id else None,
            "actor_role": context.actor_role if context else None,
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


_configured = False


def configure_logging() -> None:
    """모듈 로드 시 1회. Lambda가 기본으로 붙이는 핸들러를 우리 것으로 교체한다."""
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(SensitiveDataFilter())

    root = logging.getLogger("gallery_k")
    root.handlers = [handler]
    root.setLevel(settings.log_level)
    root.propagate = False
    _configured = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(f"gallery_k.{name}")


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    message: str = "",
    **fields: Any,
) -> None:
    """이벤트 이름을 1급 필드로 둔다. 로그 검색이 문자열 매칭이 되지 않게 한다."""
    logger.log(level, message or event, extra={"event": event, "fields": fields})
