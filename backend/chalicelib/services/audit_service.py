"""감사 기록 (DB 문서 §4.11, 백엔드 문서 §13).

관리자 변경 조작은 **전건** 남는다. `@audited` 데코레이터가 성공한 요청에서 이 서비스를
부르고, 서비스가 요청 처리 중에 `stage()`로 쌓아 둔 요약·변경 내역을 함께 기록한다.

비밀번호 해시·전화번호 전체를 담지 않는다.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from chalicelib.core.timeutil import now_utc
from chalicelib.db import query as q
from chalicelib.db.models import AuditLog
from chalicelib.utils.text import mask_phone

#: 값이 통째로 빠져야 하는 키. 로그 필터와 같은 목록을 쓰지 않는 이유는 여기가
#: **영구 저장**이기 때문이다 — 더 좁게 잡는다.
_FORBIDDEN_KEYS = frozenset({"password", "password_hash", "new_password", "initial_password", "token"})
_PHONE_KEYS = frozenset({"phone", "curator_phone"})


def scrub(payload: Any) -> Any:
    if isinstance(payload, dict):
        cleaned: dict[str, Any] = {}
        for key, value in payload.items():
            lowered = str(key).lower()
            if lowered in _FORBIDDEN_KEYS:
                continue
            if lowered in _PHONE_KEYS and isinstance(value, str):
                cleaned[key] = mask_phone(value)
                continue
            cleaned[key] = scrub(value)
        return cleaned
    if isinstance(payload, list):
        return [scrub(item) for item in payload]
    return payload


def record(
    session: Session,
    *,
    action: str,
    actor_id: uuid.UUID | None,
    actor_role: str | None,
    request_id: str | None,
    target_type: str | None = None,
    target_id: str | None = None,
    summary: str | None = None,
    changes: dict[str, Any] | None = None,
) -> None:
    q.insert(
        session,
        AuditLog,
        {
            "actor_id": actor_id,
            "actor_role": actor_role,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "summary": summary,
            "changes": scrub(changes) if changes else None,
            "request_id": request_id,
            "created_at": now_utc(),
        },
    )
