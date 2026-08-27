"""회원 관리·설정·공지·통계 — 실제 DB (API 문서 §9.13–§9.19)."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from sqlalchemy.orm import Session

from chalicelib.core.errors import ErrorCode
from chalicelib.core.timeutil import freeze_time
from chalicelib.db import query as q
from chalicelib.db.models import AppUser, Notice, ViewLog
from chalicelib.schemas.member_admin import (
    MemberListOut,
    MemberOut,
    NoticeListOut,
    NoticeOut,
    SettingsOut,
    StatsDailyOut,
    StatsMemberDetailOut,
    StatsMembersOut,
)
from chalicelib.services import setting_service

from .factories import make_exhibition
from .helpers import auth_headers, curator_token, json_body, login, session_token, signup

pytestmark = pytest.mark.integration

AUG_27 = dt.datetime(2026, 8, 27, 3, 0, tzinfo=dt.UTC)
TODAY = dt.date(2026, 8, 27)


def _seed_members(api_client: Any) -> None:
    signup(api_client, phone="01011112222", name="김가나")
    signup(api_client, phone="01033334444", name="이다라")


def test_member_list_returns_full_phone_numbers(api_client: Any, write_session: Session) -> None:
    """B-3은 전화 한 통으로 돕는 화면이므로 관리자 응답에만 전체 번호가 나간다."""
    _seed_members(api_client)
    token = curator_token(api_client, write_session)

    response = api_client.http.get("/admin/members", headers=auth_headers(token, csrf=False))
    assert response.status_code == 200
    data = MemberListOut.model_validate(response.json_body["data"])
    assert {member.phone for member in data.members} == {"01011112222", "01033334444"}
    assert data.signup_open is True
    # 큐레이터 자신은 목록에 없다.
    assert all(member.role == "viewer" for member in data.members)

    meta = response.json_body["meta"]["pagination"]
    assert meta["mode"] == "page"
    assert meta["total_count"] == 2
    assert meta["page"] == 1


def test_member_list_derives_push_status_without_extra_queries(
    api_client: Any, write_session: Session
) -> None:
    """`push_status`·`push_platforms`·`last_viewed_on`은 한 질의로 결합된다(교차검토 X-25)."""
    token_a = session_token(signup(api_client, phone="01011112222", name="김가나"))
    api_client.http.post(
        "/me/push-subscriptions",
        headers=auth_headers(token_a),
        body=json_body(
            {
                "endpoint": "https://example.com/push/a",
                "keys": {"p256dh": "k", "auth": "a"},
                "platform": "ios",
            }
        ),
    )
    signup(api_client, phone="01033334444", name="이다라")
    token = curator_token(api_client, write_session)

    data = MemberListOut.model_validate(
        api_client.http.get("/admin/members", headers=auth_headers(token, csrf=False)).json_body["data"]
    )
    by_phone = {member.phone: member for member in data.members}
    assert by_phone["01011112222"].push_status == "active"
    assert by_phone["01011112222"].push_platforms == ["ios"]
    assert by_phone["01033334444"].push_status == "none"
    assert by_phone["01033334444"].push_platforms == []


def test_member_list_filters_and_search(api_client: Any, write_session: Session) -> None:
    _seed_members(api_client)
    token = curator_token(api_client, write_session)
    headers = auth_headers(token, csrf=False)

    by_name = MemberListOut.model_validate(
        api_client.http.get("/admin/members?query=가나", headers=headers).json_body["data"]
    )
    assert [member.name for member in by_name.members] == ["김가나"]

    by_phone = MemberListOut.model_validate(
        api_client.http.get("/admin/members?query=010-3333-4444", headers=headers).json_body["data"]
    )
    assert [member.name for member in by_phone.members] == ["이다라"]

    none_found = MemberListOut.model_validate(
        api_client.http.get("/admin/members?query=없는이름", headers=headers).json_body["data"]
    )
    assert none_found.members == []


def test_member_list_sorting_is_restricted_to_the_allow_list(api_client: Any, write_session: Session) -> None:
    _seed_members(api_client)
    token = curator_token(api_client, write_session)
    headers = auth_headers(token, csrf=False)

    ascending = MemberListOut.model_validate(
        api_client.http.get("/admin/members?sort=name", headers=headers).json_body["data"]
    )
    assert [member.name for member in ascending.members] == ["김가나", "이다라"]

    # 허용 목록 밖의 정렬은 전용 코드로 거절하고, 무엇이 허용되는지 함께 알려 준다.
    rejected = api_client.http.get("/admin/members?sort=phone", headers=headers)
    assert rejected.status_code == 400
    assert rejected.json_body["error"]["code"] == ErrorCode.QUERY_INVALID_SORT
    assert rejected.json_body["error"]["details"]["allowed"] == [
        "created_at",
        "-created_at",
        "name",
        "-name",
        "last_viewed_on",
        "-last_viewed_on",
    ]


def test_member_list_sorts_by_derived_last_viewed_on(api_client: Any, write_session: Session) -> None:
    """파생 필드 정렬 시 계산이 페이징보다 앞선다 (DB 문서 §7)."""
    _seed_members(api_client)
    make_exhibition(write_session, TODAY)
    write_session.commit()
    older = q.fetch_one(write_session, AppUser, where={"phone": "01011112222"})
    assert older is not None
    exhibition = make_exhibition(write_session, dt.date(2026, 8, 20), title="지난")
    now = dt.datetime(2026, 8, 20, 0, 0, tzinfo=dt.UTC)
    q.insert(
        write_session,
        ViewLog,
        {
            "user_id": older.id,
            "viewed_on": dt.date(2026, 8, 20),
            "exhibition_id": exhibition.id,
            "first_entered_at": now,
            "last_entered_at": now,
        },
    )
    write_session.commit()
    token = curator_token(api_client, write_session)

    data = MemberListOut.model_validate(
        api_client.http.get(
            "/admin/members?sort=-last_viewed_on", headers=auth_headers(token, csrf=False)
        ).json_body["data"]
    )
    assert data.members[0].last_viewed_on == "2026-08-20"
    assert data.members[-1].last_viewed_on is None  # NULLS LAST


def test_curator_can_create_members_even_while_signup_is_locked(
    api_client: Any, write_session: Session
) -> None:
    """잠금은 외부 가입을 막는 장치이지 큐레이터를 막는 장치가 아니다 (API 문서 §9.14)."""
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
    token = curator_token(api_client, write_session)

    response = api_client.http.post(
        "/admin/members",
        headers=auth_headers(token),
        body=json_body({"phone": "01055556666", "name": "대행가입", "initial_password": "initialpass123"}),
    )
    assert response.status_code == 201
    member = MemberOut.model_validate(response.json_body["data"]).member
    assert member.created_via == "curator"

    created = q.fetch_one(write_session, AppUser, where={"phone": "01055556666"})
    assert created is not None
    assert created.must_change_password is True


def test_blocking_is_idempotent_and_does_not_cut_existing_sessions(
    api_client: Any, write_session: Session
) -> None:
    """차단은 로그인 시점에만 작동한다 (PRD §6.4)."""
    member_token = session_token(signup(api_client, phone="01011112222", name="김가나"))
    token = curator_token(api_client, write_session)
    member_id = (
        MemberListOut.model_validate(
            api_client.http.get("/admin/members", headers=auth_headers(token, csrf=False)).json_body["data"]
        )
        .members[0]
        .id
    )

    first = api_client.http.post(
        f"/admin/members/{member_id}/block", headers=auth_headers(token), body=json_body({"reason": "요청"})
    )
    assert first.status_code == 200
    assert MemberOut.model_validate(first.json_body["data"]).member.is_blocked is True

    again = api_client.http.post(
        f"/admin/members/{member_id}/block", headers=auth_headers(token), body=json_body({})
    )
    assert again.status_code == 200

    # 이미 열린 세션은 그대로 살아 있다.
    assert api_client.http.get("/me", headers=auth_headers(member_token, csrf=False)).status_code == 200
    # 그러나 새 로그인은 막힌다.
    assert login(api_client, phone="01011112222", password="password123").status_code == 401

    unblocked = api_client.http.post(
        f"/admin/members/{member_id}/unblock", headers=auth_headers(token), body=b""
    )
    assert MemberOut.model_validate(unblocked.json_body["data"]).member.is_blocked is False


def test_password_reset_revokes_every_session(api_client: Any, write_session: Session) -> None:
    member_token = session_token(signup(api_client, phone="01011112222", name="김가나"))
    token = curator_token(api_client, write_session)
    member_id = (
        MemberListOut.model_validate(
            api_client.http.get("/admin/members", headers=auth_headers(token, csrf=False)).json_body["data"]
        )
        .members[0]
        .id
    )

    response = api_client.http.post(
        f"/admin/members/{member_id}/reset-password",
        headers=auth_headers(token),
        body=json_body({"new_password": "brandnewpass123"}),
    )
    assert response.status_code == 200

    stale = api_client.http.get("/me", headers=auth_headers(member_token, csrf=False))
    assert stale.status_code == 401
    assert stale.json_body["error"]["code"] == ErrorCode.AUTH_SESSION_REVOKED

    fresh = login(api_client, phone="01011112222", password="brandnewpass123")
    assert fresh.status_code == 200
    assert fresh.json_body["data"]["user"]["must_change_password"] is True


def test_curator_account_cannot_be_blocked(api_client: Any, write_session: Session) -> None:
    token = curator_token(api_client, write_session)
    curator = q.fetch_one(write_session, AppUser, where={"role": "curator"})
    assert curator is not None

    response = api_client.http.post(
        f"/admin/members/{curator.id}/block", headers=auth_headers(token), body=json_body({})
    )
    assert response.status_code == 403
    assert response.json_body["error"]["code"] == ErrorCode.MEMBER_CURATOR_IMMUTABLE


def test_settings_round_trip(api_client: Any, write_session: Session) -> None:
    from chalicelib.db.models import AppSetting

    q.insert(
        write_session,
        AppSetting,
        {
            "key": setting_service.SettingKey.SIGNUP_OPEN,
            "value": True,
            "value_type": "boolean",
            "description": "신규 가입 허용",
        },
    )
    write_session.commit()
    setting_service.invalidate_cache()
    token = curator_token(api_client, write_session)

    listed = SettingsOut.model_validate(
        api_client.http.get("/admin/settings", headers=auth_headers(token, csrf=False)).json_body["data"]
    )
    assert listed.settings[0].key == "signup_open"

    patched = api_client.http.patch(
        "/admin/settings",
        headers=auth_headers(token),
        body=json_body({"settings": {"signup_open": False}}),
    )
    assert patched.status_code == 200
    assert SettingsOut.model_validate(patched.json_body["data"]).settings[0].value is False

    # 가입 잠금이 즉시 반영된다(같은 인스턴스는 캐시를 비운다).
    assert signup(api_client, phone="01088889999").status_code == 403


def test_unknown_and_mistyped_settings_are_refused(api_client: Any, write_session: Session) -> None:
    from chalicelib.db.models import AppSetting

    q.insert(
        write_session,
        AppSetting,
        {
            "key": setting_service.SettingKey.ARCHIVE_SIZE,
            "value": 30,
            "value_type": "number",
            "description": "아카이브 크기",
        },
    )
    write_session.commit()
    token = curator_token(api_client, write_session)

    unknown = api_client.http.patch(
        "/admin/settings",
        headers=auth_headers(token),
        body=json_body({"settings": {"nope": 1}}),
    )
    assert unknown.status_code == 400
    assert unknown.json_body["error"]["code"] == ErrorCode.SETTING_UNKNOWN_KEY

    mistyped = api_client.http.patch(
        "/admin/settings",
        headers=auth_headers(token),
        body=json_body({"settings": {"archive_size": "삼십"}}),
    )
    assert mistyped.status_code == 422


def test_notice_lifecycle(api_client: Any, write_session: Session) -> None:
    token = curator_token(api_client, write_session)

    created = api_client.http.post(
        "/admin/notices",
        headers=auth_headers(token),
        body=json_body({"starts_on": "2026-09-01", "ends_on": "2026-09-05", "body": "9월 초에 쉽니다."}),
    )
    assert created.status_code == 201
    notice = NoticeOut.model_validate(created.json_body["data"]).notice

    patched = api_client.http.patch(
        f"/admin/notices/{notice.id}",
        headers=auth_headers(token),
        body=json_body({"body": "일정이 바뀌었습니다."}),
    )
    assert NoticeOut.model_validate(patched.json_body["data"]).notice.body == "일정이 바뀌었습니다."

    with freeze_time(AUG_27):
        listed = NoticeListOut.model_validate(
            api_client.http.get("/admin/notices", headers=auth_headers(token, csrf=False)).json_body["data"]
        )
    assert len(listed.notices) == 1

    cancelled = api_client.http.delete(f"/admin/notices/{notice.id}", headers=auth_headers(token))
    assert cancelled.status_code == 200
    # 취소는 삭제가 아니라 비활성이다.
    rows = q.fetch(write_session, Notice)
    assert len(rows) == 1
    assert rows[0].is_active is False


def test_overlapping_notice_periods_are_refused(api_client: Any, write_session: Session) -> None:
    """겹침을 허용하면 "오늘의 공지"가 비결정적이 된다 (DB 문서 §4.8)."""
    token = curator_token(api_client, write_session)
    api_client.http.post(
        "/admin/notices",
        headers=auth_headers(token),
        body=json_body({"starts_on": "2026-09-01", "ends_on": "2026-09-05", "body": "휴관"}),
    )
    overlapping = api_client.http.post(
        "/admin/notices",
        headers=auth_headers(token),
        body=json_body({"starts_on": "2026-09-04", "ends_on": "2026-09-08", "body": "또 휴관"}),
    )
    assert overlapping.status_code == 409
    assert overlapping.json_body["error"]["code"] == ErrorCode.NOTICE_PERIOD_OVERLAP
    assert overlapping.json_body["error"]["details"]["conflict_notice_id"]


def test_inverted_notice_period_is_refused(api_client: Any, write_session: Session) -> None:
    token = curator_token(api_client, write_session)
    response = api_client.http.post(
        "/admin/notices",
        headers=auth_headers(token),
        body=json_body({"starts_on": "2026-09-05", "ends_on": "2026-09-01", "body": "휴관"}),
    )
    assert response.status_code == 422
    assert response.json_body["error"]["code"] == ErrorCode.NOTICE_PERIOD_INVALID


def test_stats_daily_includes_every_day_in_range(api_client: Any, write_session: Session) -> None:
    """미입장일도 행으로 포함한다 (API 문서 §9.19)."""
    make_exhibition(write_session, dt.date(2026, 8, 25), title="25일 전시")
    write_session.commit()
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        response = api_client.http.get(
            "/admin/stats/daily?from=2026-08-24&to=2026-08-27",
            headers=auth_headers(token, csrf=False),
        )
    data = StatsDailyOut.model_validate(response.json_body["data"])
    assert [day.date for day in data.days] == [
        "2026-08-24",
        "2026-08-25",
        "2026-08-26",
        "2026-08-27",
    ]
    by_date = {day.date: day for day in data.days}
    assert by_date["2026-08-25"].is_carried_over is False
    assert by_date["2026-08-26"].is_carried_over is True
    assert by_date["2026-08-26"].exhibition_date == "2026-08-25"
    assert all(day.entrant_count == 0 for day in data.days)


def test_stats_member_search_masks_the_phone_number(api_client: Any, write_session: Session) -> None:
    signup(api_client, phone="01011112222", name="김가나")
    token = curator_token(api_client, write_session)

    response = api_client.http.get("/admin/stats/members?query=가나", headers=auth_headers(token, csrf=False))
    data = StatsMembersOut.model_validate(response.json_body["data"])
    assert len(data.members) == 1
    assert data.members[0].phone_masked == "010-****-2222"
    assert "01011112222" not in str(response.json_body)


def test_stats_member_detail_shows_progress_per_day(api_client: Any, write_session: Session) -> None:
    member_token = session_token(signup(api_client, phone="01011112222", name="김가나"))
    make_exhibition(write_session, TODAY)
    write_session.commit()
    from chalicelib.db.models import Artwork

    artwork = q.fetch_one(write_session, Artwork, where={"position": 1})
    assert artwork is not None
    with freeze_time(AUG_27):
        api_client.http.post("/exhibitions/2026-08-27/view", headers=auth_headers(member_token), body=b"")
        api_client.http.post(f"/artworks/{artwork.id}/view", headers=auth_headers(member_token), body=b"")

    token = curator_token(api_client, write_session)
    member_id = (
        MemberListOut.model_validate(
            api_client.http.get("/admin/members", headers=auth_headers(token, csrf=False)).json_body["data"]
        )
        .members[0]
        .id
    )

    with freeze_time(AUG_27):
        response = api_client.http.get(
            f"/admin/stats/members/{member_id}?days=3", headers=auth_headers(token, csrf=False)
        )
    data = StatsMemberDetailOut.model_validate(response.json_body["data"])
    assert data.member["phone_masked"] == "010-****-2222"
    assert len(data.days) == 3
    today_row = data.days[-1]
    assert today_row.date == "2026-08-27"
    assert today_row.entered is True
    assert today_row.viewed_artwork_count == 1
    assert today_row.total_artwork_count == 12
    assert data.days[0].entered is False


def test_operational_settings_actually_take_effect(api_client: Any, write_session: Session) -> None:
    """시드만 되고 아무도 읽지 않는 설정은 설정이 아니다 (DB 문서 §4.9).

    달력 기본 일수와 세션 수명이 실제로 값을 따르는지 확인한다.
    """
    from chalicelib.db.models import AppSetting

    for key, value in (
        (setting_service.SettingKey.ADMIN_CALENDAR_DAYS, 3),
        (setting_service.SettingKey.SESSION_TTL_DAYS, 7),
    ):
        q.insert(
            write_session,
            AppSetting,
            {"key": key, "value": value, "value_type": "number", "description": "테스트"},
        )
    write_session.commit()
    setting_service.invalidate_cache()

    token = curator_token(api_client, write_session)
    with freeze_time(AUG_27):
        calendar = api_client.http.get("/admin/exhibitions/calendar", headers=auth_headers(token, csrf=False))
    assert len(calendar.json_body["data"]["days"]) == 3

    from .helpers import login, set_cookie_values

    response = login(api_client, phone="01000000000", password="curatorpass123")
    cookie = next(c for c in set_cookie_values(response) if c.startswith("gk_session="))
    assert "Max-Age=604800" in cookie  # 7일
