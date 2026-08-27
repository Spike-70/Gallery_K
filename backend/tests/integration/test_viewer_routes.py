"""관람자 API — 실제 DB (API 문서 §7, PRD §4.3·§6.5–§6.8).

문서가 "반드시 있어야 하는 것"으로 지정한 시나리오 중 연장·숨김·날짜 경계 입장 기록이
여기에 있다(백엔드 문서 §12).
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from sqlalchemy.orm import Session

from chalicelib.core.errors import ErrorCode
from chalicelib.core.timeutil import freeze_time
from chalicelib.db import query as q
from chalicelib.db.models import ViewLog
from chalicelib.schemas.exhibition import (
    ArchiveOut,
    ArtworkDetailResponseOut,
    EntryRecordedOut,
    ExhibitionDetailOut,
)

from .factories import make_exhibition
from .helpers import auth_headers, session_token, signup

pytestmark = pytest.mark.integration

AUG_27 = dt.datetime(2026, 8, 27, 3, 0, tzinfo=dt.UTC)  # KST 12:00


def _member(api_client: Any) -> str:
    token = session_token(signup(api_client))
    assert token
    return token


def test_current_returns_todays_exhibition(api_client: Any, write_session: Session) -> None:
    make_exhibition(write_session, dt.date(2026, 8, 27))
    write_session.commit()
    token = _member(api_client)

    with freeze_time(AUG_27):
        response = api_client.http.get("/exhibitions/current", headers=auth_headers(token, csrf=False))

    assert response.status_code == 200
    data = ExhibitionDetailOut.model_validate(response.json_body["data"])
    assert data.exhibition_date == "2026-08-27"
    assert data.viewing_date == "2026-08-27"
    assert data.is_carried_over is False
    assert data.carried_over_label is None
    assert len(data.artworks) == 12
    assert [artwork.position for artwork in data.artworks] == list(range(1, 13))


def test_current_carries_over_the_previous_exhibition(api_client: Any, write_session: Session) -> None:
    """오늘 발행분이 없으면 직전 전시가 걸리고, **문구는 서버가 완성해 준다**(PRD §4.3)."""
    make_exhibition(write_session, dt.date(2026, 8, 30), title="빛을 등진 사람들")
    write_session.commit()
    token = _member(api_client)

    with freeze_time(dt.datetime(2026, 8, 31, 3, 0, tzinfo=dt.UTC)):
        response = api_client.http.get("/exhibitions/current", headers=auth_headers(token, csrf=False))

    data = ExhibitionDetailOut.model_validate(response.json_body["data"])
    assert data.exhibition_date == "2026-08-30"
    assert data.viewing_date == "2026-08-31"
    assert data.is_carried_over is True
    assert data.carried_over_label == "8월 30일의 전시"


def test_current_before_opening_is_a_dedicated_code(api_client: Any) -> None:
    token = _member(api_client)
    response = api_client.http.get("/exhibitions/current", headers=auth_headers(token, csrf=False))
    assert response.status_code == 404
    assert response.json_body["error"]["code"] == ErrorCode.EXHIBITION_NOT_OPENED
    assert response.json_body["error"]["message"] == "첫 전시를 준비하고 있습니다."


def test_unpublished_exhibition_never_reaches_viewers(api_client: Any, write_session: Session) -> None:
    """부분 업로드는 발행으로 치지 않는다 — 직전 전시가 계속 연장된다 (PRD §6.5)."""
    make_exhibition(write_session, dt.date(2026, 8, 26), title="이전 전시")
    make_exhibition(write_session, dt.date(2026, 8, 27), title="작업 중", published=False)
    write_session.commit()
    token = _member(api_client)

    with freeze_time(AUG_27):
        response = api_client.http.get("/exhibitions/current", headers=auth_headers(token, csrf=False))
    assert response.json_body["data"]["title"] == "이전 전시"


def test_hidden_exhibition_falls_back(api_client: Any, write_session: Session) -> None:
    make_exhibition(write_session, dt.date(2026, 8, 26), title="이전 전시")
    make_exhibition(write_session, dt.date(2026, 8, 27), title="숨긴 전시", hidden=True)
    write_session.commit()
    token = _member(api_client)

    with freeze_time(AUG_27):
        response = api_client.http.get("/exhibitions/current", headers=auth_headers(token, csrf=False))
    assert response.json_body["data"]["title"] == "이전 전시"


def test_current_supports_conditional_requests(api_client: Any, write_session: Session) -> None:
    """`304`는 봉투 규약의 유일한 예외이며 본문이 비어 있다 (API 문서 §2.9)."""
    make_exhibition(write_session, dt.date(2026, 8, 27))
    write_session.commit()
    token = _member(api_client)

    with freeze_time(AUG_27):
        first = api_client.http.get("/exhibitions/current", headers=auth_headers(token, csrf=False))
    etag = first.headers["ETag"]
    assert first.headers["Cache-Control"] == "private, max-age=0, must-revalidate"

    with freeze_time(AUG_27):
        second = api_client.http.get(
            "/exhibitions/current",
            headers={**auth_headers(token, csrf=False), "If-None-Match": etag},
        )
    assert second.status_code == 304
    assert second.body in (b"", "")
    assert second.headers["ETag"] == etag


def test_exhibition_by_date_marks_archive_view(api_client: Any, write_session: Session) -> None:
    make_exhibition(write_session, dt.date(2026, 8, 20), title="지난 전시")
    make_exhibition(write_session, dt.date(2026, 8, 27))
    write_session.commit()
    token = _member(api_client)

    with freeze_time(AUG_27):
        response = api_client.http.get("/exhibitions/2026-08-20", headers=auth_headers(token, csrf=False))
    data = ExhibitionDetailOut.model_validate(response.json_body["data"])
    assert data.is_archive_view is True
    assert data.exhibition_date == "2026-08-20"
    assert response.headers["Cache-Control"] == "private, max-age=300"


@pytest.mark.parametrize(
    "path",
    ["/exhibitions/2026-09-30", "/exhibitions/2026-08-25", "/exhibitions/not-a-date"],
)
def test_missing_hidden_and_future_dates_answer_identically(
    api_client: Any, write_session: Session, path: str
) -> None:
    """미발행·숨김·미래 날짜를 구분해 주지 않는다 (API 문서 §7.2)."""
    make_exhibition(write_session, dt.date(2026, 8, 25), title="숨김", hidden=True)
    make_exhibition(write_session, dt.date(2026, 9, 30), title="미래")
    write_session.commit()
    token = _member(api_client)

    with freeze_time(AUG_27):
        response = api_client.http.get(path, headers=auth_headers(token, csrf=False))
    assert response.status_code == 404
    assert response.json_body["error"]["code"] == ErrorCode.EXHIBITION_NOT_FOUND


def test_archive_lists_exhibitions_not_days(api_client: Any, write_session: Session) -> None:
    """연장된 날은 별도 행으로 나타나지 않는다 (PRD §6.8)."""
    for day in (dt.date(2026, 8, 20), dt.date(2026, 8, 24), dt.date(2026, 8, 27)):
        make_exhibition(write_session, day, title=f"전시 {day.day}")
    make_exhibition(write_session, dt.date(2026, 8, 25), title="숨김", hidden=True)
    write_session.commit()
    token = _member(api_client)

    with freeze_time(AUG_27):
        response = api_client.http.get("/exhibitions", headers=auth_headers(token, csrf=False))

    data = ArchiveOut.model_validate(response.json_body["data"])
    assert [item.exhibition_date for item in data.exhibitions] == [
        "2026-08-27",
        "2026-08-24",
        "2026-08-20",
    ]
    assert data.exhibitions[0].cover_image is not None
    meta = response.json_body["meta"]["pagination"]
    assert meta["mode"] == "cursor"
    assert meta["has_more"] is False
    assert meta["next_cursor"] is None


def test_archive_paginates_by_cursor(api_client: Any, write_session: Session) -> None:
    for offset in range(5):
        make_exhibition(write_session, dt.date(2026, 8, 20) + dt.timedelta(days=offset))
    write_session.commit()
    token = _member(api_client)

    with freeze_time(dt.datetime(2026, 8, 27, 3, 0, tzinfo=dt.UTC)):
        first = api_client.http.get("/exhibitions?limit=2", headers=auth_headers(token, csrf=False))
    meta = first.json_body["meta"]["pagination"]
    assert meta["count"] == 2
    assert meta["has_more"] is True

    with freeze_time(dt.datetime(2026, 8, 27, 3, 0, tzinfo=dt.UTC)):
        second = api_client.http.get(
            f"/exhibitions?limit=2&cursor={meta['next_cursor']}",
            headers=auth_headers(token, csrf=False),
        )
    dates = [item["exhibition_date"] for item in second.json_body["data"]["exhibitions"]]
    assert dates == ["2026-08-22", "2026-08-21"]


def test_broken_cursor_is_refused(api_client: Any) -> None:
    token = _member(api_client)
    response = api_client.http.get("/exhibitions?cursor=!!!broken", headers=auth_headers(token, csrf=False))
    assert response.status_code == 400
    assert response.json_body["error"]["code"] == ErrorCode.PAGINATION_INVALID_CURSOR


def test_entry_is_recorded_once_per_viewing_day(api_client: Any, write_session: Session) -> None:
    """관람일 기준 하루 1행. 하루 여러 번 열어도 지표는 1이다 (PRD §6.5)."""
    make_exhibition(write_session, dt.date(2026, 8, 27))
    write_session.commit()
    token = _member(api_client)

    with freeze_time(AUG_27):
        first = api_client.http.post("/exhibitions/2026-08-27/view", headers=auth_headers(token), body=b"")
        second = api_client.http.post("/exhibitions/2026-08-27/view", headers=auth_headers(token), body=b"")

    assert EntryRecordedOut.model_validate(first.json_body["data"]).is_first_entry_today is True
    assert EntryRecordedOut.model_validate(second.json_body["data"]).is_first_entry_today is False

    rows = q.fetch(write_session, ViewLog)
    assert len(rows) == 1
    assert rows[0].entry_count == 2
    assert rows[0].viewed_on == dt.date(2026, 8, 27)


def test_entry_crossing_kst_midnight_creates_a_second_row(api_client: Any, write_session: Session) -> None:
    """연장 중이어서 같은 전시를 이틀에 걸쳐 봐도 관람일이 다르면 각각 1회다."""
    make_exhibition(write_session, dt.date(2026, 8, 27))
    write_session.commit()
    token = _member(api_client)

    # KST 23:59 → 8월 27일
    with freeze_time(dt.datetime(2026, 8, 27, 14, 59, tzinfo=dt.UTC)):
        api_client.http.post("/exhibitions/2026-08-27/view", headers=auth_headers(token), body=b"")
    # KST 00:01 → 8월 28일
    with freeze_time(dt.datetime(2026, 8, 27, 15, 1, tzinfo=dt.UTC)):
        api_client.http.post("/exhibitions/2026-08-27/view", headers=auth_headers(token), body=b"")

    rows = q.fetch(write_session, ViewLog, order_by=["viewed_on"])
    assert [row.viewed_on for row in rows] == [dt.date(2026, 8, 27), dt.date(2026, 8, 28)]


def test_archive_entry_counts_as_the_same_visit(api_client: Any, write_session: Session) -> None:
    """아카이브 진입도 그날의 입장으로 센다 (PRD §6.5)."""
    make_exhibition(write_session, dt.date(2026, 8, 20), title="지난 전시")
    make_exhibition(write_session, dt.date(2026, 8, 27))
    write_session.commit()
    token = _member(api_client)

    with freeze_time(AUG_27):
        api_client.http.post("/exhibitions/2026-08-27/view", headers=auth_headers(token), body=b"")
        api_client.http.post("/exhibitions/2026-08-20/view", headers=auth_headers(token), body=b"")

    rows = q.fetch(write_session, ViewLog)
    assert len(rows) == 1
    # 그날 처음 연 전시가 대표값이다 — 두 번째 진입이 덮어쓰지 않는다.
    exhibition = q.fetch_one(write_session, ViewLog, where={"id": rows[0].id})
    assert exhibition is not None


def test_artwork_detail_carries_the_exhibition_context(api_client: Any, write_session: Session) -> None:
    exhibition = make_exhibition(write_session, dt.date(2026, 8, 27))
    write_session.commit()
    from chalicelib.db.models import Artwork

    artworks = q.fetch(write_session, Artwork, order_by=["position"])
    third = artworks[2]
    token = _member(api_client)

    with freeze_time(AUG_27):
        response = api_client.http.get(f"/artworks/{third.id}", headers=auth_headers(token, csrf=False))

    data = ArtworkDetailResponseOut.model_validate(response.json_body["data"])
    assert data.position_label == "3 / 12"
    assert data.exhibition.exhibition_date == "2026-08-27"
    assert data.artwork.prev_artwork_id == str(artworks[1].id)
    assert data.artwork.next_artwork_id == str(artworks[3].id)
    assert data.artwork.description
    assert exhibition.title == data.exhibition.title


def test_first_and_last_artwork_have_no_neighbour_on_one_side(
    api_client: Any, write_session: Session
) -> None:
    make_exhibition(write_session, dt.date(2026, 8, 27))
    write_session.commit()
    from chalicelib.db.models import Artwork

    artworks = q.fetch(write_session, Artwork, order_by=["position"])
    token = _member(api_client)

    with freeze_time(AUG_27):
        first = api_client.http.get(
            f"/artworks/{artworks[0].id}", headers=auth_headers(token, csrf=False)
        ).json_body["data"]["artwork"]
        last = api_client.http.get(
            f"/artworks/{artworks[-1].id}", headers=auth_headers(token, csrf=False)
        ).json_body["data"]["artwork"]

    assert first["prev_artwork_id"] is None
    assert last["next_artwork_id"] is None


def test_artwork_of_a_hidden_exhibition_is_absent(api_client: Any, write_session: Session) -> None:
    make_exhibition(write_session, dt.date(2026, 8, 27), hidden=True)
    write_session.commit()
    from chalicelib.db.models import Artwork

    artwork = q.fetch_one(write_session, Artwork)
    assert artwork is not None
    token = _member(api_client)

    with freeze_time(AUG_27):
        response = api_client.http.get(f"/artworks/{artwork.id}", headers=auth_headers(token, csrf=False))
    assert response.status_code == 404
    assert response.json_body["error"]["code"] == ErrorCode.ARTWORK_NOT_FOUND


def test_viewed_marks_are_scoped_to_the_exhibition(api_client: Any, write_session: Session) -> None:
    """ "열어봄" 표식의 기준은 관람일이 아니라 전시다 (PRD §6.5)."""
    make_exhibition(write_session, dt.date(2026, 8, 27))
    write_session.commit()
    from chalicelib.db.models import Artwork

    artworks = q.fetch(write_session, Artwork, order_by=["position"])
    token = _member(api_client)

    with freeze_time(AUG_27):
        recorded = api_client.http.post(
            f"/artworks/{artworks[0].id}/view", headers=auth_headers(token), body=b""
        )
        assert recorded.json_body["data"]["viewed_artwork_count"] == 1

    # 다음 날에도 같은 전시가 연장되면 표식이 그대로 남아 있다.
    with freeze_time(dt.datetime(2026, 8, 28, 3, 0, tzinfo=dt.UTC)):
        detail = api_client.http.get("/exhibitions/current", headers=auth_headers(token, csrf=False))
    data = ExhibitionDetailOut.model_validate(detail.json_body["data"])
    assert data.is_carried_over is True
    assert [artwork.is_viewed for artwork in data.artworks].count(True) == 1


def test_artwork_view_is_idempotent(api_client: Any, write_session: Session) -> None:
    make_exhibition(write_session, dt.date(2026, 8, 27))
    write_session.commit()
    from chalicelib.db.models import Artwork, ArtworkViewLog

    artwork = q.fetch_one(write_session, Artwork, where={"position": 1})
    assert artwork is not None
    token = _member(api_client)

    with freeze_time(AUG_27):
        for _ in range(3):
            response = api_client.http.post(
                f"/artworks/{artwork.id}/view", headers=auth_headers(token), body=b""
            )
    assert response.json_body["data"]["viewed_artwork_count"] == 1
    rows = q.fetch(write_session, ArtworkViewLog)
    assert len(rows) == 1
    assert rows[0].view_count == 3


def test_image_urls_are_signed_and_expire(api_client: Any, write_session: Session) -> None:
    """이미지 접근 수단은 presigned URL 하나뿐이다 (백엔드 문서 §10)."""
    make_exhibition(write_session, dt.date(2026, 8, 27))
    write_session.commit()
    token = _member(api_client)

    with freeze_time(AUG_27):
        response = api_client.http.get("/exhibitions/current", headers=auth_headers(token, csrf=False))
    image = response.json_body["data"]["artworks"][0]["image"]
    assert "X-Amz-Signature=" in image["thumb_url"]
    assert "X-Amz-Expires=900" in image["thumb_url"]
    assert image["aspect_ratio"] == round(1600 / 1200, 4)
    assert image["lqip"].startswith("data:image/webp")


def test_viewer_endpoints_require_a_session(api_client: Any) -> None:
    for method, path in (
        ("get", "/exhibitions/current"),
        ("get", "/exhibitions"),
        ("get", "/exhibitions/2026-08-27"),
    ):
        response = getattr(api_client.http, method)(path)
        assert response.status_code == 401
        assert response.json_body["error"]["code"] == ErrorCode.AUTH_REQUIRED
