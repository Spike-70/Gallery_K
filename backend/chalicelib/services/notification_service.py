"""알림 큐 (DB 문서 §4.10, PRD §6.12, 백엔드 문서 §11).

이 모듈은 **큐 생성**과 **스킵 판정**을 맡는다. 실제 발송은 스케줄 루틴이 한다.

`dedupe_key` UNIQUE가 "하루 1회"와 "연장 기간당 1회"를 DB 수준에서 보장하므로, 중복
기동과 재시도가 무해하다. 보내지 않기로 한 경우에도 `skipped` 행을 남긴다 — 보내지 않은
이유가 남아야 문의에 답할 수 있다.
"""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any

from sqlalchemy.orm import Session

from chalicelib.config.constants import (
    NOTIFICATION_MAX_ATTEMPTS,
    PUSH_TAG_CURATOR,
    PUSH_TAG_MORNING,
)
from chalicelib.core.ids import new_id
from chalicelib.core.timeutil import kst_datetime, now_utc, to_kst
from chalicelib.db import query as q
from chalicelib.db.models import AppUser, NotificationLog
from chalicelib.db.models.enums import (
    NotificationKind,
    NotificationSkipReason,
    NotificationStatus,
)
from chalicelib.services import setting_service
from chalicelib.services.setting_service import SettingKey


def morning_dedupe_key(user_id: uuid.UUID, exhibition_date: _dt.date) -> str:
    return f"morning:{user_id}:{exhibition_date.isoformat()}"


def curator_signup_dedupe_key(new_user_id: uuid.UUID) -> str:
    return f"signup:{new_user_id}"


def curator_carryover_dedupe_key(exhibition_date: _dt.date) -> str:
    """연장 **기간당** 1회. 키가 연장 시작 전시의 발행일이므로 3일째에도 같은 키가 된다."""
    return f"carryover:{exhibition_date.isoformat()}"


