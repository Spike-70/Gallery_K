"""발행 규칙 (PRD §4.3·부록 B, DB 문서 §6, 백엔드 문서 §9).

**발행 전환은 이 파일의 함수 하나에서만 일어난다.** 제목 저장·그림 저장·삭제·순서 변경
등 모든 변경 경로가 마지막에 `apply(...)`를 호출한다. 전환 지점이 둘이 되는 순간
"어떤 경로로 저장했느냐"에 따라 발행 여부가 갈리기 시작한다.

불변식
  ① `is_published`는 단조 증가한다 — 어떤 수정으로도 false로 되돌리지 않는다
  ② 발행 전환은 저장 트랜잭션 안에서만 일어나고 동시에 알림 행이 등록된다
  ③ 미래 날짜 발행본은 존재할 수 있으며 관람자 질의가 날짜로 걸러낸다
  ④ 과거 날짜 신규 발행(백필)은 여기서 거부한다
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Any

from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import Session

from chalicelib.config.constants import ARTWORK_COUNT
from chalicelib.core.logging import get_logger, log_event
from chalicelib.core.timeutil import now_utc
from chalicelib.db import query as q
from chalicelib.db.models import Artwork, Exhibition
from chalicelib.services import notification_service

logger = get_logger("publishing")

#: `publish_blockers` 값 (API 문서 §9.3)
MISSING_TITLE = "missing_title"
MISSING_THEME = "missing_theme"


@dataclass(frozen=True, slots=True)
class PublishState:
    can_publish: bool
    blockers: list[str]
    is_published: bool
    published_now: bool


def recount(session: Session, exhibition_id: Any) -> tuple[int, int]:
    """파생 카운터를 그림 변경과 **같은 트랜잭션**에서 재계산한다 (DB 문서 §4.4).

    `is_complete`는 DB 생성 컬럼이므로 완성 판정은 여기서 다시 하지 않는다.
    """
    from sqlalchemy import case, func

    # 생성 컬럼은 매퍼 속성이 아니라 테이블 컬럼으로 참조한다.
    is_complete = sa_inspect(Artwork).c.is_complete
    rows = q.aggregate(
        session,
        Artwork,
        values={
            "total": func.count(),
            "complete": func.count(case((is_complete, 1))),
        },
        where={"exhibition_id": exhibition_id},
    )
    total = int(rows[0]["total"]) if rows else 0
    complete = int(rows[0]["complete"]) if rows else 0
    q.update(
        session,
        Exhibition,
        where={"id": exhibition_id},
        values={"artwork_count": total, "complete_artwork_count": complete},
        bump_version=False,
    )
    return total, complete


def blockers_for(exhibition: Exhibition) -> list[str]:
    """발행을 막고 있는 것들. 화면이 그대로 목록으로 보여 준다 (API 문서 §9.3)."""
    found: list[str] = []
    if not (exhibition.title or "").strip():
        found.append(MISSING_TITLE)
    if not (exhibition.theme or "").strip():
        found.append(MISSING_THEME)
    # 어느 자리가 비었는지까지 알려 준다 — 12점 중 하나를 찾는 일을 사람에게 시키지 않는다.
    return found


def slot_blockers(session: Session, exhibition_id: Any) -> list[str]:
    """완성되지 않은 자리 번호. 빈 자리와 미완성 자리를 **한 질의로** 함께 판정한다.

    어느 자리가 비었는지까지 알려 준다 — 12점 중 하나를 찾는 일을 사람에게 시키지 않는다.
    """
    rows = q.fetch(
        session,
        Artwork,
        where={"exhibition_id": exhibition_id},
        columns=["position", "is_complete"],
    )
    complete = {row["position"] for row in rows if row["is_complete"]}
    positions = [position for position in range(1, ARTWORK_COUNT + 1) if position not in complete]
    return [f"incomplete_artwork:{position}" for position in positions]


def apply(
    session: Session,
    exhibition: Exhibition,
    *,
    today: _dt.date,
    actor_id: Any = None,
) -> PublishState:
    """저장 경로의 마지막에 호출한다. 조건이 처음 충족되면 여기서 발행된다.

    발행 조건 — 제목 · 테마 · 완성 그림 12점. **서비스 계층에서만 판정하며 DB 트리거를
    쓰지 않는다**(DB 문서 §4.4): 발행은 알림을 유발하는 도메인 이벤트이기 때문이다.
    """
    total, complete = recount(session, exhibition.id)
    session.expire(exhibition)
    session.refresh(exhibition)

    found = blockers_for(exhibition)
    if complete < ARTWORK_COUNT:
        found.extend(slot_blockers(session, exhibition.id))

    conditions_met = not found
    already_published = exhibition.is_published

    # ① 단조 증가 — 발행된 전시는 조건이 깨져도 발행 상태를 유지한다.
    if already_published:
        return PublishState(
            can_publish=conditions_met,
            blockers=found,
            is_published=True,
            published_now=False,
        )

    # ④ 백필 금지 — 과거 날짜에 새 전시가 생기지 않는다. 조건이 충족돼도 발행하지 않는다.
    if conditions_met and exhibition.exhibition_date < today:
        return PublishState(
            can_publish=False,
            blockers=[*found, "backfill_forbidden"],
            is_published=False,
            published_now=False,
        )

    if not conditions_met:
        return PublishState(can_publish=False, blockers=found, is_published=False, published_now=False)

    published_at = now_utc()
    q.update(
        session,
        Exhibition,
        where={"id": exhibition.id, "is_published": False},
        values={"is_published": True, "published_at": published_at},
        bump_version=False,
    )
    session.expire(exhibition)
    session.refresh(exhibition)

    # ② 같은 트랜잭션에서 알림 행을 등록한다.
    queued = notification_service.queue_morning_notifications(
        session,
        exhibition_id=exhibition.id,
        exhibition_date=exhibition.exhibition_date,
        exhibition_title=exhibition.title or "",
        published_at=published_at,
    )
    log_event(
        logger,
        "exhibition.published",
        exhibition_date=exhibition.exhibition_date.isoformat(),
        artwork_count=total,
        notifications_queued=queued,
    )
    return PublishState(can_publish=True, blockers=[], is_published=True, published_now=True)
