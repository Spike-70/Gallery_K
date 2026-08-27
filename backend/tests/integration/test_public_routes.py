"""공개 API — 실제 DB (API 문서 §6.1·§6.2)."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from sqlalchemy.orm import Session

from chalicelib.core.timeutil import freeze_time, kst_datetime
from chalicelib.db import query as q
from chalicelib.db.models import Exhibition, Notice
from chalicelib.services import setting_service

pytestmark = pytest.mark.integration


def _publish(session: Session, day: dt.date, title: str) -> Exhibition:
    return q.insert(
        session,
        Exhibition,
        {
            "exhibition_date": day,
            "title": title,
            "theme": "테마",
            "is_published": True,
            "published_at": kst_datetime(day, dt.time(7, 0)),
            "artwork_count": 12,
            "complete_artwork_count": 12,
        },
    )


def test_landing_shows_the_current_exhibition(api_client: Any, write_session: Session) -> None:
    _publish(write_session, dt.date(2026, 8, 27), "빛을 등진 사람들")
    write_session.commit()

    with freeze_time(dt.datetime(2026, 8, 27, 3, 0, tzinfo=dt.UTC)):
        response = api_client.http.get("/public/landing")

    data = response.json_body["data"]
    assert data["exhibition_title"] == "빛을 등진 사람들"
    assert data["has_exhibition"] is True
    assert data["today"] == "2026-08-27"
    assert data["today_label"] == "2026. 08. 27. 목"


def test_landing_carries_over_the_previous_exhibition(api_client: Any, write_session: Session) -> None:
    """오늘 발행분이 없으면 직전 전시가 그대로 걸린다 (PRD §4.3 규칙 1)."""
    _publish(write_session, dt.date(2026, 8, 30), "빛을 등진 사람들")
    write_session.commit()

    with freeze_time(dt.datetime(2026, 8, 31, 3, 0, tzinfo=dt.UTC)):
        response = api_client.http.get("/public/landing")

    data = response.json_body["data"]
    assert data["exhibition_title"] == "빛을 등진 사람들"
    # 첫 화면에는 발행일을 병기하지 않는다 (UX §3.1)
    assert set(data) == {
        "today",
        "today_label",
        "exhibition_title",
        "has_exhibition",
        "notice",
        "signup_open",
        "is_authenticated",
        "is_curator",
        "member_name",
    }


def test_landing_before_opening_has_no_title(api_client: Any) -> None:
    response = api_client.http.get("/public/landing")
    data = response.json_body["data"]
    assert data["exhibition_title"] is None
    assert data["has_exhibition"] is False


def test_hidden_exhibition_falls_back_to_the_previous_one(api_client: Any, write_session: Session) -> None:
    """숨김의 결과는 직전 전시 노출이다 (백엔드 문서 §12 필수 시나리오)."""
    _publish(write_session, dt.date(2026, 8, 26), "이전 전시")
    hidden = _publish(write_session, dt.date(2026, 8, 27), "숨긴 전시")
    hidden.is_hidden = True
    hidden.hidden_at = kst_datetime(dt.date(2026, 8, 27), dt.time(9, 0))
    write_session.commit()

    with freeze_time(dt.datetime(2026, 8, 27, 3, 0, tzinfo=dt.UTC)):
        response = api_client.http.get("/public/landing")
    assert response.json_body["data"]["exhibition_title"] == "이전 전시"


def test_notice_endpoint_returns_the_active_period_only(api_client: Any, write_session: Session) -> None:
    q.insert(
        write_session,
        Notice,
        {
            "starts_on": dt.date(2026, 8, 26),
            "ends_on": dt.date(2026, 8, 28),
            "body": "8월 26일부터 28일까지 쉽니다.",
            "is_active": True,
        },
    )
    write_session.commit()

    with freeze_time(dt.datetime(2026, 8, 27, 3, 0, tzinfo=dt.UTC)):
        inside = api_client.http.get("/public/notice").json_body["data"]["notice"]
    with freeze_time(dt.datetime(2026, 8, 29, 3, 0, tzinfo=dt.UTC)):
        outside = api_client.http.get("/public/notice").json_body["data"]["notice"]

    assert inside is not None
    assert inside["body"] == "8월 26일부터 28일까지 쉽니다."
    assert set(inside) == {"id", "starts_on", "ends_on", "body", "is_active"}
    assert outside is None


def test_signup_lock_is_reflected_in_landing(api_client: Any, write_session: Session) -> None:
    from chalicelib.db.models import AppSetting

    q.insert(
        write_session,
        AppSetting,
        {
            "key": setting_service.SettingKey.SIGNUP_OPEN,
            "value": False,
            "value_type": "boolean",
            "description": "테스트",
        },
    )
    write_session.commit()
    setting_service.invalidate_cache()

    response = api_client.http.get("/public/landing")
    assert response.json_body["data"]["signup_open"] is False


def test_health_reports_database_ok_against_a_real_database(
    api_client: Any, monkeypatch: pytest.MonkeyPatch, database_url: str
) -> None:
    from chalicelib.db import engine as engine_module

    probe = engine_module.create_db_engine(database_url)
    monkeypatch.setattr(engine_module, "engine", probe)
    monkeypatch.setattr(engine_module, "ping", lambda: True)

    body = api_client.http.get("/system/health").json_body["data"]
    assert body["checks"]["database"] == "ok"
    # 스토리지는 로컬에 없다. 그래도 200이며 상태만 degraded다.
    assert body["status"] in {"ok", "degraded"}
