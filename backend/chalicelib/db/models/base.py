"""모델 공통 규약 (DB 문서 §2).

* PK는 애플리케이션이 만드는 UUIDv7
* 시각은 `timestamptz`(UTC 저장), 업무일은 `date`
* 문자열은 전부 `varchar(n)` — 무제한 `text`를 쓰지 않는다
* 제약·인덱스 이름은 `ix_` `uq_` `ck_` `fk_` `ex_` 접두를 따른다
"""

from __future__ import annotations

import datetime as _dt
import uuid

from sqlalchemy import DateTime, Integer, MetaData
from sqlalchemy import text as sa_text
from sqlmodel import Field, SQLModel

from chalicelib.core.ids import new_id
from chalicelib.core.timeutil import now_utc

#: 자동 생성되는 제약·인덱스 이름을 규약에 맞춘다. 이름 없는 제약이 생기면
#: 제약 위반 → 오류 코드 매핑(백엔드 문서 §8.2)이 성립하지 않는다.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}

metadata: MetaData = SQLModel.metadata
metadata.naming_convention = NAMING_CONVENTION


# 믹스인 필드는 `sa_column=`을 쓸 수 없다 — Column 객체는 테이블 하나에만 붙는다.
# `sa_type=` + `sa_column_kwargs=`로 선언하면 상속받는 모델마다 새 Column이 만들어진다.


class UUIDPKMixin(SQLModel):
    id: uuid.UUID = Field(default_factory=new_id, primary_key=True, nullable=False)


class TimestampMixin(SQLModel):
    # SQLModel의 타입 스텁은 `sa_type`을 클래스로만 선언해 두었으나 런타임은 인스턴스를
    # 받는다. `timezone=True`가 곧 `timestamptz`이므로 인스턴스가 필요하다.
    created_at: _dt.datetime = Field(
        default_factory=now_utc,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        nullable=False,
    )
    #: ORM `onupdate`로 갱신한다. 우리 시계를 쓰므로 테스트가 고정할 수 있다.
    updated_at: _dt.datetime = Field(
        default_factory=now_utc,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        nullable=False,
        sa_column_kwargs={"onupdate": now_utc},
    )


class VersionMixin(SQLModel):
    """낙관적 잠금. 충돌 시 `409 CONFLICT_VERSION` (DB 문서 §2).

    검사는 매퍼 기능이 아니라 **조건부 UPDATE**로 한다(`db/query.py`의 `expected_version`).
    `WHERE id = :id AND version = :expected`가 0행을 건드리면 충돌이며, 규칙이 ORM
    내부 동작이 아니라 눈에 보이는 SQL 한 줄에 있다.
    """

    version: int = Field(
        default=1,
        sa_type=Integer,
        nullable=False,
        sa_column_kwargs={"server_default": sa_text("1")},
    )
