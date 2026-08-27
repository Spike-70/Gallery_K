"""회원 (DB 문서 §4.1·§10, API 문서 §3.6·§8).

수집 항목은 전화번호·비밀번호·이름 **셋뿐이다.** 최소 수집이 곧 최소 리스크다(PRD §8.4).
전체 전화번호는 관리자 응답에서만 나가고, 관람자 응답에는 마스킹된 형태만 나간다.
"""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any

from sqlalchemy.orm import Session

from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.timeutil import format_rfc3339, format_time_of_day, now_utc
from chalicelib.db import query as q
from chalicelib.db.models import (
    AppUser,
    ArtworkViewLog,
    AuthThrottle,
    NotificationLog,
    PushSubscription,
    ViewLog,
)
from chalicelib.db.models.enums import UserRole
from chalicelib.utils.text import mask_phone


def serialize_session_user(user: AppUser) -> dict[str, Any]:
    """`SessionUser` (API 문서 §3.6).

    **전체 전화번호는 어떤 관람자 API에서도 반환하지 않는다.**
    """
    return {
        "id": str(user.id),
        "name": user.name,
        "phone_masked": mask_phone(user.phone),
        "role": user.role,
        "font_scale": user.font_scale,
        "notify_enabled": user.notify_enabled,
        "notify_at": format_time_of_day(user.notify_at),
        "must_change_password": user.must_change_password,
        "created_at": format_rfc3339(user.created_at),
    }


def get_user(session: Session, user_id: uuid.UUID) -> AppUser:
    user = q.fetch_one(session, AppUser, where={"id": user_id})
    if user is None:
        raise AppError(ErrorCode.MEMBER_NOT_FOUND)
    return user


def update_settings(
    session: Session,
    user_id: uuid.UUID,
    *,
    notify_enabled: bool | None,
    notify_at: _dt.time | None,
    font_scale: str | None,
) -> dict[str, Any]:
    """부분 갱신 — **보낸 필드만** 반영한다 (API 문서 §8.2).

    알림을 꺼도 `notify_at`은 보존한다. 다시 켤 때 쓰던 시각이 그대로 있어야 한다.
    """
    values: dict[str, Any] = {}
    if notify_enabled is not None:
        values["notify_enabled"] = notify_enabled
    if notify_at is not None:
        values["notify_at"] = notify_at
    if font_scale is not None:
        values["font_scale"] = font_scale

    q.update(session, AppUser, where={"id": user_id}, values=values)
    user = get_user(session, user_id)
    session.refresh(user)
    return serialize_session_user(user)


def withdraw(session: Session, user_id: uuid.UUID) -> None:
    """탈퇴 트랜잭션 (DB 문서 §10).

    열람 로그를 익명화하고, 구독·알림·시도 제한 행을 삭제하고, 회원 행을 삭제한다.
    감사 로그에는 `member.withdraw` 1건을 남기되 **탈퇴자를 식별할 값을 어디에도 남기지
    않는다** — `@audited`가 액션만 기록하고, 이 함수는 대상 정보를 넘기지 않는다.

    큐레이터는 탈퇴할 수 없다. 큐레이터 없는 서비스는 동작 불가 상태다.
    """
    user = get_user(session, user_id)
    if user.role == UserRole.CURATOR:
        raise AppError(ErrorCode.MEMBER_CURATOR_IMMUTABLE)

    now = now_utc()
    # 집계 형태는 남기고 식별만 끊는다. 익명화된 로그는 전 지표에서 제외된다.
    q.update(
        session,
        ViewLog,
        where={"user_id": user_id},
        values={"user_id": None, "is_anonymized": True, "updated_at": now},
    )
    q.update(
        session,
        ArtworkViewLog,
        where={"user_id": user_id},
        values={"user_id": None, "is_anonymized": True, "updated_at": now},
    )

    # 개인정보성 자원은 즉시 파기한다.
    q.delete(session, PushSubscription, where={"user_id": user_id})
    q.delete(session, NotificationLog, where={"user_id": user_id})
    q.delete(session, AuthThrottle, where={"throttle_key__startswith": f"login:{user.phone}"})

    q.delete(session, AppUser, where={"id": user_id})


