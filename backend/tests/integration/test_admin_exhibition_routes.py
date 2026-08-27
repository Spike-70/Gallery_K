"""관리자 전시 편집 — 실제 DB (API 문서 §9, PRD §4.3·§6.9·§6.10).

문서가 "반드시 있어야 하는 것"으로 지정한 시나리오 대부분이 여기에 있다(백엔드 문서 §12):
발행 후 조건이 깨져도 발행 상태 유지 · 백필 거부와 과거 발행본 수정 허용 · 이어쓰기 원자성.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from sqlalchemy.orm import Session

from chalicelib.core.errors import ErrorCode
from chalicelib.core.timeutil import freeze_time
from chalicelib.db import query as q
from chalicelib.db.models import Artwork, AuditLog, Exhibition, NotificationLog
from chalicelib.schemas.admin import (
    AdminExhibitionDetailOut,
    AdminSummaryOut,
    CalendarOut,
    CarryDraftOut,
    ExhibitionSaveOut,
    HideOut,
)
from chalicelib.schemas.exhibition import ExhibitionDetailOut

from .factories import make_exhibition
from .helpers import auth_headers, curator_token, json_body, session_token, signup

pytestmark = pytest.mark.integration

AUG_27 = dt.datetime(2026, 8, 27, 3, 0, tzinfo=dt.UTC)  # KST 12:00
TODAY = dt.date(2026, 8, 27)


def _fill_slot(client: Any, token: str, date: str, position: int) -> Any:
    return client.http.put(
        f"/admin/exhibitions/{date}/artworks/{position}",
        headers=auth_headers(token),
        body=json_body(
            {
                "title": f"그림 {position}",
                "artist": "요하네스 페르메이르",
                "year_text": "1665년경",
                "description": "설명입니다.",
                "collection": None,
                "source_url": None,
            }
        ),
    )


def _mark_image_ready(session: Session, exhibition_date: dt.date) -> None:
    """이미지 처리는 범위 8의 일이다. 여기서는 준비 완료 상태만 만들어 준다."""
    exhibition = q.fetch_one(session, Exhibition, where={"exhibition_date": exhibition_date})
    assert exhibition is not None
    for artwork in q.fetch(session, Artwork, where={"exhibition_id": exhibition.id}):
        q.update(
            session,
            Artwork,
            where={"id": artwork.id},
            values={
                "image_status": "ready",
                "image_origin_key": "k/origin.jpg",
                "image_display_key": "k/display.webp",
                "image_thumb_key": "k/thumb.webp",
                "image_width": 1600,
                "image_height": 1200,
            },
            bump_version=False,
        )
    session.commit()


def test_member_is_told_no_not_hidden_from(api_client: Any, write_session: Session) -> None:
    """회원의 관리자 API 접근은 숨기지 않고 권한 없음으로 답한다 (API 문서 §2.7)."""
    token = session_token(signup(api_client))
    response = api_client.http.get("/admin/summary", headers=auth_headers(token, csrf=False))
    assert response.status_code == 403
    assert response.json_body["error"]["code"] == ErrorCode.AUTH_FORBIDDEN


def test_admin_responses_are_never_cached(api_client: Any, write_session: Session) -> None:
    token = curator_token(api_client, write_session)
    response = api_client.http.get("/admin/summary", headers=auth_headers(token, csrf=False))
    assert response.headers["Cache-Control"] == "no-store"


def test_detail_of_an_empty_date_returns_twelve_placeholders(api_client: Any, write_session: Session) -> None:
    """행이 없어도 부재 오류가 아니다 (API 문서 §9.3)."""
    token = curator_token(api_client, write_session)
    with freeze_time(AUG_27):
        response = api_client.http.get(
            "/admin/exhibitions/2026-08-27", headers=auth_headers(token, csrf=False)
        )
    assert response.status_code == 200
    data = AdminExhibitionDetailOut.model_validate(response.json_body["data"])
    assert len(data.slots) == 12
    assert all(slot.artwork_id is None for slot in data.slots)
    assert data.edit_mode == "create"
    assert data.can_publish is False
    assert "missing_title" in data.publish_blockers


def test_saving_title_and_theme_creates_the_draft(api_client: Any, write_session: Session) -> None:
    token = curator_token(api_client, write_session)
    with freeze_time(AUG_27):
        response = api_client.http.put(
            "/admin/exhibitions/2026-08-27",
            headers=auth_headers(token),
            body=json_body({"title": "빛을 등진 사람들", "theme": "테마 본문"}),
        )
    data = ExhibitionSaveOut.model_validate(response.json_body["data"])
    assert data.is_published is False
    assert data.published_now is False
    assert data.can_publish is False
    assert any(item.startswith("incomplete_artwork:") for item in data.publish_blockers)


def test_publication_happens_when_the_last_condition_is_met(api_client: Any, write_session: Session) -> None:
    """12점 + 제목 + 테마가 채워지는 순간 자동으로 발행된다 (PRD §6.10)."""
    token = curator_token(api_client, write_session)
    with freeze_time(AUG_27):
        api_client.http.put(
            "/admin/exhibitions/2026-08-27",
            headers=auth_headers(token),
            body=json_body({"title": "빛을 등진 사람들", "theme": "테마"}),
        )
        for position in range(1, 13):
            _fill_slot(api_client, token, "2026-08-27", position)

    _mark_image_ready(write_session, TODAY)

    with freeze_time(AUG_27):
        final = api_client.http.put(
            "/admin/exhibitions/2026-08-27",
            headers=auth_headers(token),
            body=json_body({"title": "빛을 등진 사람들", "theme": "테마"}),
        )
    data = ExhibitionSaveOut.model_validate(final.json_body["data"])
    assert data.is_published is True
    assert data.published_now is True
    assert data.publish_blockers == []


def test_publication_queues_morning_notifications(api_client: Any, write_session: Session) -> None:
    """발행 트랜잭션 안에서 대상 회원 전원의 알림이 예약된다 (API 문서 §11.3)."""
    signup(api_client, phone="01011112222", name="관람자A")
    signup(api_client, phone="01033334444", name="관람자B")
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        api_client.http.put(
            "/admin/exhibitions/2026-08-27",
            headers=auth_headers(token),
            body=json_body({"title": "전시", "theme": "테마"}),
        )
        for position in range(1, 13):
            _fill_slot(api_client, token, "2026-08-27", position)
    _mark_image_ready(write_session, TODAY)
    with freeze_time(AUG_27):
        api_client.http.put(
            "/admin/exhibitions/2026-08-27",
            headers=auth_headers(token),
            body=json_body({"title": "전시", "theme": "테마"}),
        )

    morning = q.fetch(
        write_session,
        NotificationLog,
        where={"kind__in": ["morning_exhibition", "late_publish"]},
    )
    # 관람자 2명 + 큐레이터 1명
    assert len(morning) == 3
    assert {row.dedupe_key.split(":")[0] for row in morning} == {"morning"}
    assert all(row.payload["title"] == "전시" for row in morning)


def test_published_exhibition_stays_published_when_a_slot_is_cleared(
    api_client: Any, write_session: Session
) -> None:
    """한 번 Y가 된 전시는 12점이 깨져도 N으로 되돌아가지 않는다 (PRD §6.10)."""
    make_exhibition(write_session, TODAY)
    write_session.commit()
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        response = api_client.http.delete(
            "/admin/exhibitions/2026-08-27/artworks/1", headers=auth_headers(token)
        )
    assert response.status_code == 200
    assert response.json_body["data"]["exhibition"]["is_published"] is True
    assert response.json_body["data"]["exhibition"]["can_publish"] is False
    assert response.json_body["data"]["slot"]["artwork_id"] is None

    exhibition = q.fetch_one(write_session, Exhibition, where={"exhibition_date": TODAY})
    assert exhibition is not None
    write_session.refresh(exhibition)
    assert exhibition.is_published is True
    assert exhibition.artwork_count == 11


def test_backfill_is_refused(api_client: Any, write_session: Session) -> None:
    """지난 날짜에는 새 전시를 걸 수 없다 (PRD §4.3)."""
    token = curator_token(api_client, write_session)
    with freeze_time(AUG_27):
        response = api_client.http.put(
            "/admin/exhibitions/2026-08-20",
            headers=auth_headers(token),
            body=json_body({"title": "지난 날짜 전시", "theme": "테마"}),
        )
    assert response.status_code == 409
    assert response.json_body["error"]["code"] == ErrorCode.EXHIBITION_BACKFILL_FORBIDDEN
    assert response.json_body["error"]["details"] == {"date": "2026-08-20", "today": "2026-08-27"}


def test_editing_an_already_published_past_exhibition_is_allowed(
    api_client: Any, write_session: Session
) -> None:
    """막는 것은 '과거 날짜에 새 전시가 생기는 것'이지 수정이 아니다."""
    make_exhibition(write_session, dt.date(2026, 8, 20), title="예전 제목")
    write_session.commit()
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        response = api_client.http.put(
            "/admin/exhibitions/2026-08-20",
            headers=auth_headers(token),
            body=json_body({"title": "고친 제목", "theme": "고친 테마"}),
        )
    assert response.status_code == 200
    assert response.json_body["data"]["is_published"] is True

    exhibition = q.fetch_one(write_session, Exhibition, where={"exhibition_date": dt.date(2026, 8, 20)})
    assert exhibition is not None
    write_session.refresh(exhibition)
    assert exhibition.title == "고친 제목"


def test_calendar_shows_three_states(api_client: Any, write_session: Session) -> None:
    """`Y` / `↑` / `N` (PRD §6.9). 과거 미발행일은 실패가 아니라 연장이다."""
    make_exhibition(write_session, dt.date(2026, 8, 25), title="25일 전시")
    write_session.commit()
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        response = api_client.http.get(
            "/admin/exhibitions/calendar?from=2026-08-24&to=2026-08-28",
            headers=auth_headers(token, csrf=False),
        )
    days = {day.date: day for day in CalendarOut.model_validate(response.json_body["data"]).days}
    assert set(days) == {"2026-08-24", "2026-08-25", "2026-08-26", "2026-08-27", "2026-08-28"}

    assert days["2026-08-25"].status == "published"
    assert days["2026-08-26"].status == "carried_over"
    assert days["2026-08-26"].carried_from_date == "2026-08-25"
    assert days["2026-08-26"].carried_from_title == "25일 전시"
    # 오늘과 미래는 `N` — 아직 준비되지 않았다는 뜻이고, 그것이 오늘 할 일이다.
    assert days["2026-08-27"].status == "empty"
    assert days["2026-08-28"].status == "empty"
    # 개관 전 과거에는 걸릴 전시 자체가 없었다.
    assert days["2026-08-24"].status == "empty"


def test_calendar_decides_edit_mode_on_the_server(api_client: Any, write_session: Session) -> None:
    make_exhibition(write_session, dt.date(2026, 8, 25), title="발행본")
    make_exhibition(
        write_session, dt.date(2026, 8, 26), title="쓰다 만 원고", published=False, artwork_count=3
    )
    write_session.commit()
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        response = api_client.http.get(
            "/admin/exhibitions/calendar?from=2026-08-24&to=2026-08-28",
            headers=auth_headers(token, csrf=False),
        )
    days = {day.date: day for day in CalendarOut.model_validate(response.json_body["data"]).days}
    assert days["2026-08-24"].edit_mode == "locked"  # 과거의 빈 날 — 백필 금지
    assert days["2026-08-25"].edit_mode == "edit"  # 발행본은 수정 가능
    assert days["2026-08-26"].edit_mode == "carry_draft"  # 쓰다 만 원고가 있다
    assert days["2026-08-27"].edit_mode == "create"
    assert days["2026-08-28"].edit_mode == "create"
    assert days["2026-08-24"].is_editable is False
    assert days["2026-08-26"].draft_progress.artwork_count == 3


def test_calendar_defaults_to_seven_days_from_today(api_client: Any, write_session: Session) -> None:
    token = curator_token(api_client, write_session)
    with freeze_time(AUG_27):
        response = api_client.http.get("/admin/exhibitions/calendar", headers=auth_headers(token, csrf=False))
    days = CalendarOut.model_validate(response.json_body["data"]).days
    assert len(days) == 7
    assert days[0].date == "2026-08-27"
    assert days[0].is_today is True
    assert days[-1].date == "2026-09-02"


def test_calendar_scrolls_into_the_past(api_client: Any, write_session: Session) -> None:
    token = curator_token(api_client, write_session)
    with freeze_time(AUG_27):
        response = api_client.http.get(
            "/admin/exhibitions/calendar?direction=past&limit=3",
            headers=auth_headers(token, csrf=False),
        )
    days = CalendarOut.model_validate(response.json_body["data"]).days
    assert [day.date for day in days] == ["2026-08-24", "2026-08-25", "2026-08-26"]
    assert response.json_body["meta"]["pagination"]["has_more"] is True


def test_calendar_rejects_unknown_parameters(api_client: Any, write_session: Session) -> None:
    """오타로 필터가 조용히 풀리는 사고를 막는다 (API 문서 §2.6)."""
    token = curator_token(api_client, write_session)
    response = api_client.http.get(
        "/admin/exhibitions/calendar?fromm=2026-08-01", headers=auth_headers(token, csrf=False)
    )
    assert response.status_code == 400
    assert response.json_body["error"]["code"] == ErrorCode.QUERY_UNKNOWN_PARAM
    assert response.json_body["error"]["details"]["unknown"] == ["fromm"]


def test_hide_reports_which_exhibition_now_hangs(api_client: Any, write_session: Session) -> None:
    """큐레이터가 조작 결과를 즉시 확인할 수 있어야 한다 (PRD §6.9)."""
    make_exhibition(write_session, dt.date(2026, 8, 25), title="이전 전시")
    make_exhibition(write_session, TODAY, title="오늘 전시")
    write_session.commit()
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        response = api_client.http.post(
            "/admin/exhibitions/2026-08-27/hide",
            headers=auth_headers(token),
            body=json_body({"reason": "저작권 확인 중"}),
        )
    data = HideOut.model_validate(response.json_body["data"])
    assert data.is_hidden is True
    assert data.current_exhibition_date == "2026-08-25"

    with freeze_time(AUG_27):
        again = api_client.http.post(
            "/admin/exhibitions/2026-08-27/hide", headers=auth_headers(token), body=json_body({})
        )
    assert again.status_code == 409
    assert again.json_body["error"]["code"] == ErrorCode.EXHIBITION_ALREADY_HIDDEN


def test_unhide_restores_the_exhibition(api_client: Any, write_session: Session) -> None:
    make_exhibition(write_session, TODAY, title="오늘 전시", hidden=True)
    write_session.commit()
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        response = api_client.http.post(
            "/admin/exhibitions/2026-08-27/unhide", headers=auth_headers(token), body=b""
        )
    data = HideOut.model_validate(response.json_body["data"])
    assert data.is_hidden is False
    assert data.current_exhibition_date == "2026-08-27"


def test_hiding_an_unpublished_exhibition_is_refused(api_client: Any, write_session: Session) -> None:
    make_exhibition(write_session, TODAY, published=False)
    write_session.commit()
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        response = api_client.http.post(
            "/admin/exhibitions/2026-08-27/hide", headers=auth_headers(token), body=json_body({})
        )
    assert response.status_code == 409
    assert response.json_body["error"]["code"] == ErrorCode.EXHIBITION_NOT_PUBLISHED


def test_carry_draft_moves_the_work_and_leaves_nothing_behind(
    api_client: Any, write_session: Session
) -> None:
    """이동이지 복사가 아니다. 원본 날짜의 행은 남지 않는다 (PRD 부록 B)."""
    make_exhibition(
        write_session, dt.date(2026, 8, 26), title="쓰다 만 원고", published=False, artwork_count=11
    )
    write_session.commit()
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        response = api_client.http.post(
            "/admin/exhibitions/2026-08-26/carry-draft",
            headers=auth_headers(token),
            body=json_body({"confirm": True}),
        )
    data = CarryDraftOut.model_validate(response.json_body["data"])
    assert data.from_date == "2026-08-26"
    assert data.to_date == "2026-08-27"
    assert data.moved_artwork_count == 11
    assert data.exhibition.title == "쓰다 만 원고"
    assert len([slot for slot in data.exhibition.slots if slot.artwork_id]) == 11

    assert q.count(write_session, Exhibition, where={"exhibition_date": dt.date(2026, 8, 26)}) == 0
    moved = q.fetch_one(write_session, Exhibition, where={"exhibition_date": TODAY})
    assert moved is not None
    assert q.count(write_session, Artwork, where={"exhibition_id": moved.id}) == 11


def test_carry_draft_is_refused_when_today_is_occupied(api_client: Any, write_session: Session) -> None:
    make_exhibition(write_session, dt.date(2026, 8, 26), title="원고", published=False, artwork_count=2)
    make_exhibition(write_session, TODAY, title="오늘 작업물", published=False, artwork_count=1)
    write_session.commit()
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        response = api_client.http.post(
            "/admin/exhibitions/2026-08-26/carry-draft",
            headers=auth_headers(token),
            body=json_body({"confirm": True}),
        )
    assert response.status_code == 409
    assert response.json_body["error"]["code"] == ErrorCode.DRAFT_TARGET_OCCUPIED
    assert response.json_body["error"]["details"]["target_date"] == "2026-08-27"
    # 실패한 이동은 원본을 건드리지 않는다.
    assert q.count(write_session, Exhibition, where={"exhibition_date": dt.date(2026, 8, 26)}) == 1


def test_carry_draft_needs_something_to_carry(api_client: Any, write_session: Session) -> None:
    token = curator_token(api_client, write_session)
    with freeze_time(AUG_27):
        response = api_client.http.post(
            "/admin/exhibitions/2026-08-26/carry-draft",
            headers=auth_headers(token),
            body=json_body({"confirm": True}),
        )
    assert response.status_code == 404
    assert response.json_body["error"]["code"] == ErrorCode.DRAFT_NOT_FOUND


def test_reorder_is_a_final_state_declaration(api_client: Any, write_session: Session) -> None:
    """슬롯 유니크가 DEFERRABLE이므로 임시 오프셋 없이 한 번에 재할당한다."""
    exhibition = make_exhibition(write_session, TODAY, artwork_count=3)
    write_session.commit()
    artworks = q.fetch(write_session, Artwork, where={"exhibition_id": exhibition.id}, order_by=["position"])
    token = curator_token(api_client, write_session)

    order = [
        {"artwork_id": str(artworks[2].id), "position": 1},
        {"artwork_id": str(artworks[0].id), "position": 2},
        {"artwork_id": str(artworks[1].id), "position": 3},
    ]
    with freeze_time(AUG_27):
        response = api_client.http.post(
            "/admin/exhibitions/2026-08-27/artworks/reorder",
            headers=auth_headers(token),
            body=json_body({"order": order}),
        )
    assert response.status_code == 200
    slots = response.json_body["data"]["slots"]
    assert slots[0]["artwork_id"] == str(artworks[2].id)
    assert slots[1]["artwork_id"] == str(artworks[0].id)
    assert len(slots) == 12


def test_reorder_refuses_duplicate_positions(api_client: Any, write_session: Session) -> None:
    exhibition = make_exhibition(write_session, TODAY, artwork_count=2)
    write_session.commit()
    artworks = q.fetch(write_session, Artwork, where={"exhibition_id": exhibition.id})
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        response = api_client.http.post(
            "/admin/exhibitions/2026-08-27/artworks/reorder",
            headers=auth_headers(token),
            body=json_body(
                {
                    "order": [
                        {"artwork_id": str(artworks[0].id), "position": 1},
                        {"artwork_id": str(artworks[1].id), "position": 1},
                    ]
                }
            ),
        )
    assert response.status_code == 422


def test_optimistic_locking_refuses_a_stale_version(api_client: Any, write_session: Session) -> None:
    token = curator_token(api_client, write_session)
    with freeze_time(AUG_27):
        first = api_client.http.put(
            "/admin/exhibitions/2026-08-27",
            headers=auth_headers(token),
            body=json_body({"title": "처음", "theme": "테마"}),
        )
        version = first.json_body["data"]["version"]
        api_client.http.put(
            "/admin/exhibitions/2026-08-27",
            headers=auth_headers(token),
            body=json_body({"title": "두번째", "theme": "테마", "version": version}),
        )
        stale = api_client.http.put(
            "/admin/exhibitions/2026-08-27",
            headers=auth_headers(token),
            body=json_body({"title": "세번째", "theme": "테마", "version": version}),
        )
    assert stale.status_code == 409
    assert stale.json_body["error"]["code"] == ErrorCode.CONFLICT_VERSION


def test_preview_matches_the_viewer_schema(api_client: Any, write_session: Session) -> None:
    """관람자 컴포넌트를 그대로 재사용하기 위해 스키마를 일치시킨다 (API 문서 §9.12)."""
    make_exhibition(write_session, TODAY, published=False)
    write_session.commit()
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        response = api_client.http.get(
            "/admin/exhibitions/2026-08-27/preview", headers=auth_headers(token, csrf=False)
        )
    data = ExhibitionDetailOut.model_validate(response.json_body["data"])
    assert data.is_carried_over is False
    assert data.viewing_date == "2026-08-27"
    assert len(data.artworks) == 12


def test_summary_reports_the_two_numbers_the_prd_asked_for(api_client: Any, write_session: Session) -> None:
    make_exhibition(write_session, dt.date(2026, 8, 25), title="25일 전시")
    write_session.commit()
    signup(api_client, phone="01011112222")
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        response = api_client.http.get("/admin/summary", headers=auth_headers(token, csrf=False))
    data = AdminSummaryOut.model_validate(response.json_body["data"])
    assert data.total_member_count == 1
    assert data.today_entrant_count == 0
    assert data.weekly_active_ratio == 0.0
    assert data.carried_over_days == 2  # 8/25 발행분이 8/27까지 걸려 있다
    assert data.lead_time_days == 0


def test_admin_mutations_leave_an_audit_trail(api_client: Any, write_session: Session) -> None:
    """관리자 변경 조작은 전건 기록한다 (백엔드 문서 §13)."""
    token = curator_token(api_client, write_session)
    with freeze_time(AUG_27):
        api_client.http.put(
            "/admin/exhibitions/2026-08-27",
            headers=auth_headers(token),
            body=json_body({"title": "전시", "theme": "테마"}),
        )
    rows = q.fetch(write_session, AuditLog)
    assert len(rows) == 1
    assert rows[0].action == "exhibition.save"
    assert rows[0].actor_role == "curator"
    assert rows[0].target_id == "2026-08-27"
    assert rows[0].request_id
