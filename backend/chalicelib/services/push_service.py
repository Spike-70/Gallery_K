"""웹 푸시 구독 (DB 문서 §4.3, API 문서 §8.4–§8.6).

한 회원이 여러 단말을 구독할 수 있다. **엔드포인트 원문은 응답에 담지 않는다** —
엔드포인트 URL은 그 단말에 푸시를 보낼 권한 그 자체이므로 불필요하게 왕복시키지 않는다.
클라이언트는 자신의 구독 endpoint를 SHA-256 해시해 대조한다(API 문서 §8.5).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from chalicelib.config.constants import PUSH_FAILURE_DEACTIVATE_THRESHOLD
from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.timeutil import format_rfc3339, now_utc
from chalicelib.db import query as q
from chalicelib.db.models import AppUser, PushSubscription
from chalicelib.db.models.enums import PushPlatform, PushStatus
from chalicelib.utils.text import sha256_hex


def serialize_subscription(row: PushSubscription) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "endpoint_hash": row.endpoint_hash,
        "platform": row.platform,
        "is_active": row.is_active,
        "created_at": format_rfc3339(row.created_at),
        "last_success_at": format_rfc3339(row.last_success_at),
    }


def detect_platform(user_agent: str | None) -> str:
    """미지정 시 UA로 추정한다 (API 문서 §8.4). 확신이 없으면 `unknown`이다."""
    agent = (user_agent or "").lower()
    if "iphone" in agent or "ipad" in agent or "ios" in agent:
        return PushPlatform.IOS
    if "android" in agent:
        return PushPlatform.ANDROID
    if any(token in agent for token in ("windows", "macintosh", "linux", "cros")):
        return PushPlatform.DESKTOP
    return PushPlatform.UNKNOWN


def subscribe(
    session: Session,
    user_id: uuid.UUID,
    *,
    endpoint: str,
    p256dh: str,
    auth: str,
    platform: str,
) -> tuple[dict[str, Any], bool]:
    """등록·갱신. 두 번째 값은 신규 여부(`201` vs `200`)다.

    같은 엔드포인트가 다른 회원으로 재등록되면 **소유자를 갱신한다** — 한 기기를 나눠 쓰는
    경우가 실제로 있고, 그때 이전 소유자에게 알림이 가면 안 된다.

    **부수효과** — `notify_enabled`가 false였다면 true로 함께 전환한다. 브라우저 권한을
    허용한 시점이 곧 알림을 켜겠다는 의사표시다.
    """
    _guard_subscription(endpoint=endpoint, p256dh=p256dh, auth=auth)
    endpoint_hash = sha256_hex(endpoint)
    now = now_utc()
    existing = q.fetch_one(session, PushSubscription, where={"endpoint_hash": endpoint_hash})

    if existing is None:
        row = q.insert(
            session,
            PushSubscription,
            {
                "user_id": user_id,
                "endpoint": endpoint,
                "endpoint_hash": endpoint_hash,
                "p256dh": p256dh,
                "auth": auth,
                "platform": platform,
                "is_active": True,
                "failure_count": 0,
            },
        )
        is_new = True
    else:
        q.update(
            session,
            PushSubscription,
            where={"id": existing.id},
            values={
                "user_id": user_id,
                "endpoint": endpoint,
                "p256dh": p256dh,
                "auth": auth,
                "platform": platform,
                "is_active": True,
                "failure_count": 0,
                "deactivated_at": None,
                "updated_at": now,
            },
        )
        session.expire(existing)
        refreshed = q.fetch_one(session, PushSubscription, where={"id": existing.id})
        assert refreshed is not None
        row = refreshed
        is_new = False

    q.update(
        session, AppUser, where={"id": user_id, "notify_enabled": False}, values={"notify_enabled": True}
    )
    return serialize_subscription(row), is_new


def _guard_subscription(*, endpoint: str, p256dh: str, auth: str) -> None:
    """브라우저가 준 구독 정보가 실제로 쓸 수 있는 모양인지 본다 (API 문서 §8.4).

    스키마 검증은 "값이 있는가"까지만 본다. 여기서 보는 것은 **푸시 서비스로 보낼 수
    있는 값인가**이고, 그 실패는 문서가 지정한 전용 코드로 답한다.
    """
    if not endpoint.startswith("https://"):
        raise AppError(ErrorCode.PUSH_SUBSCRIPTION_INVALID)
    if not p256dh.strip() or not auth.strip():
        raise AppError(ErrorCode.PUSH_SUBSCRIPTION_INVALID)


def list_subscriptions(session: Session, user_id: uuid.UUID) -> list[dict[str, Any]]:
    rows = q.fetch(session, PushSubscription, where={"user_id": user_id}, order_by=["-created_at"])
    return [serialize_subscription(row) for row in rows]


def active_subscriptions_for(
    session: Session, user_ids: Sequence[uuid.UUID | None]
) -> dict[uuid.UUID, list[PushSubscription]]:
    """여러 회원의 활성 구독을 **한 질의로** 모아 회원별로 나눈다.

    발송 배치가 알림마다 구독을 조회하면 그것이 곧 N+1이다(DB 문서 §7).
    """
    identifiers = [user_id for user_id in user_ids if user_id is not None]
    if not identifiers:
        return {}

    grouped: dict[uuid.UUID, list[PushSubscription]] = {}
    rows = q.fetch(
        session,
        PushSubscription,
        where={"user_id__in": identifiers, "is_active": True},
        order_by=["created_at"],
    )
    for row in rows:
        grouped.setdefault(row.user_id, []).append(row)
    return grouped


def owns_subscription(session: Session, user_id: uuid.UUID, subscription_id: uuid.UUID) -> bool:
    return q.exists(session, PushSubscription, where={"id": subscription_id, "user_id": user_id})


def unsubscribe(session: Session, user_id: uuid.UUID, subscription_id: uuid.UUID) -> None:
    """해당 단말 구독만 해제한다.

    `notify_enabled`는 건드리지 않는다 — 다른 단말에서는 계속 받을 수 있어야 한다.
    전면 해제는 `PATCH /me/settings`의 `notify_enabled=false`다(API 문서 §8.6).
    """
    affected = q.delete(session, PushSubscription, where={"id": subscription_id, "user_id": user_id})
    if affected == 0:
        raise AppError(ErrorCode.NOT_FOUND, details={"resource": "push_subscription"})


def push_status_of(*, subscription_count: int, has_active: bool) -> str:
    """`MemberItem.push_status` (API 문서 §3.8).

    구독이 없으면 `none`, 있는데 전부 실패 중이면 `inactive`. 이 판정이 두 곳에 있으면
    "iOS 안내가 필요한 회원"을 고르는 기준이 화면마다 달라진다.
    """
    if subscription_count == 0:
        return PushStatus.NONE
    return PushStatus.ACTIVE if has_active else PushStatus.INACTIVE


def register_failure(session: Session, subscription_id: uuid.UUID, *, permanent: bool) -> None:
    """푸시 404/410이면 즉시 비활성, 5xx는 연속 실패 누적 후 비활성 (DB 문서 §4.3)."""
    now = now_utc()
    if permanent:
        q.update(
            session,
            PushSubscription,
            where={"id": subscription_id},
            values={"is_active": False, "deactivated_at": now, "updated_at": now},
        )
        return

    q.update(
        session,
        PushSubscription,
        where={"id": subscription_id},
        values={"failure_count": PushSubscription.failure_count + 1, "updated_at": now},
    )
    q.update(
        session,
        PushSubscription,
        where={
            "id": subscription_id,
            "failure_count__gte": PUSH_FAILURE_DEACTIVATE_THRESHOLD,
        },
        values={"is_active": False, "deactivated_at": now},
    )


def register_success(session: Session, subscription_id: uuid.UUID) -> None:
    now = now_utc()
    q.update(
        session,
        PushSubscription,
        where={"id": subscription_id},
        values={"failure_count": 0, "last_success_at": now, "updated_at": now},
    )