# ── 관리자 회원 관리 (API 문서 §9.13–§9.16) ────────────────────────────────


def serialize_member_item(row: dict[str, Any]) -> dict[str, Any]:
    """`MemberItem` (API 문서 §3.8).

    **관리자 응답에서만 전체 번호를 반환한다** — B-3은 전화 한 통으로 돕는 화면이다.
    """
    from chalicelib.services import push_service

    return {
        "id": str(row["id"]),
        "name": row["name"],
        "phone": row["phone"],
        "role": row["role"],
        "created_at": format_rfc3339(row["created_at"]),
        "created_via": row["created_via"],
        "is_blocked": row["is_blocked"],
        "blocked_at": format_rfc3339(row["blocked_at"]),
        "notify_enabled": row["notify_enabled"],
        "notify_at": format_time_of_day(row["notify_at"]),
        "push_status": push_service.push_status_of(
            subscription_count=row["subscription_count"],
            has_active=row["has_active_subscription"],
        ),
        "push_platforms": sorted(platform for platform in (row["platforms"] or []) if platform),
        "last_login_at": format_rfc3339(row["last_login_at"]),
        "last_viewed_on": row["last_viewed_on"].isoformat() if row["last_viewed_on"] else None,
    }


def list_members(
    session: Session,
    *,
    query: str | None,
    status: str,
    notify: str,
    sort: str,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    from chalicelib.db.queries import member_list

    filters = member_list.build_filters(query=query, status=status, notify=notify)
    total = member_list.count_members(session, filters=filters)
    rows = member_list.fetch_members(session, filters=filters, sort=sort, limit=limit, offset=offset)
    return [serialize_member_item(row) for row in rows], total


def member_item(session: Session, user_id: uuid.UUID) -> dict[str, Any]:
    """단건 응답도 목록과 **같은 질의**로 만든다 — 두 경로가 갈라지지 않게 한다."""
    from chalicelib.db.queries import member_list

    user = get_user(session, user_id)
    filters = member_list.build_filters(query=user.phone, status="all", notify="all")
    rows = member_list.fetch_members(session, filters=filters, sort="-created_at", limit=1, offset=0)
    if not rows:
        raise AppError(ErrorCode.MEMBER_NOT_FOUND)
    return serialize_member_item(rows[0])


def _guard_viewer(user: AppUser) -> None:
    if user.role == UserRole.CURATOR:
        raise AppError(ErrorCode.MEMBER_CURATOR_IMMUTABLE)


def set_blocked(
    session: Session, user_id: uuid.UUID, *, blocked: bool, reason: str | None = None
) -> dict[str, Any]:
    """차단은 **로그인 시점에만** 작동한다. 기존 세션을 끊지 않는다 (PRD §6.4).

    이미 같은 상태면 그대로 성공이다(멱등).
    """
    user = get_user(session, user_id)
    _guard_viewer(user)
    now = now_utc()
    q.update(
        session,
        AppUser,
        where={"id": user_id},
        values={
            "is_blocked": blocked,
            "blocked_at": now if blocked else None,
            "blocked_reason": reason if blocked else None,
            "updated_at": now,
        },
    )
    return member_item(session, user_id)


def reset_password(session: Session, user_id: uuid.UUID, *, new_password: str) -> dict[str, Any]:
    """`must_change_password=true`, `token_version+1`로 모든 세션을 무효화한다.

    큐레이터가 전화로 새 비밀번호를 전달하는 운영 흐름을 전제한다(PRD §6.14).
    """
    from chalicelib.config.constants import PASSWORD_MIN_LENGTH
    from chalicelib.core.security import hash_password
    from chalicelib.services import session_service

    user = get_user(session, user_id)
    _guard_viewer(user)
    if len(new_password) < PASSWORD_MIN_LENGTH:
        raise AppError(ErrorCode.PASSWORD_POLICY_VIOLATION, details={"min_length": PASSWORD_MIN_LENGTH})

    q.update(
        session,
        AppUser,
        where={"id": user_id},
        values={
            "password_hash": hash_password(new_password),
            "must_change_password": True,
            "updated_at": now_utc(),
            **session_service.revocation_values(),
        },
    )
    return member_item(session, user_id)
