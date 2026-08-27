"""인증 시도 제한 (DB 문서 §4.2, API 문서 §2.10).

Lambda는 인스턴스 메모리를 신뢰할 수 없으므로 시도 상태를 DB에 둔다. 같은 전화번호로
다른 인스턴스에 붙어도 같은 카운터를 본다.

스코프마다 의미가 다르다.
  * `login`         — **연속 실패** 5회면 10분 잠금. 성공하면 행을 지운다
  * 그 외           — **시간창 안의 시도 횟수**. 초과하면 창이 끝날 때까지 잠근다
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Final, cast

from sqlalchemy import ColumnElement, case
from sqlalchemy import false as sa_false
from sqlalchemy.orm import Session

from chalicelib.config.constants import (
    THROTTLE_LOGIN_LOCK_SECONDS,
    THROTTLE_LOGIN_MAX_FAILURES,
    THROTTLE_PASSWORD_RESET_MAX_ATTEMPTS,
    THROTTLE_PASSWORD_RESET_WINDOW_SECONDS,
    THROTTLE_SIGNUP_MAX_ATTEMPTS,
    THROTTLE_SIGNUP_WINDOW_SECONDS,
    THROTTLE_UPLOAD_URL_MAX_ATTEMPTS,
    THROTTLE_UPLOAD_URL_WINDOW_SECONDS,
)
from chalicelib.core.timeutil import now_utc
from chalicelib.db import query as q
from chalicelib.db.models import AuthThrottle
from chalicelib.db.models.enums import ThrottleScope


@dataclass(frozen=True, slots=True)
class Policy:
    max_attempts: int
    #: None이면 연속 실패 방식이다.
    window_seconds: int | None
    lock_seconds: int

    @property
    def lock_at(self) -> int:
        """이 횟수에 도달하면 잠근다.

        두 방식의 셈이 다르다.
          * 연속 실패(`login`) — 임계 번째 **실패**에서 곧바로 잠근다. 그 시도는 이미
            실패했으므로 "5회 연속 실패 → 차단"이 그대로 성립한다
          * 시간창(그 외) — 허용량을 다 쓴 **다음** 시도에서 잠근다. "60회 / 10분"은
            60번째까지 통과하고 61번째가 막힌다는 뜻이다
        """
        return self.max_attempts if self.window_seconds is None else self.max_attempts + 1


#: 스코프 별칭. `api` 계층은 `db.models`를 직접 import 하지 않으므로(문서 §5) 여기를 통해
#: 열거형 값을 참조한다. 단일 진실 원천은 여전히 `db/models/enums.py`다.
LOGIN: Final = ThrottleScope.LOGIN
SIGNUP: Final = ThrottleScope.SIGNUP
PASSWORD_RESET: Final = ThrottleScope.PASSWORD_RESET
UPLOAD_URL: Final = ThrottleScope.UPLOAD_URL

POLICIES: Final[dict[str, Policy]] = {
    ThrottleScope.LOGIN: Policy(THROTTLE_LOGIN_MAX_FAILURES, None, THROTTLE_LOGIN_LOCK_SECONDS),
    ThrottleScope.SIGNUP: Policy(
        THROTTLE_SIGNUP_MAX_ATTEMPTS, THROTTLE_SIGNUP_WINDOW_SECONDS, THROTTLE_SIGNUP_WINDOW_SECONDS
    ),
    ThrottleScope.PASSWORD_RESET: Policy(
        THROTTLE_PASSWORD_RESET_MAX_ATTEMPTS,
        THROTTLE_PASSWORD_RESET_WINDOW_SECONDS,
        THROTTLE_PASSWORD_RESET_WINDOW_SECONDS,
    ),
    ThrottleScope.UPLOAD_URL: Policy(
        THROTTLE_UPLOAD_URL_MAX_ATTEMPTS,
        THROTTLE_UPLOAD_URL_WINDOW_SECONDS,
        THROTTLE_UPLOAD_URL_WINDOW_SECONDS,
    ),
}


def build_key(scope: str, identifier: str) -> str:
    return f"{scope}:{identifier}"


def remaining_lock_seconds(session: Session, scope: str, identifier: str) -> int:
    """잠겨 있으면 남은 초, 아니면 0. `@throttled`가 요청 처리 전에 부른다."""
    row = q.fetch_one(
        session,
        AuthThrottle,
        where={"throttle_key": build_key(scope, identifier)},
        columns=["locked_until"],
    )
    if row is None or row["locked_until"] is None:
        return 0
    remaining = (row["locked_until"] - now_utc()).total_seconds()
    return max(0, int(remaining))


def register_hit(scope: str, identifier: str) -> int:
    """시도를 원자적으로 누적한다. 임계를 넘으면 잠그고 남은 초를 돌려준다.

    **요청 트랜잭션과 별개의 세션에서 커밋한다.** 로그인 실패는 401로 끝나고 요청
    트랜잭션은 롤백되는데, 그때 카운터까지 되돌아가면 시도 제한이 성립하지 않는다.
    """
    session = _own_session()
    try:
        locked = _register_hit(session, scope, identifier)
        session.commit()
        return locked
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _register_hit(session: Session, scope: str, identifier: str) -> int:
    """**한 문장의 UPSERT**로 시도를 누적하고, 그 결과로 잠금을 판정한다.

    이전 구현은 조회 → 갱신 → 재조회로 왕복이 서너 번이었다. 인증 실패 경로는 공격자가
    가장 많이 두드리는 곳이므로, 여기서의 왕복 수가 곧 방어 비용이다.

    시간창 방식(`signup`·`password_reset`·`upload_url`)은 창이 지났으면 카운터를 1로
    되돌리고, 연속 실패 방식(`login`)은 성공 전까지 계속 누적한다. 그 판정을 SQL 안에
    두어 읽고-쓰는 사이의 경쟁을 없앤다.
    """
    policy = POLICIES[scope]
    now = now_utc()
    key = build_key(scope, identifier)

    window_start = now - _dt.timedelta(seconds=policy.window_seconds) if policy.window_seconds else None
    # 시간창이 지났는가 — 지났으면 카운터를 새로 시작한다. SQLModel의 필드 애너테이션이
    # 비교식을 파이썬 bool로 보이게 하므로 SQL 표현식임을 명시한다.
    expired: ColumnElement[bool] = sa_false()
    if window_start is not None:
        expired = cast("ColumnElement[bool]", AuthThrottle.first_failed_at) < window_start

    updated = q.upsert(
        session,
        AuthThrottle,
        values={
            "id": _new_id(),
            "throttle_key": key,
            "scope": scope,
            "fail_count": 1,
            "first_failed_at": now,
            "last_failed_at": now,
            "created_at": now,
            "updated_at": now,
        },
        conflict=["throttle_key"],
        update_values={
            "fail_count": case((expired, 1), else_=AuthThrottle.fail_count + 1),
            "first_failed_at": case((expired, now), else_=AuthThrottle.first_failed_at),
            "locked_until": case((expired, None), else_=AuthThrottle.locked_until),
            "last_failed_at": now,
            "updated_at": now,
        },
        returning=["fail_count"],
    )
    fail_count = int(updated["fail_count"]) if isinstance(updated, dict) else 1
    if fail_count < policy.lock_at:
        return 0

    locked_until = now + _dt.timedelta(seconds=policy.lock_seconds)
    q.update(
        session,
        AuthThrottle,
        where={"throttle_key": key},
        values={"locked_until": locked_until, "updated_at": now},
    )
    return policy.lock_seconds


def clear(scope: str, identifier: str) -> None:
    """성공하면 행을 지운다 — 남겨 둘 이유가 없고, 야간 배치의 대상도 줄어든다."""
    session = _own_session()
    try:
        q.delete(session, AuthThrottle, where={"throttle_key": build_key(scope, identifier)})
        session.commit()
    finally:
        session.close()


def _own_session() -> Session:
    # 모듈 속성으로 돌아간다 — 테스트가 세션을 바꿔칠 수 있어야 한다.
    from chalicelib.db import engine as engine_module

    return engine_module.open_session()


def _new_id() -> object:
    from chalicelib.core.ids import new_id

    return new_id()
