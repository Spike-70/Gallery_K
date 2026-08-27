"""엔진과 세션 (백엔드 문서 §4.4).

엔진은 **모듈 로드 시 1회** 생성한다. 풀은 `NullPool` — Lambda 인스턴스가 요청 사이에
얼어붙기 때문에 풀에 남은 연결은 다음 요청에서 대개 죽어 있다. 연결을 아끼는 것보다
매번 새로 여는 편이 예측 가능하다.

**커밋은 미들웨어의 책임이다.** 여기서도, 서비스에서도 커밋하지 않는다.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from chalicelib.config.settings import settings


def _connect_args() -> dict[str, Any]:
    # 세션 TZ는 UTC 고정(DB 문서 §2). 질의 타임아웃은 Lambda 타임아웃보다 짧다.
    options = f"-c timezone=UTC -c statement_timeout={settings.db_statement_timeout_ms}"
    return {
        "connect_timeout": settings.db_connect_timeout_seconds,
        "options": options,
    }


def create_db_engine(url: str | None = None) -> Engine:
    return create_engine(
        url or settings.database_url,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args=_connect_args(),
        future=True,
    )


#: 모듈 로드 시 1회. 엔진 생성은 연결을 열지 않으므로 콜드 스타트에 안전하다.
engine: Engine = create_db_engine()

_session_factory = sessionmaker(
    bind=engine,
    class_=Session,
    expire_on_commit=False,
    autoflush=False,
)


def open_session() -> Session:
    """요청 스코프 세션. `db_session` 미들웨어가 지연 생성으로 등록한다."""
    return _session_factory()


def ping() -> bool:
    """헬스 체크용. 예외를 밖으로 내지 않는다 — `degraded`도 200이어야 한다(PRD §8.5)."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