def _notification_row(
    *,
    user_id: uuid.UUID | None,
    kind: str,
    dedupe_key: str,
    scheduled_for: _dt.datetime,
    now: _dt.datetime,
    exhibition_id: uuid.UUID | None = None,
    status: str = NotificationStatus.PENDING,
    skip_reason: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """알림 이력 한 행. 단건 예약과 벌크 예약이 같은 모양을 쓰게 하는 것이 목적이다."""
    return {
        "id": new_id(),
        "user_id": user_id,
        "kind": kind,
        "dedupe_key": dedupe_key,
        "exhibition_id": exhibition_id,
        "status": status,
        "skip_reason": skip_reason,
        "scheduled_for": scheduled_for,
        "attempt_count": 0,
        "payload": payload,
        "created_at": now,
        "updated_at": now,
    }


def _enqueue(
    session: Session,
    *,
    user_id: uuid.UUID | None,
    kind: str,
    dedupe_key: str,
    scheduled_for: _dt.datetime,
    exhibition_id: uuid.UUID | None = None,
    status: str = NotificationStatus.PENDING,
    skip_reason: str | None = None,
    payload: dict[str, Any] | None = None,
) -> bool:
    """새로 예약했으면 True. 이미 있으면 False다.

    `ON CONFLICT DO NOTHING`은 충돌 시 아무 행도 돌려주지 않으므로, `RETURNING`의
    유무가 곧 "이번에 새로 만들었는가"의 답이 된다 — 별도 조회를 두지 않는다.
    """
    inserted = q.upsert(
        session,
        NotificationLog,
        values=_notification_row(
            user_id=user_id,
            kind=kind,
            dedupe_key=dedupe_key,
            scheduled_for=scheduled_for,
            now=now_utc(),
            exhibition_id=exhibition_id,
            status=status,
            skip_reason=skip_reason,
            payload=payload,
        ),
        # 이미 있으면 그대로 둔다 — 같은 알림을 두 번 예약하지 않는다.
        conflict=["dedupe_key"],
        returning=["id"],
    )
    return inserted is not None


def queue_curator_signup(session: Session, *, new_user_id: uuid.UUID, new_user_name: str) -> None:
    """누군가 가입하면 큐레이터에게 알린다 — 모르는 사람이면 즉시 알 수 있다(PRD §6.4)."""
    curator = q.fetch_one(session, AppUser, where={"role": "curator"}, columns=["id", "notify_enabled"])
    if curator is None:
        return

    now = now_utc()
    skip_reason = None if curator["notify_enabled"] else NotificationSkipReason.NOTIFY_DISABLED
    _enqueue(
        session,
        user_id=curator["id"],
        kind=NotificationKind.CURATOR_SIGNUP,
        dedupe_key=curator_signup_dedupe_key(new_user_id),
        scheduled_for=now,
        status=NotificationStatus.PENDING if skip_reason is None else NotificationStatus.SKIPPED,
        skip_reason=skip_reason,
        # 이름만 담는다. 전화번호는 알림 본문에도 이력에도 넣지 않는다.
        payload={"member_name": new_user_name},
    )


def queue_morning_notifications(
    session: Session,
    *,
    exhibition_id: uuid.UUID,
    exhibition_date: _dt.date,
    exhibition_title: str,
    published_at: _dt.datetime,
) -> int:
    """발행 트랜잭션 안에서 대상 회원 전원의 알림을 예약한다 (API 문서 §11.3).

    사용자의 알림 시각이 이미 지났으면 즉시 발송으로 예약하되, 컷오프(기본 21시)를
    넘겼으면 발송하지 않고 `skipped(cutoff_passed)`로 종료한다. 발송 종류가 둘로 나뉘는
    이유는 도달률을 사후에 분리 관측하기 위해서다(교차검토 X-16).

    **보내지 않기로 한 회원에게도 행을 남긴다** (DB 문서 §4.10) — 알림을 꺼 두었거나
    차단된 회원이 "왜 못 받았나"를 물었을 때 답할 근거가 그 행이다.

    행마다 왕복하지 않고 **한 문장으로 넣는다.** 회원 수에 비례해 발행 요청이 느려지면
    마지막 그림을 저장하는 순간이 가장 오래 걸리는 순간이 된다.
    """
    cutoff_hour = setting_service.get_int(session, SettingKey.NOTIFY_CUTOFF_HOUR)
    published_kst = to_kst(published_at)
    past_cutoff = published_kst.hour >= cutoff_hour
    now = now_utc()

    targets = q.fetch(
        session,
        AppUser,
        columns=["id", "notify_at", "notify_enabled", "is_blocked"],
    )

    rows: list[dict[str, Any]] = []
    queued = 0
    for target in targets:
        scheduled = kst_datetime(exhibition_date, target["notify_at"])
        is_late = scheduled <= published_at
        kind = NotificationKind.LATE_PUBLISH if is_late else NotificationKind.MORNING_EXHIBITION
        if is_late:
            scheduled = published_at

        skip_reason = _morning_skip_reason(target, is_late=is_late, past_cutoff=past_cutoff)
        status = NotificationStatus.PENDING if skip_reason is None else NotificationStatus.SKIPPED
        queued += skip_reason is None

        rows.append(
            _notification_row(
                user_id=target["id"],
                kind=kind,
                dedupe_key=morning_dedupe_key(target["id"], exhibition_date),
                exhibition_id=exhibition_id,
                scheduled_for=scheduled,
                status=status,
                skip_reason=skip_reason,
                payload={"title": exhibition_title, "exhibition_date": exhibition_date.isoformat()},
                now=now,
            )
        )

    if rows:
        q.upsert(session, NotificationLog, values=rows, conflict=["dedupe_key"])
    return queued


def _morning_skip_reason(target: dict[str, Any], *, is_late: bool, past_cutoff: bool) -> str | None:
    """보내지 않을 이유가 있으면 그 사유를, 없으면 None을 준다."""
    if target["is_blocked"]:
        return NotificationSkipReason.USER_BLOCKED
    if not target["notify_enabled"]:
        return NotificationSkipReason.NOTIFY_DISABLED
    if is_late and past_cutoff:
        # 아침 알림은 시의성이 전부다. 컷오프를 넘긴 발행분은 큐에 넣지 않는다.
        return NotificationSkipReason.CUTOFF_PASSED
    return None


# ── 발송 (백엔드 문서 §11) ─────────────────────────────────────────────────


def due_notifications(session: Session, *, now: _dt.datetime, limit: int) -> list[Any]:
    """발송 예정 시각이 지난 대기 행. 부분 인덱스 `ix_notification_log_due`를 탄다."""
    return q.fetch(
        session,
        NotificationLog,
        where={"status": NotificationStatus.PENDING, "scheduled_for__lte": now},
        order_by=["scheduled_for"],
        limit=limit,
    )


def claim(session: Session, notification_id: uuid.UUID) -> bool:
    """조건부 상태 갱신으로 한 행을 잡는다.

    **중복 기동이 무해한 이유**의 절반이 여기 있다(나머지 절반은 `dedupe_key` 유니크다).
    두 인스턴스가 같은 행을 집어도 UPDATE가 성공하는 쪽은 하나뿐이다.
    """
    affected = q.update(
        session,
        NotificationLog,
        where={"id": notification_id, "status": NotificationStatus.PENDING},
        values={
            "attempt_count": NotificationLog.attempt_count + 1,
            "updated_at": now_utc(),
        },
    )
    return affected == 1


def mark_sent(session: Session, notification_id: uuid.UUID) -> None:
    now = now_utc()
    q.update(
        session,
        NotificationLog,
        where={"id": notification_id},
        values={"status": NotificationStatus.SENT, "sent_at": now, "updated_at": now},
    )


def mark_skipped(session: Session, notification_id: uuid.UUID, *, reason: str) -> None:
    """보내지 않기로 한 경우에도 행을 남긴다 — 보내지 않은 이유가 남아야 문의에 답할 수 있다."""
    q.update(
        session,
        NotificationLog,
        where={"id": notification_id},
        values={
            "status": NotificationStatus.SKIPPED,
            "skip_reason": reason,
            "updated_at": now_utc(),
        },
    )


def mark_failed(session: Session, notification_id: uuid.UUID, *, error: str) -> None:
    q.update(
        session,
        NotificationLog,
        where={"id": notification_id},
        values={
            "status": NotificationStatus.FAILED,
            "last_error": error[:300],
            "updated_at": now_utc(),
        },
    )


def release(session: Session, notification_id: uuid.UUID, *, error: str) -> None:
    """재시도 여지를 남기고 되돌린다. 상한을 넘기면 실패로 종료한다."""
    row = q.fetch_one(session, NotificationLog, where={"id": notification_id}, columns=["attempt_count"])
    attempts = int(row["attempt_count"]) if row else NOTIFICATION_MAX_ATTEMPTS
    if attempts >= NOTIFICATION_MAX_ATTEMPTS:
        mark_failed(session, notification_id, error=error)
        return
    q.update(
        session,
        NotificationLog,
        where={"id": notification_id},
        values={"last_error": error[:300], "updated_at": now_utc()},
    )


def is_past_cutoff(session: Session, notification: Any, *, now: _dt.datetime) -> bool:
    """아침 알림은 시의성이 전부다. 당일 컷오프를 넘기면 재시도하지 않는다 (DB 문서 §6)."""
    if notification.kind not in {
        NotificationKind.MORNING_EXHIBITION,
        NotificationKind.LATE_PUBLISH,
    }:
        return False
    cutoff_hour = setting_service.get_int(session, SettingKey.NOTIFY_CUTOFF_HOUR)
    scheduled_kst = to_kst(notification.scheduled_for)
    now_kst_value = to_kst(now)
    if now_kst_value.date() > scheduled_kst.date():
        return True
    return now_kst_value.hour >= cutoff_hour


def notification_content(session: Session, notification: Any) -> tuple[str, str, str]:
    """(제목, 본문, 태그). 문구는 전시 제목까지만 담는다 — 12점이 무엇인지는 알려주지 않는다."""
    payload = notification.payload or {}
    if notification.kind == NotificationKind.CURATOR_SIGNUP:
        return (
            "새 회원이 가입했습니다",
            payload.get("member_name", "새 회원"),
            PUSH_TAG_CURATOR,
        )
    if notification.kind == NotificationKind.CURATOR_CARRYOVER:
        return (
            "전시가 연장되고 있습니다",
            payload.get("message", "새 전시를 준비해 주세요."),
            PUSH_TAG_CURATOR,
        )
    return ("오늘의 전시", payload.get("title", ""), PUSH_TAG_MORNING)


def queue_curator_carryover(
    session: Session, *, exhibition_date: _dt.date, carried_days: int, today: _dt.date
) -> bool:
    """연장이 2일 연속되면 큐레이터에게 **1회만** 보낸다 (PRD §6.12).

    3일째부터는 다시 보내지 않는다 — `dedupe_key`가 연장 시작 전시의 발행일이라 같은
    연장 기간 안에서는 키가 변하지 않는다.

    **휴관 공지 기간에는 보내지 않는다.** 쉬겠다고 미리 적어둔 사람에게 쉬고 있다고
    알리는 것은 의미가 없다.
    """
    from chalicelib.services import notice_service

    curator = q.fetch_one(session, AppUser, where={"role": "curator"}, columns=["id", "notify_enabled"])
    if curator is None:
        return False

    skip_reason: str | None = None
    if notice_service.is_notice_period(session, today):
        skip_reason = NotificationSkipReason.NOTICE_PERIOD
    elif not curator["notify_enabled"]:
        skip_reason = NotificationSkipReason.NOTIFY_DISABLED

    queued = _enqueue(
        session,
        user_id=curator["id"],
        kind=NotificationKind.CURATOR_CARRYOVER,
        dedupe_key=curator_carryover_dedupe_key(exhibition_date),
        scheduled_for=now_utc(),
        status=NotificationStatus.PENDING if skip_reason is None else NotificationStatus.SKIPPED,
        skip_reason=skip_reason,
        payload={
            "message": f"{carried_days}일째 같은 전시가 걸려 있습니다.",
            "exhibition_date": exhibition_date.isoformat(),
        },
    )
    return queued and skip_reason is None
