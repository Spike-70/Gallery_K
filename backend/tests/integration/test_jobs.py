"""스케줄 루틴 — 실제 DB (백엔드 문서 §11, PRD §6.12, DB 문서 §10)."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from sqlalchemy.orm import Session

from chalicelib.core.timeutil import freeze_time, kst_datetime
from chalicelib.db import query as q
from chalicelib.db.models import (
    AppUser,
    ArtworkViewLog,
    AuditLog,
    AuthThrottle,
    Exhibition,
    NotificationLog,
    PushSubscription,
    ViewLog,
)
from chalicelib.integrations import webpush
from chalicelib.jobs import dispatch_due_notifications, run_nightly_maintenance
from chalicelib.services import notification_service

from .factories import make_exhibition
from .fake_storage import install as install_fake_storage
from .helpers import make_curator

pytestmark = pytest.mark.integration

TODAY = dt.date(2026, 8, 27)
AUG_27_MORNING = dt.datetime(2026, 8, 26, 22, 30, tzinfo=dt.UTC)  # KST 8/27 07:30


@pytest.fixture()
def sent_pushes(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """웹 푸시를 보내지 않고 기록만 한다. 외부 어댑터가 하나라 갈아 끼우기 쉽다."""
    delivered: list[str] = []

    def _send(subscription: Any, payload: str) -> webpush.DeliveryResult:
        delivered.append(payload)
        return webpush.DeliveryResult("sent")

    monkeypatch.setattr(webpush, "send", _send)
    return delivered


def _member(session: Session, phone: str = "01011112222", *, notify: bool = True) -> AppUser:
    user = q.insert(
        session,
        AppUser,
        {
            "phone": phone,
            "password_hash": "x" * 60,
            "name": "관람자",
            "notify_enabled": notify,
            "notify_at": dt.time(7, 30),
        },
    )
    q.insert(
        session,
        PushSubscription,
        {
            "user_id": user.id,
            "endpoint": f"https://example.com/push/{phone}",
            "endpoint_hash": f"hash-{phone}",
            "p256dh": "key",
            "auth": "auth",
        },
    )
    session.commit()
    return user


def test_due_notifications_are_sent_and_marked(
    write_session: Session, db_session_factory: Any, sent_pushes: list[str]
) -> None:
    user = _member(write_session)
    exhibition = make_exhibition(write_session, TODAY)
    write_session.commit()

    with freeze_time(AUG_27_MORNING - dt.timedelta(minutes=1)):
        notification_service.queue_morning_notifications(
            write_session,
            exhibition_id=exhibition.id,
            exhibition_date=TODAY,
            exhibition_title="빛을 등진 사람들",
            published_at=kst_datetime(TODAY, dt.time(6, 0)),
        )
        write_session.commit()

    # 예정 시각 전에는 나가지 않는다.
    with freeze_time(AUG_27_MORNING - dt.timedelta(minutes=10)):
        early = dispatch_due_notifications(db_session_factory)
    assert early.considered == 0
    assert sent_pushes == []

    with freeze_time(AUG_27_MORNING + dt.timedelta(minutes=1)):
        report = dispatch_due_notifications(db_session_factory)

    assert report.considered == 1
    assert report.sent == 1
    assert len(sent_pushes) == 1
    assert "빛을 등진 사람들" in sent_pushes[0]
    # 문구는 전시 제목까지만 담는다 — 그림 정보는 없다.
    assert "그림" not in sent_pushes[0]

    row = q.fetch_one(write_session, NotificationLog, where={"user_id": user.id})
    assert row is not None
    write_session.refresh(row)
    assert row.status == "sent"
    assert row.sent_at is not None


def test_dispatch_is_idempotent_across_duplicate_runs(
    write_session: Session, db_session_factory: Any, sent_pushes: list[str]
) -> None:
    """중복 기동은 조건부 상태 갱신으로 무해하다."""
    user = _member(write_session)
    exhibition = make_exhibition(write_session, TODAY)
    write_session.commit()
    notification_service.queue_morning_notifications(
        write_session,
        exhibition_id=exhibition.id,
        exhibition_date=TODAY,
        exhibition_title="전시",
        published_at=kst_datetime(TODAY, dt.time(6, 0)),
    )
    write_session.commit()

    with freeze_time(AUG_27_MORNING + dt.timedelta(minutes=1)):
        first = dispatch_due_notifications(db_session_factory)
        second = dispatch_due_notifications(db_session_factory)

    assert first.sent == 1
    assert second.considered == 0
    assert len(sent_pushes) == 1
    assert q.count(write_session, NotificationLog, where={"user_id": user.id}) == 1


def test_cutoff_stops_late_notifications(
    write_session: Session, db_session_factory: Any, sent_pushes: list[str]
) -> None:
    """아침 알림은 시의성이 전부다. 21시를 넘기면 재시도하지 않고 스킵으로 끝난다."""
    _member(write_session)
    exhibition = make_exhibition(write_session, TODAY)
    write_session.commit()
    notification_service.queue_morning_notifications(
        write_session,
        exhibition_id=exhibition.id,
        exhibition_date=TODAY,
        exhibition_title="전시",
        published_at=kst_datetime(TODAY, dt.time(6, 0)),
    )
    write_session.commit()

    # KST 8/27 22:00
    with freeze_time(dt.datetime(2026, 8, 27, 13, 0, tzinfo=dt.UTC)):
        report = dispatch_due_notifications(db_session_factory)

    assert report.skipped == 1
    assert sent_pushes == []
    row = q.fetch_one(write_session, NotificationLog)
    assert row is not None
    write_session.refresh(row)
    assert row.status == "skipped"
    assert row.skip_reason == "cutoff_passed"


def test_publishing_after_the_cutoff_is_skipped_at_queue_time(
    write_session: Session,
) -> None:
    """컷오프를 넘긴 발행분은 큐에 넣는 시점에 이미 `skipped`다 (API 문서 §11.3)."""
    _member(write_session)
    exhibition = make_exhibition(write_session, TODAY)
    write_session.commit()

    notification_service.queue_morning_notifications(
        write_session,
        exhibition_id=exhibition.id,
        exhibition_date=TODAY,
        exhibition_title="전시",
        published_at=kst_datetime(TODAY, dt.time(22, 0)),
    )
    write_session.commit()

    row = q.fetch_one(write_session, NotificationLog)
    assert row is not None
    assert row.status == "skipped"
    assert row.skip_reason == "cutoff_passed"
    assert row.kind == "late_publish"


def test_late_publish_is_recorded_separately(write_session: Session) -> None:
    """알림 시각이 지난 뒤 발행된 것은 `late_publish`로 구분한다 (교차검토 X-16)."""
    _member(write_session)
    exhibition = make_exhibition(write_session, TODAY)
    write_session.commit()

    notification_service.queue_morning_notifications(
        write_session,
        exhibition_id=exhibition.id,
        exhibition_date=TODAY,
        exhibition_title="전시",
        published_at=kst_datetime(TODAY, dt.time(10, 0)),  # 07:30 이후
    )
    write_session.commit()

    row = q.fetch_one(write_session, NotificationLog)
    assert row is not None
    assert row.kind == "late_publish"
    assert row.status == "pending"


def test_members_who_opted_out_get_a_skipped_row(write_session: Session) -> None:
    """**보내지 않기로 한 경우에도 행을 남긴다** (DB 문서 §4.10).

    "왜 못 받았나"라는 문의에 답할 근거가 그 행이다.
    """
    _member(write_session, "01011112222", notify=False)
    exhibition = make_exhibition(write_session, TODAY)
    write_session.commit()

    queued = notification_service.queue_morning_notifications(
        write_session,
        exhibition_id=exhibition.id,
        exhibition_date=TODAY,
        exhibition_title="전시",
        published_at=kst_datetime(TODAY, dt.time(6, 0)),
    )
    write_session.commit()

    assert queued == 0  # 실제로 보낼 것은 없다
    rows = q.fetch(write_session, NotificationLog)
    assert len(rows) == 1
    assert rows[0].status == "skipped"
    assert rows[0].skip_reason == "notify_disabled"


def test_blocked_members_get_a_skipped_row(write_session: Session) -> None:
    """차단된 회원은 로그인할 수 없으므로 부르지 않되, 부르지 않은 이유는 남긴다."""
    user = _member(write_session, "01011112222")
    q.update(
        write_session,
        AppUser,
        where={"id": user.id},
        values={"is_blocked": True, "blocked_at": dt.datetime.now(dt.UTC)},
    )
    exhibition = make_exhibition(write_session, TODAY)
    write_session.commit()

    queued = notification_service.queue_morning_notifications(
        write_session,
        exhibition_id=exhibition.id,
        exhibition_date=TODAY,
        exhibition_title="전시",
        published_at=kst_datetime(TODAY, dt.time(6, 0)),
    )
    write_session.commit()

    assert queued == 0
    rows = q.fetch(write_session, NotificationLog)
    assert len(rows) == 1
    assert rows[0].skip_reason == "user_blocked"


def test_queueing_uses_a_single_statement_for_every_member(
    write_session: Session,
) -> None:
    """회원 수에 비례해 왕복하지 않는다 — 발행 요청이 느려지는 지점이 여기다."""
    from sqlalchemy import event

    for index in range(12):
        _member(write_session, f"010111122{index:02d}")
    exhibition = make_exhibition(write_session, TODAY)
    write_session.commit()

    inserts: list[str] = []

    def record(conn: Any, cursor: Any, statement: str, *args: Any) -> None:
        if statement.lstrip().upper().startswith("INSERT INTO NOTIFICATION_LOG"):
            inserts.append(statement)

    event.listen(write_session.get_bind(), "before_cursor_execute", record)
    try:
        notification_service.queue_morning_notifications(
            write_session,
            exhibition_id=exhibition.id,
            exhibition_date=TODAY,
            exhibition_title="전시",
            published_at=kst_datetime(TODAY, dt.time(6, 0)),
        )
        write_session.commit()
    finally:
        event.remove(write_session.get_bind(), "before_cursor_execute", record)

    assert q.count(write_session, NotificationLog) == 12
    assert len(inserts) == 1, f"INSERT 문이 {len(inserts)}회 실행되었습니다"


def test_a_member_without_a_subscription_is_skipped_with_a_reason(
    write_session: Session, db_session_factory: Any, sent_pushes: list[str]
) -> None:
    user = q.insert(
        write_session,
        AppUser,
        {"phone": "01099998888", "password_hash": "x" * 60, "name": "구독없음"},
    )
    exhibition = make_exhibition(write_session, TODAY)
    write_session.commit()
    notification_service.queue_morning_notifications(
        write_session,
        exhibition_id=exhibition.id,
        exhibition_date=TODAY,
        exhibition_title="전시",
        published_at=kst_datetime(TODAY, dt.time(6, 0)),
    )
    write_session.commit()

    with freeze_time(AUG_27_MORNING + dt.timedelta(minutes=1)):
        report = dispatch_due_notifications(db_session_factory)

    assert report.skipped == 1
    row = q.fetch_one(write_session, NotificationLog, where={"user_id": user.id})
    assert row is not None
    write_session.refresh(row)
    assert row.skip_reason == "no_subscription"


def test_a_gone_subscription_is_deactivated_immediately(
    write_session: Session, db_session_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """푸시 404/410이면 즉시 비활성 (DB 문서 §4.3)."""
    user = _member(write_session)
    exhibition = make_exhibition(write_session, TODAY)
    write_session.commit()
    notification_service.queue_morning_notifications(
        write_session,
        exhibition_id=exhibition.id,
        exhibition_date=TODAY,
        exhibition_title="전시",
        published_at=kst_datetime(TODAY, dt.time(6, 0)),
    )
    write_session.commit()

    monkeypatch.setattr(webpush, "send", lambda *_: webpush.DeliveryResult("gone", "HTTP 410"))
    with freeze_time(AUG_27_MORNING + dt.timedelta(minutes=1)):
        report = dispatch_due_notifications(db_session_factory)

    assert report.deactivated == 1
    subscription = q.fetch_one(write_session, PushSubscription, where={"user_id": user.id})
    assert subscription is not None
    write_session.refresh(subscription)
    assert subscription.is_active is False
    assert subscription.deactivated_at is not None


def test_server_errors_accumulate_then_fail(
    write_session: Session, db_session_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """5xx는 재시도 누적 후 실패 처리."""
    _member(write_session)
    exhibition = make_exhibition(write_session, TODAY)
    write_session.commit()
    notification_service.queue_morning_notifications(
        write_session,
        exhibition_id=exhibition.id,
        exhibition_date=TODAY,
        exhibition_title="전시",
        published_at=kst_datetime(TODAY, dt.time(6, 0)),
    )
    write_session.commit()

    monkeypatch.setattr(webpush, "send", lambda *_: webpush.DeliveryResult("retryable", "HTTP 503"))
    with freeze_time(AUG_27_MORNING + dt.timedelta(minutes=1)):
        for _ in range(3):
            dispatch_due_notifications(db_session_factory)

    row = q.fetch_one(write_session, NotificationLog)
    assert row is not None
    write_session.refresh(row)
    assert row.status == "failed"
    assert row.attempt_count == 3
    assert row.last_error == "HTTP 503"


def test_zero_work_still_logs(write_session: Session, db_session_factory: Any) -> None:
    """처리 0건도 로그를 남긴다 — 잡이 죽었는지 알 수 있어야 한다."""
    report = dispatch_due_notifications(db_session_factory)
    assert report.considered == 0
    assert report.sent == 0


def test_nightly_deletes_expired_rows(
    write_session: Session, db_session_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fake_storage(monkeypatch)
    user = _member(write_session)
    exhibition = make_exhibition(write_session, dt.date(2026, 1, 1))
    old = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)

    q.insert(
        write_session,
        ViewLog,
        {
            "user_id": user.id,
            "viewed_on": dt.date(2025, 1, 1),
            "exhibition_id": exhibition.id,
            "first_entered_at": old,
            "last_entered_at": old,
        },
    )
    from chalicelib.db.models import Artwork

    artwork = q.fetch_one(write_session, Artwork, where={"exhibition_id": exhibition.id})
    assert artwork is not None
    q.insert(
        write_session,
        ArtworkViewLog,
        {
            "user_id": user.id,
            "artwork_id": artwork.id,
            "exhibition_id": exhibition.id,
            "first_viewed_on": dt.date(2025, 1, 1),
            "first_viewed_at": old,
            "last_viewed_at": old,
        },
    )
    q.insert(
        write_session,
        NotificationLog,
        {
            "user_id": user.id,
            "kind": "morning_exhibition",
            "dedupe_key": "old:1",
            "status": "sent",
            "scheduled_for": old,
            "created_at": old,
            "updated_at": old,
        },
    )
    q.insert(
        write_session,
        AuditLog,
        {"action": "exhibition.save", "created_at": dt.datetime(2024, 1, 1, tzinfo=dt.UTC)},
    )
    q.insert(
        write_session,
        AuthThrottle,
        {
            "throttle_key": "login:01000000001",
            "scope": "login",
            "fail_count": 3,
            "first_failed_at": old,
            "last_failed_at": old,
            "created_at": old,
            "updated_at": old,
        },
    )
    q.insert(
        write_session,
        PushSubscription,
        {
            "user_id": user.id,
            "endpoint": "https://example.com/push/dead",
            "endpoint_hash": "dead",
            "p256dh": "k",
            "auth": "a",
            "is_active": False,
            "deactivated_at": old,
        },
    )
    write_session.commit()

    with freeze_time(dt.datetime(2026, 8, 27, 18, 0, tzinfo=dt.UTC)):
        report = run_nightly_maintenance(db_session_factory)

    assert report.view_logs_deleted == 1
    assert report.artwork_view_logs_deleted == 1
    assert report.notifications_deleted == 1
    assert report.audit_logs_deleted == 1
    assert report.throttles_deleted == 1
    assert report.subscriptions_deleted == 1

    assert q.count(write_session, ViewLog) == 0
    assert q.count(write_session, AuthThrottle) == 0
    # 살아 있는 구독은 남는다.
    assert q.count(write_session, PushSubscription, where={"is_active": True}) == 1


def test_nightly_keeps_recent_rows(
    write_session: Session, db_session_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fake_storage(monkeypatch)
    user = _member(write_session)
    exhibition = make_exhibition(write_session, TODAY)
    now = dt.datetime(2026, 8, 27, 0, 0, tzinfo=dt.UTC)
    q.insert(
        write_session,
        ViewLog,
        {
            "user_id": user.id,
            "viewed_on": TODAY,
            "exhibition_id": exhibition.id,
            "first_entered_at": now,
            "last_entered_at": now,
        },
    )
    write_session.commit()

    with freeze_time(dt.datetime(2026, 8, 27, 18, 0, tzinfo=dt.UTC)):
        report = run_nightly_maintenance(db_session_factory)

    assert report.view_logs_deleted == 0
    assert q.count(write_session, ViewLog) == 1


def test_nightly_reclaims_only_unreferenced_objects(
    write_session: Session, db_session_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """살아 있는 키를 먼저 모으고 그 밖의 것만 지운다."""
    storage = install_fake_storage(monkeypatch)
    exhibition = make_exhibition(write_session, dt.date(2026, 1, 1), artwork_count=1)
    write_session.commit()
    from chalicelib.db.models import Artwork

    artwork = q.fetch_one(write_session, Artwork, where={"exhibition_id": exhibition.id})
    assert artwork is not None

    storage.objects[artwork.image_thumb_key] = b"live"
    storage.objects["artworks/2026-01-01/orphan/thumb.webp"] = b"orphan"
    storage.objects["uploads/2026-08-26/recent/file.jpg"] = b"too recent"

    with freeze_time(dt.datetime(2026, 8, 27, 18, 0, tzinfo=dt.UTC)):
        report = run_nightly_maintenance(db_session_factory)

    assert report.objects_reclaimed == 1
    assert storage.deleted == ["artworks/2026-01-01/orphan/thumb.webp"]
    assert artwork.image_thumb_key in storage.objects
    assert "uploads/2026-08-26/recent/file.jpg" in storage.objects


def test_carryover_alert_fires_once_per_period(
    write_session: Session, db_session_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """연장 2일 연속이면 큐레이터에게 1회. 3일째부터는 다시 보내지 않는다 (PRD §6.12)."""
    install_fake_storage(monkeypatch)
    make_curator(write_session)
    make_exhibition(write_session, dt.date(2026, 8, 25), title="25일 전시")
    write_session.commit()

    with freeze_time(dt.datetime(2026, 8, 27, 18, 0, tzinfo=dt.UTC)):  # KST 8/28
        first = run_nightly_maintenance(db_session_factory)
    with freeze_time(dt.datetime(2026, 8, 28, 18, 0, tzinfo=dt.UTC)):  # KST 8/29
        second = run_nightly_maintenance(db_session_factory)

    assert first.carryover_alerts_queued == 1
    assert second.carryover_alerts_queued == 0
    rows = q.fetch(write_session, NotificationLog, where={"kind": "curator_carryover"})
    assert len(rows) == 1
    assert rows[0].dedupe_key == "carryover:2026-08-25"


def test_carryover_alert_is_suppressed_during_a_notice_period(
    write_session: Session, db_session_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """쉬겠다고 미리 적어둔 사람에게 쉬고 있다고 알리는 것은 의미가 없다."""
    install_fake_storage(monkeypatch)
    make_curator(write_session)
    make_exhibition(write_session, dt.date(2026, 8, 25), title="25일 전시")
    from chalicelib.db.models import Notice

    q.insert(
        write_session,
        Notice,
        {
            "starts_on": dt.date(2026, 8, 26),
            "ends_on": dt.date(2026, 8, 30),
            "body": "휴관합니다.",
            "is_active": True,
        },
    )
    write_session.commit()

    with freeze_time(dt.datetime(2026, 8, 27, 18, 0, tzinfo=dt.UTC)):
        report = run_nightly_maintenance(db_session_factory)

    assert report.carryover_alerts_queued == 0
    rows = q.fetch(write_session, NotificationLog, where={"kind": "curator_carryover"})
    assert len(rows) == 1
    # 보내지 않기로 한 경우에도 이유가 남는다.
    assert rows[0].status == "skipped"
    assert rows[0].skip_reason == "notice_period"


def test_no_alert_before_the_threshold(
    write_session: Session, db_session_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """하루 걸렀다고 알림을 보내면 그 알림 자체가 부담이 된다."""
    install_fake_storage(monkeypatch)
    make_curator(write_session)
    make_exhibition(write_session, dt.date(2026, 8, 26), title="어제 전시")
    write_session.commit()

    with freeze_time(dt.datetime(2026, 8, 27, 18, 0, tzinfo=dt.UTC)):  # KST 8/28, 연장 2일
        report = run_nightly_maintenance(db_session_factory)
    assert report.carryover_alerts_queued == 1

    q.delete(write_session, NotificationLog, where={"kind": "curator_carryover"})
    q.delete(write_session, Exhibition, where={"exhibition_date": dt.date(2026, 8, 26)})
    make_exhibition(write_session, dt.date(2026, 8, 27), title="오늘 전시")
    write_session.commit()

    with freeze_time(dt.datetime(2026, 8, 27, 18, 0, tzinfo=dt.UTC)):  # KST 8/28, 연장 1일
        second = run_nightly_maintenance(db_session_factory)
    assert second.carryover_alerts_queued == 0


def test_dispatch_loads_subscriptions_in_one_query(
    write_session: Session, db_session_factory: Any, sent_pushes: list[str]
) -> None:
    """알림마다 구독을 조회하면 그것이 곧 N+1이다 (DB 문서 §7)."""
    from sqlalchemy import event

    for index in range(8):
        _member(write_session, f"010222233{index:02d}")
    exhibition = make_exhibition(write_session, TODAY)
    write_session.commit()
    notification_service.queue_morning_notifications(
        write_session,
        exhibition_id=exhibition.id,
        exhibition_date=TODAY,
        exhibition_title="전시",
        published_at=kst_datetime(TODAY, dt.time(6, 0)),
    )
    write_session.commit()

    selects: list[str] = []

    def record(conn: Any, cursor: Any, statement: str, *args: Any) -> None:
        normalized = " ".join(statement.split()).upper()
        if normalized.startswith("SELECT") and "FROM PUSH_SUBSCRIPTION" in normalized:
            selects.append(normalized)

    bind = write_session.get_bind()
    event.listen(bind, "before_cursor_execute", record)
    try:
        with freeze_time(AUG_27_MORNING + dt.timedelta(minutes=1)):
            report = dispatch_due_notifications(db_session_factory)
    finally:
        event.remove(bind, "before_cursor_execute", record)

    assert report.sent == 8
    assert len(selects) == 1, f"구독 조회가 {len(selects)}회 실행되었습니다"
