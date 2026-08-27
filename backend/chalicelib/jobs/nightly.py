"""야간 정리 루틴 (백엔드 문서 §11, DB 문서 §10).

하루 1회. 여섯 가지 일을 한다.

  1. 보존기간 초과 관람 로그 삭제 (180일)
  2. 알림 이력 삭제 (90일)
  3. 감사 이력 삭제 (365일)
  4. 만료된 시도 제한 행 삭제 (24시간)
  5. 비활성 푸시 구독 정리 (30일)
  6. 미참조 S3 오브젝트 회수 (7일) + 연장 지속 시 큐레이터 알림

**멱등하다.** 두 번 돌아도 결과가 같고, 처리 0건도 로그를 남긴다.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy.orm import Session

from chalicelib.core.logging import get_logger, log_event
from chalicelib.core.timeutil import kst_today, now_utc
from chalicelib.db import query as q
from chalicelib.db.models import (
    Artwork,
    ArtworkViewLog,
    AuditLog,
    AuthThrottle,
    NotificationLog,
    PushSubscription,
    ViewLog,
)
from chalicelib.services import exhibition_service, notification_service, setting_service
from chalicelib.services.setting_service import SettingKey

logger = get_logger("job.nightly")

#: DB 문서 §10의 보존 기간. `log_retention_days`만 운영 중 조정 가능하다.
NOTIFICATION_RETENTION_DAYS = 90
AUDIT_RETENTION_DAYS = 365
THROTTLE_RETENTION_HOURS = 24
PUSH_INACTIVE_RETENTION_DAYS = 30
#: 미참조 오브젝트를 바로 지우지 않는 유예. 삭제를 되돌리고 싶은 순간이 실제로 있다.
ORPHAN_OBJECT_GRACE_DAYS = 7


@dataclass(frozen=True, slots=True)
class MaintenanceReport:
    view_logs_deleted: int = 0
    artwork_view_logs_deleted: int = 0
    notifications_deleted: int = 0
    audit_logs_deleted: int = 0
    throttles_deleted: int = 0
    subscriptions_deleted: int = 0
    objects_reclaimed: int = 0
    carryover_alerts_queued: int = 0


def run_nightly_maintenance(session_factory: Any | None = None) -> MaintenanceReport:
    from chalicelib.db import engine as engine_module

    factory = session_factory or engine_module.open_session
    session: Session = factory()
    now = now_utc()
    today = kst_today()

    try:
        retention_days = setting_service.get_int(session, SettingKey.LOG_RETENTION_DAYS)
        cutoff_viewed_on = today - _dt.timedelta(days=retention_days)

        report = MaintenanceReport(
            view_logs_deleted=q.delete(session, ViewLog, where={"viewed_on__lt": cutoff_viewed_on}),
            artwork_view_logs_deleted=q.delete(
                session, ArtworkViewLog, where={"first_viewed_on__lt": cutoff_viewed_on}
            ),
            notifications_deleted=q.delete(
                session,
                NotificationLog,
                where={"created_at__lt": now - _dt.timedelta(days=NOTIFICATION_RETENTION_DAYS)},
            ),
            audit_logs_deleted=q.delete(
                session,
                AuditLog,
                where={"created_at__lt": now - _dt.timedelta(days=AUDIT_RETENTION_DAYS)},
            ),
            throttles_deleted=_prune_throttles(session, now),
            subscriptions_deleted=_prune_subscriptions(session, now),
            objects_reclaimed=_reclaim_objects(session, now),
            carryover_alerts_queued=_alert_on_carryover(session, today),
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    log_event(logger, "job.nightly.finished", **asdict(report))
    return report


def _prune_throttles(session: Session, now: _dt.datetime) -> int:
    """잠금이 풀렸고 24시간 이상 조용한 행만 지운다 — 살아 있는 잠금은 건드리지 않는다."""
    cutoff = now - _dt.timedelta(hours=THROTTLE_RETENTION_HOURS)
    return q.delete(
        session,
        AuthThrottle,
        where=q.Q(last_failed_at__lt=cutoff) & (q.Q(locked_until=None) | q.Q(locked_until__lt=now)),
    )


def _prune_subscriptions(session: Session, now: _dt.datetime) -> int:
    """비활성 구독은 개인정보성 자원이므로 오래 들고 있지 않는다 (DB 문서 §10)."""
    cutoff = now - _dt.timedelta(days=PUSH_INACTIVE_RETENTION_DAYS)
    return q.delete(
        session,
        PushSubscription,
        where={"is_active": False, "deactivated_at__lt": cutoff},
    )


def _reclaim_objects(session: Session, now: _dt.datetime) -> int:
    """미참조 S3 오브젝트 회수.

    **살아 있는 키를 먼저 모으고 그 밖의 것만 지운다.** 반대로 하면 방금 업로드된
    오브젝트가 회수 대상이 된다.
    """
    from chalicelib.config.constants import MEDIA_ARTWORK_PREFIX, MEDIA_UPLOAD_PREFIX
    from chalicelib.integrations import storage

    # 살아 있는 키만 필요하다. 그림 전체를 ORM 객체로 적재하면 하루 한 번의 정리가
    # 행 수에 비례해 무거워진다.
    referenced: set[str] = set()
    for row in q.fetch(
        session,
        Artwork,
        columns=[
            "image_origin_key",
            "image_display_key",
            "image_thumb_key",
            "image_pending_key",
        ],
    ):
        referenced.update(key for key in row.values() if key)

    cutoff = now - _dt.timedelta(days=ORPHAN_OBJECT_GRACE_DAYS)
    orphans: list[str] = []
    try:
        candidates = storage.list_object_keys(f"{MEDIA_ARTWORK_PREFIX}/") + storage.list_object_keys(
            f"{MEDIA_UPLOAD_PREFIX}/"
        )
    except Exception as exc:
        log_event(logger, "job.nightly.storage_unavailable", message=str(exc))
        return 0

    for key in candidates:
        if key in referenced:
            continue
        if not _is_older_than(key, cutoff):
            continue
        orphans.append(key)

    return storage.delete_objects(orphans) if orphans else 0


def _is_older_than(object_key: str, cutoff: _dt.datetime) -> bool:
    """키에 박힌 날짜로 유예 기간을 판정한다.

    오브젝트 메타데이터를 하나씩 조회하면 그 자체가 N+1이므로, 키 경로의 날짜를 쓴다.
    날짜를 읽을 수 없으면 **지우지 않는다** — 회수는 되돌릴 수 없다.
    """
    parts = object_key.split("/")
    if len(parts) < 2:
        return False
    parsed = _parse_date(parts[1])
    return parsed is not None and parsed < cutoff.date()


def _parse_date(value: str) -> _dt.date | None:
    from chalicelib.core.timeutil import parse_date

    return parse_date(value)


def _alert_on_carryover(session: Session, today: _dt.date) -> int:
    """연장이 임계일 이상 이어지면 큐레이터에게 1회 알린다 (PRD §6.12).

    매일 밤 재촉하지 않는 이유는 스킵이 정상 동작이기 때문이다 — 하루 걸렀다고 알림을
    보내면 그 알림 자체가 부담이 된다.
    """
    threshold = setting_service.get_int(session, SettingKey.CARRYOVER_ALERT_DAYS)
    # 현재 걸린 전시를 한 번만 찾는다 — 연장 일수도 그 전시에서 나온다.
    current = exhibition_service.find_current(session, today)
    if current is None:
        return 0
    carried = (today - current.exhibition_date).days
    if carried < threshold:
        return 0
    queued = notification_service.queue_curator_carryover(
        session,
        exhibition_date=current.exhibition_date,
        carried_days=carried,
        today=today,
    )
    return 1 if queued else 0
