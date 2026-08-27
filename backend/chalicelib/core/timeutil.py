"""시간을 만드는 **유일한 모듈** (백엔드 문서 §8.4).

다른 파일에서 현재 시각을 직접 얻는 것은 ruff 규칙(TID251)으로 금지되어 있다.
이유는 하나다 — Lambda의 TZ는 UTC이고 이 제품의 업무 날짜는 KST 캘린더다(DP-3).
날짜 계산이 여러 파일에 흩어지면 KST 09:00 이전에 하루가 어긋나는 버그가
어디서 났는지 찾을 수 없다.

테스트는 `freeze_time()`으로 이 모듈을 고정해 날짜 경계를 검증한다.
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final
from zoneinfo import ZoneInfo

from chalicelib.config.constants import KST_TZ_NAME, KST_WEEKDAY_LABELS

KST: Final = ZoneInfo(KST_TZ_NAME)
UTC: Final = _dt.UTC

#: 테스트가 고정하는 지점. 프로덕션에서는 항상 None이다.
_frozen_now: _dt.datetime | None = None


def now_utc() -> _dt.datetime:
    """현재 시각(UTC, tz-aware). 저장·응답의 기준이다."""
    if _frozen_now is not None:
        return _frozen_now
    return _dt.datetime.now(tz=UTC)


def now_kst() -> _dt.datetime:
    return now_utc().astimezone(KST)


def kst_today() -> _dt.date:
    """서버 기준 **KST 오늘**. 관람일·달력·통계의 기준 날짜다 (PRD §6.1)."""
    return now_kst().date()


def to_kst(value: _dt.datetime) -> _dt.datetime:
    """naive 값은 UTC로 간주한다 — DB 세션 TZ가 UTC 고정이기 때문이다 (DB 문서 §2)."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(KST)


def to_utc(value: _dt.datetime) -> _dt.datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def kst_datetime(day: _dt.date, time_of_day: _dt.time) -> _dt.datetime:
    """KST 캘린더의 (날짜, 시각)을 UTC 시각으로 바꾼다. 알림 예약에 쓴다."""
    return _dt.datetime.combine(day, time_of_day, tzinfo=KST).astimezone(UTC)


# ── 표시 문자열 ────────────────────────────────────────────────────────────
# 서버가 완성해서 준다. 요일 로케일 처리를 클라이언트에 분산시키지 않는다(API 문서 §6.1).


def date_label(day: _dt.date) -> str:
    """`2026. 08. 27. 목` — A 첫 화면의 오늘 표시."""
    return f"{day.year}. {day.month:02d}. {day.day:02d}. {KST_WEEKDAY_LABELS[day.weekday()]}"


def carried_over_label(exhibition_date: _dt.date) -> str:
    """`8월 30일의 전시` — 연장 중일 때 발행일을 병기하는 문구 (PRD §4.3)."""
    return f"{exhibition_date.month}월 {exhibition_date.day}일의 전시"


# ── 파싱·직렬화 ────────────────────────────────────────────────────────────


def parse_date(value: str) -> _dt.date | None:
    """`YYYY-MM-DD`. 형식이 아니면 None — 호출부가 부재/검증 실패를 고른다."""
    try:
        return _dt.date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def parse_time_of_day(value: str) -> _dt.time | None:
    """`HH:MM` 24시간 (KST). 알림 시각 전용 (API 문서 §2.1)."""
    if not isinstance(value, str) or len(value) != 5 or value[2] != ":":
        return None
    try:
        hour, minute = int(value[:2]), int(value[3:])
    except ValueError:
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return _dt.time(hour=hour, minute=minute)


def format_time_of_day(value: _dt.time) -> str:
    return f"{value.hour:02d}:{value.minute:02d}"


def format_rfc3339(value: _dt.datetime | None) -> str | None:
    """`2026-08-27T22:30:00Z`. 응답의 모든 시각이 이 형식이다 (API 문서 §2.1)."""
    if value is None:
        return None
    return to_utc(value).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def format_date(value: _dt.date | None) -> str | None:
    return value.isoformat() if value is not None else None


def date_range(start: _dt.date, end: _dt.date) -> list[_dt.date]:
    """포함 구간의 날짜 시리즈. 달력·통계가 "모든 날짜를 빠짐없이" 반환하는 근거다."""
    if end < start:
        return []
    return [start + _dt.timedelta(days=offset) for offset in range((end - start).days + 1)]


def week_start(day: _dt.date) -> _dt.date:
    """그 주의 월요일. 주간 지표의 기준이다 (PRD 부록 B)."""
    return day - _dt.timedelta(days=day.weekday())


@contextmanager
def freeze_time(value: _dt.datetime) -> Iterator[_dt.datetime]:
    """테스트 전용. 날짜 경계 검증에 쓴다 (백엔드 문서 §8.4·§12)."""
    global _frozen_now
    previous = _frozen_now
    _frozen_now = to_utc(value)
    try:
        yield _frozen_now
    finally:
        _frozen_now = previous
