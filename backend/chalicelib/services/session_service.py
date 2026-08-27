"""세션 (API 문서 §2.7, 백엔드 문서 §13).

세션 토큰은 서명 쿠키로만 오간다. 이 서비스는 **토큰이 가리키는 회원이 지금도 유효한가**를
판정한다 — 무효화 카운터(`token_version`) 대조가 그 전부다.

차단은 여기서 보지 않는다. 차단은 로그인 시점에만 작동하며 기존 세션을 끊지 않는다
(PRD §6.4). 즉시 차단이 필요해지면 `token_version` 증가로 열린다.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from chalicelib.core.context import ActorSnapshot
from chalicelib.db import query as q
from chalicelib.db.models import AppUser


def load_actor(session: Session, user_id: uuid.UUID) -> ActorSnapshot | None:
    """인증 미들웨어가 매 요청 부른다. 필요한 세 컬럼만 읽는다."""
    row = q.fetch_one(
        session,
        AppUser,
        where={"id": user_id},
        columns=["id", "role", "token_version"],
    )
    if row is None:
        return None
    return ActorSnapshot(id=row["id"], role=row["role"], token_version=row["token_version"])


def session_ttl_seconds(session: Session) -> int:
    """세션 쿠키·토큰의 유효 기간. 운영 설정이 있으면 그것을 따른다 (DB 문서 §4.9)."""
    from chalicelib.services import setting_service
    from chalicelib.services.setting_service import SettingKey

    days = setting_service.get_int(session, SettingKey.SESSION_TTL_DAYS)
    return max(1, days) * 86_400


def revocation_values() -> dict[str, Any]:
    """세션을 끊는 갱신 값. **무효화는 이 한 곳에서만 표현한다.**

    `token_version`을 올리면 기존 토큰의 `tv`와 어긋나 즉시 거부된다(API 문서 §2.7).
    비밀번호 변경(§6.7)과 초기화(§9.16)가 같은 값을 쓰며, 두 경로가 각자
    `token_version + 1`을 적어 두면 언제든 한쪽만 바뀔 수 있다.
    """
    return {"token_version": AppUser.token_version + 1}
