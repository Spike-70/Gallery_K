"""요청 스코프 컨텍스트 (백엔드 문서 §6).

한 요청이 처리되는 동안 모든 계층이 같은 값을 봐야 하는 것들을 담는다 —
요청 ID, 그 요청이 기준으로 삼는 **하나의 시각**, KST 오늘, 인증된 행위자,
그리고 응답에 붙을 쿠키·헤더.

시각을 컨텍스트에 고정하는 이유: 한 요청 안에서 `now()`를 여러 번 부르면 자정 근처에서
`viewed_on`과 `created_at`이 다른 날에 속할 수 있다.

DB 세션은 **지연 생성**이다. 미인증·`304`로 끝나는 요청이 커넥션을 점유하지 않게
한다(교차검토 X-14).
"""

from __future__ import annotations

import datetime as _dt
import uuid
from collections.abc import Callable
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any

from chalicelib.core.ids import new_request_id
from chalicelib.core.timeutil import kst_today, now_utc


@dataclass(slots=True)
class RequestContext:
    request_id: str
    method: str
    path: str
    #: 이 요청의 기준 시각. 요청 내내 바뀌지 않는다.
    now: _dt.datetime
    #: 서버 기준 KST 오늘. 관람일·달력의 기준이다.
    today: _dt.date

    actor_id: uuid.UUID | None = None
    actor_role: str | None = None
    token_version: int | None = None
    #: 슬라이딩 갱신 대상인지 — `response_finalize`가 새 쿠키를 굽는다.
    renew_session: bool = False
    #: 로그아웃·탈퇴 시 쿠키를 만료시킨다.
    clear_session: bool = False
    #: 세션이 있었으나 무효였던 이유. `@require`가 401 코드를 고를 때 쓴다.
    auth_error: str | None = None

    #: 세션 생성 함수. `db_session` 미들웨어가 주입한다.
    session_factory: Callable[[], Any] | None = field(default=None, repr=False)
    _session: Any | None = field(default=None, repr=False)

    #: 응답에 붙일 것들
    set_cookies: list[str] = field(default_factory=list)
    extra_headers: dict[str, str] = field(default_factory=dict)
    cache_control: str | None = None
    etag: str | None = None

    #: 감사 로그용 — `@audited`가 채우고 서비스가 요약을 덧붙인다.
    audit_entries: list[dict[str, Any]] = field(default_factory=list)

    #: 오류로 끝난 요청임을 표시한다. `db_session` 미들웨어가 커밋 대신 롤백한다.
    #: 라우트 경계에서 예외를 봉투로 바꾸므로, 미들웨어에게는 정상 반환처럼 보인다.
    rollback_only: bool = False

    @property
    def is_authenticated(self) -> bool:
        return self.actor_id is not None

    @property
    def is_curator(self) -> bool:
        return self.actor_role == "curator"

    @property
    def has_session(self) -> bool:
        """세션을 실제로 열었는가. 커밋 여부 판단에 쓴다."""
        return self._session is not None

    @property
    def db(self) -> Any:
        """요청 스코프 DB 세션. **첫 접근 시점에 생성된다.**"""
        if self._session is None:
            if self.session_factory is None:
                raise RuntimeError("DB 세션 팩토리가 등록되지 않았습니다 (db_session 미들웨어 확인)")
            self._session = self.session_factory()
        return self._session

    def reset_session(self) -> None:
        self._session = None


@dataclass(frozen=True, slots=True)
class ActorSnapshot:
    """인증된 요청자. **모델 객체가 아니라 값 스냅샷**이 계층을 넘나든다.

    프레임워크를 모르는 값이므로 `services`도 이것을 안전하게 import 한다.
    """

    id: uuid.UUID
    role: str
    token_version: int


@dataclass(frozen=True, slots=True)
class MaintenanceState:
    enabled: bool
    until: str | None = None


_current: ContextVar[RequestContext | None] = ContextVar("gallery_k_request_context", default=None)


def new_context(method: str, path: str) -> RequestContext:
    """요청 시작 시 1회. 시각과 KST 오늘을 여기서 한 번만 계산한다."""
    return RequestContext(
        request_id=new_request_id(),
        method=method,
        path=path,
        now=now_utc(),
        today=kst_today(),
    )


def bind(context: RequestContext) -> Token[RequestContext | None]:
    return _current.set(context)


def unbind(token: Token[RequestContext | None]) -> None:
    _current.reset(token)


def current() -> RequestContext:
    """현재 요청 컨텍스트. 요청 밖에서 부르면 프로그래밍 오류다."""
    context = _current.get()
    if context is None:
        raise RuntimeError("요청 컨텍스트 밖에서 호출되었습니다")
    return context


def current_or_none() -> RequestContext | None:
    """로거처럼 요청 밖(배치)에서도 도는 코드용."""
    return _current.get()
