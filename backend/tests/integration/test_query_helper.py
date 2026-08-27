"""공용 DB 헬퍼 (백엔드 문서 §4). 실제 PostgreSQL로만 검증한다."""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm import Session

from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.db import query as q
from chalicelib.db.models import AppUser, Artwork, Exhibition
from chalicelib.db.models.enums import ImageStatus, UserRole

pytestmark = pytest.mark.integration


def _user(session: Session, phone: str, name: str = "관람자", **extra: object) -> AppUser:
    return q.insert(
        session,
        AppUser,
        {"phone": phone, "password_hash": "x" * 60, "name": name, **extra},
    )


def _exhibition(session: Session, day: dt.date, **extra: object) -> Exhibition:
    return q.insert(session, Exhibition, {"exhibition_date": day, **extra})


def _artwork(session: Session, exhibition: Exhibition, position: int, **extra: object) -> Artwork:
    return q.insert(session, Artwork, {"exhibition_id": exhibition.id, "position": position, **extra})


def test_insert_and_fetch_one(session: Session) -> None:
    created = _user(session, "01012340001", "김관람")
    found = q.fetch_one(session, AppUser, where={"phone": "01012340001"})
    assert found is not None
    assert found.id == created.id
    assert found.role == UserRole.VIEWER
    assert found.notify_at == dt.time(7, 30)


def test_filter_operators(session: Session) -> None:
    _user(session, "01012340002", "가나다")
    _user(session, "01012340003", "라마바")
    assert q.count(session, AppUser, where={"name__contains": "나"}) == 1
    assert q.count(session, AppUser, where={"name__startswith": "라"}) == 1
    assert q.count(session, AppUser, where={"phone__in": ["01012340002", "01012340003"]}) == 2
    assert q.count(session, AppUser, where={"phone__in": []}) == 0
    assert q.count(session, AppUser, where={"blocked_at__isnull": True}) == 2
    assert q.count(session, AppUser, where={"phone__gte": "01012340003"}) == 1


def test_q_combination(session: Session) -> None:
    _user(session, "01012340004", "가나다", is_blocked=True, blocked_at=dt.datetime.now(dt.UTC))
    _user(session, "01012340005", "라마바")
    both = q.Q(name__contains="가") | q.Q(is_blocked=True)
    assert q.count(session, AppUser, where=both) == 1
    negated = ~q.Q(is_blocked=True)
    assert q.count(session, AppUser, where=negated) == 1


def test_relationship_path_builds_the_join(session: Session) -> None:
    exhibition = _exhibition(session, dt.date(2026, 8, 27), title="빛을 등진 사람들")
    _artwork(session, exhibition, 1, title="진주 귀걸이")
    other = _exhibition(session, dt.date(2026, 8, 26))
    _artwork(session, other, 1)
    session.flush()

    rows = q.fetch(session, Artwork, where={"exhibition__exhibition_date": dt.date(2026, 8, 27)})
    assert len(rows) == 1
    assert rows[0].title == "진주 귀걸이"


def test_lazy_loading_is_forbidden_by_default(session: Session) -> None:
    """N+1의 출처를 원천 차단한다 — 로딩을 지정하지 않으면 접근 자체가 예외다."""
    exhibition = _exhibition(session, dt.date(2026, 8, 27))
    _artwork(session, exhibition, 1)
    session.flush()
    session.expire_all()

    loaded = q.fetch_one(session, Exhibition, where={"exhibition_date": dt.date(2026, 8, 27)})
    assert loaded is not None
    with pytest.raises(InvalidRequestError, match=r"lazy=.raise."):
        _ = loaded.artworks

    with_children = q.fetch_one(
        session,
        Exhibition,
        where={"exhibition_date": dt.date(2026, 8, 27)},
        selectin=["artworks"],
    )
    assert with_children is not None
    assert len(with_children.artworks) == 1


def test_projection_returns_dicts(session: Session) -> None:
    _user(session, "01012340006", "가나다")
    rows = q.fetch(session, AppUser, columns=["id", "name"])
    assert rows == [{"id": rows[0]["id"], "name": "가나다"}]


def test_ordering_and_limit(session: Session) -> None:
    for day in (dt.date(2026, 8, 25), dt.date(2026, 8, 27), dt.date(2026, 8, 26)):
        _exhibition(session, day)
    session.flush()
    rows = q.fetch(session, Exhibition, order_by=["-exhibition_date"], limit=2)
    assert [row.exhibition_date for row in rows] == [dt.date(2026, 8, 27), dt.date(2026, 8, 26)]


def test_optimistic_locking_rejects_stale_writes(session: Session) -> None:
    exhibition = _exhibition(session, dt.date(2026, 8, 27), title="처음")
    session.flush()
    assert exhibition.version == 1

    affected = q.update(
        session, Exhibition, where={"id": exhibition.id}, values={"title": "두번째"}, expected_version=1
    )
    assert affected == 1

    with pytest.raises(AppError) as caught:
        q.update(
            session,
            Exhibition,
            where={"id": exhibition.id},
            values={"title": "세번째"},
            expected_version=1,
        )
    assert caught.value.code == ErrorCode.CONFLICT_VERSION


