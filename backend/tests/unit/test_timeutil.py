"""시간 모듈 — 날짜 경계 (백엔드 문서 §8.4·§12)."""

from __future__ import annotations

import datetime as dt

from chalicelib.core import timeutil


def test_kst_today_flips_at_kst_midnight_not_utc() -> None:
    """UTC 15:00 = KST 익일 00:00. Lambda TZ가 UTC라 여기서 하루가 어긋난다."""
    with timeutil.freeze_time(dt.datetime(2026, 8, 27, 14, 59, tzinfo=dt.UTC)):
        assert timeutil.kst_today() == dt.date(2026, 8, 27)
    with timeutil.freeze_time(dt.datetime(2026, 8, 27, 15, 0, tzinfo=dt.UTC)):
        assert timeutil.kst_today() == dt.date(2026, 8, 28)


def test_kst_datetime_converts_notify_time_to_utc() -> None:
    scheduled = timeutil.kst_datetime(dt.date(2026, 8, 27), dt.time(7, 30))
    assert scheduled == dt.datetime(2026, 8, 26, 22, 30, tzinfo=dt.UTC)


def test_labels_are_server_completed_strings() -> None:
    assert timeutil.date_label(dt.date(2026, 8, 27)) == "2026. 08. 27. 목"
    assert timeutil.carried_over_label(dt.date(2026, 8, 30)) == "8월 30일의 전시"


def test_week_start_is_monday() -> None:
    assert timeutil.week_start(dt.date(2026, 8, 27)) == dt.date(2026, 8, 24)
    assert timeutil.week_start(dt.date(2026, 8, 24)) == dt.date(2026, 8, 24)


def test_date_range_includes_both_ends_and_rejects_inverted() -> None:
    assert timeutil.date_range(dt.date(2026, 8, 27), dt.date(2026, 8, 29)) == [
        dt.date(2026, 8, 27),
        dt.date(2026, 8, 28),
        dt.date(2026, 8, 29),
    ]
    assert timeutil.date_range(dt.date(2026, 8, 29), dt.date(2026, 8, 27)) == []


def test_parsers_return_none_instead_of_raising() -> None:
    assert timeutil.parse_date("2026-08-27") == dt.date(2026, 8, 27)
    assert timeutil.parse_date("2026-13-01") is None
    assert timeutil.parse_time_of_day("07:30") == dt.time(7, 30)
    assert timeutil.parse_time_of_day("7:30") is None
    assert timeutil.parse_time_of_day("24:00") is None


def test_rfc3339_uses_z_suffix() -> None:
    assert timeutil.format_rfc3339(dt.datetime(2026, 8, 27, 22, 30, tzinfo=dt.UTC)) == (
        "2026-08-27T22:30:00Z"
    )
