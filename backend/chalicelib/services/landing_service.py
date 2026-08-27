"""A 첫 화면 (API 문서 §6.1).

화면 진입당 왕복 1회가 원칙이므로(AP-3) 전시 제목·공지·가입 가능 여부·관리자 여부를
한 번에 준다.

**이 응답은 실패하지 않는다.** DB 장애 시에도 오늘 날짜와 가입 기본값만 채우고 나머지를
`null`로 반환한다 — 장애 시에도 A 첫 화면은 항상 뜬다(PRD §8.5, UX §3.1 "네트워크 오류:
오류 메시지를 띄우지 않는다").
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from chalicelib.core.logging import get_logger
from chalicelib.core.timeutil import date_label, format_date
from chalicelib.db.models.enums import UserRole
from chalicelib.services import exhibition_service, notice_service, setting_service
from chalicelib.services.setting_service import SettingKey

logger = get_logger("landing")


def build_landing(
    session_provider: Callable[[], Session],
    *,
    today: _dt.date,
    actor_id: Any,
    actor_role: str | None,
) -> dict[str, Any]:
    """세션을 **값이 아니라 함수로 받는다.**

    DB에 닿지 못하는 상황에서도 응답을 만들어야 하는데, 인자로 세션을 받으면 호출 시점에
    이미 실패한다. 요청 스코프 세션은 지연 생성이므로 여는 순간의 실패까지 여기서 잡힌다.
    세션의 수명은 그대로 미들웨어가 관리한다.
    """
    payload = _degraded(today, actor_id=actor_id, actor_role=actor_role)
    try:
        session = session_provider()
        exhibition = exhibition_service.find_current(session, today)
        payload["exhibition_title"] = exhibition.title if exhibition else None
        payload["has_exhibition"] = exhibition is not None
        payload["notice"] = notice_service.current_notice(session, today)
        payload["signup_open"] = setting_service.get_bool(session, SettingKey.SIGNUP_OPEN)
        payload["member_name"] = _member_name(session, actor_id)
    except Exception:
        logger.warning("첫 화면을 축소 응답으로 반환합니다", extra={"event": "landing.degraded"})
        return _degraded(today, actor_id=actor_id, actor_role=actor_role)
    return payload


def _degraded(today: _dt.date, *, actor_id: Any, actor_role: str | None) -> dict[str, Any]:
    return {
        "today": format_date(today),
        "today_label": date_label(today),
        "exhibition_title": None,
        "has_exhibition": False,
        "notice": None,
        # 기본값은 열림이다. 잠금 상태를 못 읽었다고 가입을 막으면 초대받은 사람이 막힌다.
        "signup_open": bool(setting_service.DEFAULTS[SettingKey.SIGNUP_OPEN]),
        "is_authenticated": actor_id is not None,
        "is_curator": actor_role == UserRole.CURATOR,
        "member_name": None,
    }


def _member_name(session: Session, actor_id: Any) -> str | None:
    if actor_id is None:
        return None
    from chalicelib.db import query as q
    from chalicelib.db.models import AppUser

    row = q.fetch_one(session, AppUser, where={"id": actor_id}, columns=["name"])
    return str(row["name"]) if row else None