def test_upsert_is_idempotent(session: Session) -> None:
    user = _user(session, "01012340007")
    exhibition = _exhibition(session, dt.date(2026, 8, 27))
    session.flush()
    now = dt.datetime.now(dt.UTC)

    from chalicelib.db.models import ViewLog

    for _ in range(3):
        q.upsert(
            session,
            ViewLog,
            values={
                "id": uuid.uuid4(),
                "user_id": user.id,
                "viewed_on": dt.date(2026, 8, 27),
                "exhibition_id": exhibition.id,
                "first_entered_at": now,
                "last_entered_at": now,
                "created_at": now,
                "updated_at": now,
            },
            conflict=["user_id", "viewed_on"],
            update_values={"last_entered_at": now, "entry_count": ViewLog.entry_count + 1},
        )
    rows = q.fetch(session, ViewLog, where={"user_id": user.id})
    assert len(rows) == 1
    assert rows[0].entry_count == 3


def test_aggregate_groups(session: Session) -> None:
    exhibition = _exhibition(session, dt.date(2026, 8, 27))
    for position in (1, 2, 3):
        _artwork(session, exhibition, position, image_status=ImageStatus.EMPTY)
    session.flush()
    rows = q.aggregate(
        session,
        Artwork,
        values={"total": func.count()},
        group_by=["exhibition_id"],
    )
    assert rows == [{"exhibition_id": exhibition.id, "total": 3}]


def test_delete_relies_on_database_cascade(session: Session) -> None:
    exhibition = _exhibition(session, dt.date(2026, 8, 27))
    _artwork(session, exhibition, 1)
    session.flush()

    q.delete(session, Exhibition, where={"id": exhibition.id})
    session.flush()
    assert q.count(session, Artwork) == 0


def test_unknown_field_is_rejected(session: Session) -> None:
    with pytest.raises(AppError):
        q.fetch(session, AppUser, where={"nickname": "없는필드"})


def test_relationship_path_is_refused_in_update(session: Session) -> None:
    with pytest.raises(AppError):
        q.update(
            session,
            Artwork,
            where={"exhibition__exhibition_date": dt.date(2026, 8, 27)},
            values={"title": "x"},
        )


def test_constraint_violation_surfaces_as_integrity_error(session: Session) -> None:
    _user(session, "01012340008")
    session.flush()
    with pytest.raises(IntegrityError):
        _user(session, "01012340008")
        session.flush()


def test_exists_stops_at_the_first_row(session: Session) -> None:
    """존재 확인에 전체 스캔을 시키지 않는다 — `count(*)`가 아니어야 한다."""
    from sqlalchemy import event

    _user(session, "01012340010")
    session.flush()

    statements: list[str] = []

    def record(conn: object, cursor: object, statement: str, *args: object) -> None:
        statements.append(" ".join(statement.split()).upper())

    bind = session.get_bind()
    event.listen(bind, "before_cursor_execute", record)
    try:
        assert q.exists(session, AppUser, where={"phone": "01012340010"}) is True
        assert q.exists(session, AppUser, where={"phone": "01099999999"}) is False
    finally:
        event.remove(bind, "before_cursor_execute", record)

    assert statements, "질의가 실행되지 않았습니다"
    assert all("COUNT(" not in statement for statement in statements), statements
    assert all("LIMIT" in statement for statement in statements), statements


def test_search_metacharacters_are_literal(session: Session) -> None:
    """검색어의 `%`·`_`는 글자 그대로다 — 이스케이프하지 않으면 `%` 하나로 전체가 나온다."""
    _user(session, "01012340011", "김가나")
    _user(session, "01012340012", "100%정직")
    _user(session, "01012340013", "김a나")
    session.flush()

    assert q.count(session, AppUser, where={"name__contains": "%"}) == 1
    assert q.count(session, AppUser, where={"name__contains": "100%"}) == 1
    # `_`도 와일드카드가 아니다. 그렇지 않으면 "김a나"까지 잡힌다.
    assert q.count(session, AppUser, where={"name__contains": "김_나"}) == 0


def test_version_conflict_reports_the_current_version(session: Session) -> None:
    """클라이언트가 무엇으로 다시 시도해야 하는지 알 수 있어야 한다 (API 문서 §5.1)."""
    exhibition = _exhibition(session, dt.date(2026, 8, 27), title="처음")
    session.flush()
    q.update(
        session,
        Exhibition,
        where={"id": exhibition.id},
        values={"title": "두번째"},
        expected_version=1,
    )

    with pytest.raises(AppError) as caught:
        q.update(
            session,
            Exhibition,
            where={"id": exhibition.id},
            values={"title": "세번째"},
            expected_version=1,
        )
    assert caught.value.details == {"current_version": 2}
