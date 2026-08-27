"""전역 설정 (DB 문서 §4.9, 백엔드 문서 §8.5).

`app_setting`은 거의 변하지 않고 거의 모든 요청이 읽는다. 프로세스 전역에 짧은 TTL
캐시를 둔다. 인스턴스가 여러 개이므로 TTL만큼 전파 지연이 있으며, 이는 모든 설정
항목에서 허용 가능하다 — 가입 잠금이 1분 늦게 반영되어도 아무 일도 일어나지 않는다.

**배포로만 바뀌는 값은 환경변수(`config/settings.py`), 운영 중 조정되는 값은 여기다.**
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy.orm import Session

from chalicelib.config.constants import SETTING_CACHE_TTL_SECONDS
from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.logging import get_logger, log_event
from chalicelib.core.timeutil import now_utc
from chalicelib.db import query as q
from chalicelib.db.models import AppSetting

logger = get_logger("setting")


class SettingKey:
    """시드된 10종 (DB 문서 §4.9). 문자열 리터럴을 코드에 흩지 않는다."""

    SIGNUP_OPEN: Final = "signup_open"
    NOTIFY_DEFAULT_TIME: Final = "notify_default_time"
    NOTIFY_CUTOFF_HOUR: Final = "notify_cutoff_hour"
    CARRYOVER_ALERT_DAYS: Final = "carryover_alert_days"
    ARCHIVE_SIZE: Final = "archive_size"
    ADMIN_CALENDAR_DAYS: Final = "admin_calendar_days"
    LOG_RETENTION_DAYS: Final = "log_retention_days"
    MEDIA_URL_TTL_SECONDS: Final = "media_url_ttl_seconds"
    MAINTENANCE_MODE: Final = "maintenance_mode"
    SESSION_TTL_DAYS: Final = "session_ttl_days"


#: 행이 없을 때 쓰는 값. DB 장애 중에도 첫 화면이 떠야 하므로(PRD §8.5) 필수다.
DEFAULTS: Final[dict[str, Any]] = {
    SettingKey.SIGNUP_OPEN: True,
    SettingKey.NOTIFY_DEFAULT_TIME: "07:30",
    SettingKey.NOTIFY_CUTOFF_HOUR: 21,
    SettingKey.CARRYOVER_ALERT_DAYS: 2,
    SettingKey.ARCHIVE_SIZE: 30,
    SettingKey.ADMIN_CALENDAR_DAYS: 7,
    SettingKey.LOG_RETENTION_DAYS: 180,
    SettingKey.MEDIA_URL_TTL_SECONDS: 900,
    SettingKey.MAINTENANCE_MODE: False,
    SettingKey.SESSION_TTL_DAYS: 90,
}

_VALUE_TYPES: Final[dict[str, type]] = {"string": str, "number": (int, float), "boolean": bool}  # type: ignore[dict-item]


@dataclass(slots=True)
class _Cache:
    values: dict[str, Any]
    expires_at: _dt.datetime


_cache: _Cache | None = None


def invalidate_cache() -> None:
    """설정 변경 직후 호출한다. 이 인스턴스만 즉시 반영되고 나머지는 TTL만큼 늦다."""
    global _cache
    _cache = None


def _load(session: Session) -> dict[str, Any]:
    rows = q.fetch(session, AppSetting, columns=["key", "value"])
    return {row["key"]: row["value"] for row in rows}


def _cached(session: Session) -> dict[str, Any]:
    global _cache
    now = now_utc()
    if _cache is not None and _cache.expires_at > now:
        return _cache.values
    try:
        values = _load(session)
    except Exception:
        # DB가 없어도 기본값으로 계속 간다. 첫 화면은 항상 뜬다.
        log_event(logger, "setting.load_failed", message="설정을 읽지 못해 기본값을 씁니다")
        return dict(DEFAULTS)
    _cache = _Cache(
        values={**DEFAULTS, **values},
        expires_at=now + _dt.timedelta(seconds=SETTING_CACHE_TTL_SECONDS),
    )
    return _cache.values


def get(session: Session, key: str) -> Any:
    return _cached(session).get(key, DEFAULTS.get(key))


def get_bool(session: Session, key: str) -> bool:
    return bool(get(session, key))


def get_int(session: Session, key: str) -> int:
    return int(get(session, key))


def get_str(session: Session, key: str) -> str:
    return str(get(session, key))


def list_all(session: Session) -> list[dict[str, Any]]:
    """관리자 설정 화면 (API 문서 §9.17). 캐시를 거치지 않는다 — 조작 화면은 실제 값을 본다."""
    rows = q.fetch(session, AppSetting, order_by=["key"])
    return [serialize_setting(row) for row in rows]


def serialize_setting(row: AppSetting) -> dict[str, Any]:
    from chalicelib.core.timeutil import format_rfc3339

    return {
        "key": row.key,
        "value": row.value,
        "value_type": row.value_type,
        "description": row.description,
        "is_mutable": row.is_mutable,
        "updated_at": format_rfc3339(row.updated_at),
    }


def update_many(session: Session, changes: dict[str, Any], *, actor_id: Any) -> list[dict[str, Any]]:
    """변경할 키만 담아 보낸다. 모르는 키·잠긴 키·타입 불일치는 각각 다른 코드로 거절한다."""
    existing = {row.key: row for row in q.fetch(session, AppSetting)}
    for key, value in changes.items():
        row = existing.get(key)
        if row is None:
            raise AppError(ErrorCode.SETTING_UNKNOWN_KEY, details={"key": key})
        if not row.is_mutable:
            raise AppError(ErrorCode.SETTING_IMMUTABLE, details={"key": key})
        expected = _VALUE_TYPES[row.value_type]
        # bool은 int의 하위 타입이므로 number 검사에서 먼저 걸러 낸다.
        if row.value_type == "number" and isinstance(value, bool):
            raise AppError(ErrorCode.VALIDATION_FAILED, doc_hint=f"{key}는 숫자여야 합니다")
        if not isinstance(value, expected):
            raise AppError(ErrorCode.VALIDATION_FAILED, doc_hint=f"{key}의 값 타입이 다릅니다")

    for key, value in changes.items():
        q.update(
            session,
            AppSetting,
            where={"key": key},
            values={"value": value, "updated_by": actor_id, "updated_at": now_utc()},
        )
    # Core UPDATE는 세션의 식별 맵을 갱신하지 않는다. 만료시키지 않으면 바로 아래
    # `list_all`이 방금 바꾼 값 대신 읽어 둔 옛 값을 돌려준다.
    session.expire_all()
    invalidate_cache()
    return list_all(session)


def maintenance_state() -> tuple[bool, str | None]:
    """점검 모드 판정 (백엔드 문서 §6 미들웨어 4번).

    이 시점에는 요청 세션이 아직 없다. 캐시가 살아 있으면 DB를 건드리지 않고, 캐시가
    비었을 때만(인스턴스당 TTL에 한 번) 짧은 세션을 직접 연다.
    """
    global _cache
    now = now_utc()
    if _cache is not None and _cache.expires_at > now:
        return bool(_cache.values.get(SettingKey.MAINTENANCE_MODE, False)), None

    from chalicelib.db.engine import open_session

    session = open_session()
    try:
        enabled = get_bool(session, SettingKey.MAINTENANCE_MODE)
    finally:
        session.close()
    return enabled, None
