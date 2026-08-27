"""공용 DB 접근 헬퍼 (백엔드 문서 §4).

**테이블별 리포지토리를 두지 않는다.** 테이블 수만큼 CRUD 래퍼를 복제하면 같은 코드가
11벌 생기고, 그중 하나만 고쳐지는 날이 온다. 대신 관계 탐색·필터·정렬·페이지네이션을
내재한 범용 헬퍼 하나를 두고 서비스가 직접 호출한다.

표현 수단
  * 필터      `필드__연산자=값`. AND/OR/NOT 결합은 `Q`로 한다
  * 관계 탐색 `관계__필드` 경로를 쓰면 필요한 조인이 자동 구성된다
  * 관계 로딩 `joined=` (조인 즉시) / `selectin=` (별도 질의 일괄).
              **기본은 지연 로딩 금지** — 모델의 관계가 `lazy="raise"`이므로 로딩을
              지정하지 않고 접근하면 예외가 난다. N+1의 출처를 원천 차단한다
  * 정렬·제한 다중 정렬 키(`-` 접두는 내림차순), 개수 제한, 오프셋
  * 투영      `columns=`로 반환 컬럼 선택, `as_dict=`로 사전 형태 선택
  * 집계      `aggregate()`가 그룹 기준과 집계 함수를 인자로 받는다
  * 잠금      `for_update=`

규칙
  * **문자열 SQL 조립을 금지**한다. 파라미터 바인딩만 쓴다
  * 헬퍼로 표현되지 않는 질의는 `db/queries/`에 이름 있는 함수로 격리한다
  * 삭제는 DB의 `ON DELETE`에 위임한다. 애플리케이션이 자식 행을 루프로 지우지 않는다
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final, Literal, cast

from sqlalchemy import ColumnElement, CursorResult, Select, and_, func, literal, not_, or_, select
from sqlalchemy import delete as sa_delete
from sqlalchemy import false as sa_false
from sqlalchemy import true as sa_true
from sqlalchemy import update as sa_update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import InstrumentedAttribute, Session, joinedload, selectinload
from sqlalchemy.sql.elements import BooleanClauseList

from chalicelib.core.errors import AppError, ErrorCode

SEPARATOR: Final = "__"

#: 필터 연산자. 이름이 곧 규약이므로 임의로 늘리지 않는다.
_OPERATORS: Final[dict[str, str]] = {
    "eq": "__eq__",
    "ne": "__ne__",
    "lt": "__lt__",
    "lte": "__le__",
    "gt": "__gt__",
    "gte": "__ge__",
    "in": "in_",
    "not_in": "not_in",
    "like": "like",
    "ilike": "ilike",
    "contains": "contains",
    "startswith": "startswith",
    "endswith": "endswith",
    "isnull": "isnull",
    "between": "between",
}


LIKE_ESCAPE: Final = "\\"


def escape_like(value: str) -> str:
    """LIKE 패턴의 메타문자를 무력화한다. 전용 질의도 이 함수를 쓴다."""
    for character in (LIKE_ESCAPE, "%", "_"):
        value = value.replace(character, LIKE_ESCAPE + character)
    return value


class Q:
    """필터 표현. `Q(a=1) & (Q(b=2) | ~Q(c=3))` 형태로 결합한다."""

    __slots__ = ("_clause", "_filters")

    def __init__(self, **filters: Any) -> None:
        self._filters: dict[str, Any] = filters
        self._clause: _Combination | None = None

    @classmethod
    def _from_clause(cls, clause: _Combination) -> Q:
        instance = cls()
        instance._clause = clause
        return instance

    def __and__(self, other: Q) -> Q:
        return Q._from_clause(_Combination("and", (self, other)))

    def __or__(self, other: Q) -> Q:
        return Q._from_clause(_Combination("or", (self, other)))

    def __invert__(self) -> Q:
        return Q._from_clause(_Combination("not", (self,)))

    def __bool__(self) -> bool:
        return bool(self._filters) or self._clause is not None

    def build(self, resolver: _PathResolver) -> ColumnElement[bool] | None:
        if self._clause is not None:
            return self._clause.build(resolver)
        conditions = [_condition(resolver, key, value) for key, value in self._filters.items()]
        if not conditions:
            return None
        return and_(*conditions)


@dataclass(frozen=True, slots=True)
class _Combination:
    kind: Literal["and", "or", "not"]
    operands: tuple[Q, ...]

    def build(self, resolver: _PathResolver) -> ColumnElement[bool] | None:
        built = [operand.build(resolver) for operand in self.operands]
        present = [item for item in built if item is not None]
        if not present:
            return None
        if self.kind == "and":
            return and_(*present)
        if self.kind == "or":
            return or_(*present)
        return not_(present[0])


WhereType = Q | Mapping[str, Any] | ColumnElement[bool] | BooleanClauseList | None


class _PathResolver:
    """`관계__필드` 경로를 컬럼으로 바꾸며 필요한 조인을 모은다."""

    def __init__(self, model: type) -> None:
        self.model = model
        self._joins: list[tuple[Any, Any]] = []
        self._aliases: dict[str, Any] = {}

    @property
    def joins(self) -> list[tuple[Any, Any]]:
        return self._joins

    def resolve(self, path: str) -> tuple[InstrumentedAttribute[Any], str]:
        """(컬럼, 연산자 이름)을 돌려준다. 연산자가 없으면 `eq`."""
        parts = path.split(SEPARATOR)
        operator = "eq"
        if len(parts) > 1 and parts[-1] in _OPERATORS:
            operator = parts[-1]
            parts = parts[:-1]
        if not parts:
            raise AppError(ErrorCode.VALIDATION_FAILED, doc_hint=f"빈 필터 경로: {path}")

        current: Any = self.model
        prefix = ""
        for index, part in enumerate(parts):
            mapper = sa_inspect(current)
            attribute = getattr(current, part, None)
            if attribute is None:
                raise AppError(
                    ErrorCode.VALIDATION_FAILED,
                    doc_hint=f"알 수 없는 필드입니다: {path} ({part})",
                )
            is_last = index == len(parts) - 1
            if not is_last:
                prefix = f"{prefix}{SEPARATOR}{part}" if prefix else part
                target = mapper.relationships[part].mapper.class_
                if prefix not in self._aliases:
                    self._aliases[prefix] = target
                    self._joins.append((target, attribute))
                current = self._aliases[prefix]
                continue
            return attribute, operator
        raise AppError(ErrorCode.VALIDATION_FAILED, doc_hint=f"해석할 수 없는 경로: {path}")


def _condition(resolver: _PathResolver, path: str, value: Any) -> ColumnElement[bool]:
    column, operator = resolver.resolve(path)
    if operator == "isnull":
        return column.is_(None) if value else column.is_not(None)
    if operator == "between":
        low, high = value
        return column.between(low, high)
    if operator in {"contains", "startswith", "endswith"} and isinstance(value, str):
        # 부분일치는 대소문자를 구분하지 않는다. 한글에는 무영향이고 영문 검색만 편해진다.
        # 검색어 안의 `%`·`_`는 **글자 그대로** 다룬다 — 이스케이프하지 않으면 `%` 한 글자로
        # 전체 목록이 나온다.
        escaped = escape_like(value)
        patterns = {
            "contains": f"%{escaped}%",
            "startswith": f"{escaped}%",
            "endswith": f"%{escaped}",
        }
        return column.ilike(patterns[operator], escape=LIKE_ESCAPE)
    if operator in {"in", "not_in"}:
        values = list(value)
        if not values:
            # 빈 목록의 IN은 항상 거짓, NOT IN은 항상 참이다. DB에 빈 배열을 보내지 않는다.
            return sa_false() if operator == "in" else sa_true()
        return getattr(column, _OPERATORS[operator])(values)
    return getattr(column, _OPERATORS[operator])(value)


def _build_where(resolver: _PathResolver, where: WhereType) -> ColumnElement[bool] | None:
    if where is None:
        return None
    if isinstance(where, Q):
        return where.build(resolver)
    if isinstance(where, Mapping):
        return Q(**dict(where)).build(resolver)
    return where


def _apply_order(statement: Select[Any], resolver: _PathResolver, order_by: Sequence[str]) -> Select[Any]:
    for key in order_by:
        descending = key.startswith("-")
        column, _ = resolver.resolve(key[1:] if descending else key)
        statement = statement.order_by(column.desc() if descending else column.asc())
    return statement


def _apply_joins(statement: Select[Any], resolver: _PathResolver) -> Select[Any]:
    for target, relationship in resolver.joins:
        statement = statement.join(target, relationship)
    return statement


def _apply_loading(
    statement: Select[Any], joined: Sequence[str], selectin: Sequence[str], model: type
) -> Select[Any]:
    options = []
    for path in joined:
        options.append(_loader_chain(model, path, joinedload))
    for path in selectin:
        options.append(_loader_chain(model, path, selectinload))
    return statement.options(*options) if options else statement


def _loader_chain(model: type, path: str, loader: Any) -> Any:
    current: Any = model
    option: Any = None
    for part in path.split(SEPARATOR):
        attribute = getattr(current, part)
        option = loader(attribute) if option is None else getattr(option, loader.__name__)(attribute)
        current = sa_inspect(current).relationships[part].mapper.class_
    return option


def _select[ModelT](
    model: type[ModelT],
    *,
    columns: Sequence[str] | None,
    resolver: _PathResolver,
) -> Select[Any]:
    if not columns:
        return select(model)
    selected = [resolver.resolve(name)[0] for name in columns]
    return select(*selected)


def _rows_to_dicts(rows: Iterable[Any], columns: Sequence[str]) -> list[dict[str, Any]]:
    keys = [name.split(SEPARATOR)[-1] for name in columns]
    return [dict(zip(keys, row, strict=True)) for row in rows]


# ── 조회 ───────────────────────────────────────────────────────────────────


def fetch[ModelT](
    session: Session,
    model: type[ModelT],
    *,
    where: WhereType = None,
    order_by: Sequence[str] = (),
    limit: int | None = None,
    offset: int | None = None,
    columns: Sequence[str] | None = None,
    joined: Sequence[str] = (),
    selectin: Sequence[str] = (),
    distinct: bool = False,
    for_update: bool = False,
    skip_locked: bool = False,
) -> list[Any]:
    resolver = _PathResolver(model)
    statement = _select(model, columns=columns, resolver=resolver)
    condition = _build_where(resolver, where)
    statement = _apply_joins(statement, resolver)
    if condition is not None:
        statement = statement.where(condition)
    statement = _apply_order(statement, resolver, order_by)
    if distinct:
        statement = statement.distinct()
    if limit is not None:
        statement = statement.limit(limit)
    if offset:
        statement = statement.offset(offset)
    if for_update:
        statement = statement.with_for_update(skip_locked=skip_locked)
    statement = _apply_loading(statement, joined, selectin, model)

    if columns:
        return _rows_to_dicts(session.execute(statement).all(), columns)
    return list(session.execute(statement).unique().scalars().all())


def fetch_one[ModelT](
    session: Session,
    model: type[ModelT],
    *,
    where: WhereType = None,
    order_by: Sequence[str] = (),
    columns: Sequence[str] | None = None,
    joined: Sequence[str] = (),
    selectin: Sequence[str] = (),
    for_update: bool = False,
) -> Any | None:
    rows = fetch(
        session,
        model,
        where=where,
        order_by=order_by,
        limit=1,
        columns=columns,
        joined=joined,
        selectin=selectin,
        for_update=for_update,
    )
    return rows[0] if rows else None


def exists[ModelT](session: Session, model: type[ModelT], *, where: WhereType = None) -> bool:
    """한 행이라도 있는지만 본다.

    `count(*)`로 세지 않는다 — 존재 확인에 전체 스캔을 시키면 `view_log`처럼 큰 테이블에서
    호출 한 번의 비용이 행 수에 비례한다. 첫 행을 찾는 즉시 끝낸다.
    """
    resolver = _PathResolver(model)
    statement = select(literal(1)).select_from(model)
    condition = _build_where(resolver, where)
    statement = _apply_joins(statement, resolver)
    if condition is not None:
        statement = statement.where(condition)
    return session.execute(statement.limit(1)).first() is not None


def count[ModelT](
    session: Session,
    model: type[ModelT],
    *,
    where: WhereType = None,
    distinct_on: str | None = None,
) -> int:
    resolver = _PathResolver(model)
    target = func.count(func.distinct(resolver.resolve(distinct_on)[0])) if distinct_on else func.count()
    statement = select(target).select_from(model)
    condition = _build_where(resolver, where)
    statement = _apply_joins(statement, resolver)
    if condition is not None:
        statement = statement.where(condition)
    return int(session.execute(statement).scalar_one())


def aggregate[ModelT](
    session: Session,
    model: type[ModelT],
    *,
    values: Mapping[str, ColumnElement[Any]],
    group_by: Sequence[str] = (),
    where: WhereType = None,
    order_by: Sequence[str] = (),
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """그룹 기준과 집계 함수를 인자로 받는다. 통계 화면의 유일한 집계 경로다."""
    resolver = _PathResolver(model)
    group_columns = [resolver.resolve(name)[0] for name in group_by]
    selected = [*group_columns, *[expression.label(alias) for alias, expression in values.items()]]
    statement = select(*selected)
    condition = _build_where(resolver, where)
    statement = _apply_joins(statement, resolver)
    if condition is not None:
        statement = statement.where(condition)
    if group_columns:
        statement = statement.group_by(*group_columns)
    statement = _apply_order(statement, resolver, order_by)
    if limit is not None:
        statement = statement.limit(limit)
    keys = [name.split(SEPARATOR)[-1] for name in group_by] + list(values)
    return [dict(zip(keys, row, strict=True)) for row in session.execute(statement).all()]


# ── 변경 ───────────────────────────────────────────────────────────────────


def _forget_generated(instance: Any) -> None:
    """생성 컬럼은 DB가 채운다.

    SQLModel은 파이썬 기본값을 인스턴스에 얹기 때문에 그대로 두면 ORM이 `is_complete`를
    INSERT 목록에 넣고 PostgreSQL이 거부한다(`GeneratedAlways`). 값을 지워 두면 INSERT에서
    빠지고, 이후 접근 시 DB가 계산한 값을 읽어 온다.
    """
    state = sa_inspect(instance)
    for column in state.mapper.columns:
        if column.computed is not None:
            state.dict.pop(column.key, None)


def insert[ModelT](session: Session, model: type[ModelT], values: Mapping[str, Any]) -> ModelT:
    instance = model(**dict(values))
    _forget_generated(instance)
    session.add(instance)
    session.flush()
    return instance


def bulk_insert[ModelT](
    session: Session, model: type[ModelT], rows: Sequence[Mapping[str, Any]]
) -> list[ModelT]:
    instances = [model(**dict(row)) for row in rows]
    for instance in instances:
        _forget_generated(instance)
    session.add_all(instances)
    session.flush()
    return instances


def update[ModelT](
    session: Session,
    model: type[ModelT],
    *,
    where: WhereType,
    values: Mapping[str, Any],
    expected_version: int | None = None,
    bump_version: bool = True,
) -> int:
    """조건부 UPDATE.

    `expected_version`을 주면 낙관적 잠금이 된다 — `WHERE ... AND version = :expected`가
    0행을 건드리면 다른 곳에서 먼저 수정된 것이고 `409 CONFLICT_VERSION`이다.
    """
    resolver = _PathResolver(model)
    condition = _build_where(resolver, where)
    if resolver.joins:
        raise AppError(ErrorCode.SYSTEM_INTERNAL, doc_hint="UPDATE의 필터에는 관계 경로를 쓸 수 없습니다")

    payload = dict(values)
    has_version = hasattr(model, "version")
    if expected_version is not None:
        if not has_version:
            raise AppError(ErrorCode.SYSTEM_INTERNAL, doc_hint="version 컬럼이 없는 모델입니다")
        version_condition = model.version == expected_version  # type: ignore[attr-defined]
        condition = version_condition if condition is None else and_(condition, version_condition)
    if bump_version and has_version and "version" not in payload:
        payload["version"] = model.version + 1  # type: ignore[attr-defined]

    statement = sa_update(model).values(**payload)
    if condition is not None:
        statement = statement.where(condition)
    result = cast(
        "CursorResult[Any]", session.execute(statement.execution_options(synchronize_session=False))
    )
    affected = int(result.rowcount or 0)
    if expected_version is not None and affected == 0:
        # 문서가 요구하는 `current_version`을 실제로 채운다(API 문서 §5.1). 값이 비어 있으면
        # 클라이언트는 무엇으로 다시 시도해야 하는지 알 수 없다.
        raise AppError(
            ErrorCode.CONFLICT_VERSION,
            details={"current_version": _current_version(session, model, where)},
        )
    return affected


def _current_version[ModelT](session: Session, model: type[ModelT], where: WhereType) -> int | None:
    """충돌한 행의 현재 버전. 행 자체가 사라졌으면 None이다."""
    resolver = _PathResolver(model)
    condition = _build_where(resolver, where)
    if condition is None:
        return None
    version_column = getattr(model, "version", None)
    if version_column is None:
        return None
    row = session.execute(select(version_column).where(condition).limit(1)).first()
    return int(row[0]) if row else None


def bulk_update[ModelT](
    session: Session, model: type[ModelT], rows: Sequence[Mapping[str, Any]], *, key: str = "id"
) -> int:
    """행마다 다른 값을 한 번에 반영한다. 순서 변경(reorder)이 이것을 쓴다."""
    if not rows:
        return 0
    session.execute(sa_update(model), [dict(row) for row in rows])
    session.flush()
    return len(rows)


def upsert[ModelT](
    session: Session,
    model: type[ModelT],
    *,
    values: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    conflict: Sequence[str],
    update_values: Mapping[str, Any] | None = None,
    returning: Sequence[str] | None = None,
) -> dict[str, Any] | list[dict[str, Any]] | None:
    """`INSERT ... ON CONFLICT`. 기록 API의 자연 멱등성이 여기서 나온다.

    `update_values`가 없으면 `DO NOTHING`이다.

    `values`에 **여러 행을 넘기면 한 번의 문장으로** 처리한다. 발행 시점에 회원 수만큼
    알림을 예약하는 경로가 이것을 쓰며, 행마다 왕복하면 발행 요청이 회원 수에 비례해
    느려진다. 여러 행을 넘겼을 때의 반환도 리스트다.
    """
    table = model.__table__  # type: ignore[attr-defined]
    many = not isinstance(values, Mapping)
    rows = [dict(row) for row in values] if many else [dict(values)]  # type: ignore[arg-type]
    if not rows:
        return [] if many else None

    statement: Any = pg_insert(table).values(rows)
    if update_values:
        statement = statement.on_conflict_do_update(index_elements=list(conflict), set_=dict(update_values))
    else:
        statement = statement.on_conflict_do_nothing(index_elements=list(conflict))
    if returning:
        statement = statement.returning(*[table.c[name] for name in returning])
        found = [dict(zip(returning, row, strict=True)) for row in session.execute(statement).all()]
        if many:
            return found
        return found[0] if found else None
    session.execute(statement)
    return [] if many else None


def delete[ModelT](session: Session, model: type[ModelT], *, where: WhereType) -> int:
    """자식 행은 DB의 `ON DELETE`가 지운다. 애플리케이션이 루프로 지우지 않는다."""
    resolver = _PathResolver(model)
    condition = _build_where(resolver, where)
    if resolver.joins:
        raise AppError(ErrorCode.SYSTEM_INTERNAL, doc_hint="DELETE의 필터에는 관계 경로를 쓸 수 없습니다")
    statement = sa_delete(model)
    if condition is not None:
        statement = statement.where(condition)
    result = cast(
        "CursorResult[Any]", session.execute(statement.execution_options(synchronize_session=False))
    )
    return int(result.rowcount or 0)
