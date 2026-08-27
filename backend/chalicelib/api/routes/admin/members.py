"""회원 관리·설정·공지·통계 API (API 문서 §9.13–§9.19)."""

from __future__ import annotations

import datetime as _dt
import uuid

from chalicelib.api.routes._base import blueprint, route
from chalicelib.config.constants import (
    CACHE_NO_STORE,
    MEMBER_LIST_DEFAULT_LIMIT,
    NOTICE_LIST_DEFAULT_LIMIT,
    PAGINATION_MAX_LIMIT,
    STATS_DAILY_DAYS,
    STATS_MAX_RANGE_DAYS,
    STATS_MEMBER_DEFAULT_DAYS,
    STATS_MEMBER_MAX_DAYS,
)
from chalicelib.core import context as ctx_module
from chalicelib.core.decorators import CURATOR, audited, body, paginated, query, require
from chalicelib.core.envelope import Result
from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.ids import parse_uuid
from chalicelib.core.pagination import PAGE, PageParams, page_meta
from chalicelib.core.timeutil import parse_date
from chalicelib.schemas.member_admin import (
    AppSettingsPatchIn,
    BlockIn,
    MemberCreateIn,
    MemberListQuery,
    NoticeCreateIn,
    NoticeListQuery,
    NoticePatchIn,
    ResetPasswordIn,
    StatsMemberDetailQuery,
    StatsMemberSearchQuery,
    StatsRangeQuery,
)
from chalicelib.services import (
    auth_service,
    member_service,
    notice_service,
    setting_service,
    stats_service,
)
from chalicelib.services.setting_service import SettingKey

bp = blueprint(__name__)


def _member_uuid(raw: str) -> uuid.UUID:
    parsed = parse_uuid(raw)
    if parsed is None:
        raise AppError(ErrorCode.MEMBER_NOT_FOUND)
    return parsed


def _date_or_422(raw: str, field: str) -> _dt.date:
    parsed = parse_date(raw)
    if parsed is None:
        raise AppError(ErrorCode.VALIDATION_FAILED, doc_hint=f"{field} 형식이 날짜가 아닙니다")
    return parsed


# ── 회원 (API 문서 §9.13–§9.16) ────────────────────────────────────────────


@route(bp, "/admin/members")
@require(CURATOR)
@paginated(PAGE, default_limit=MEMBER_LIST_DEFAULT_LIMIT, max_limit=PAGINATION_MAX_LIMIT)
@query(MemberListQuery)
def list_members(pagination: PageParams, params: MemberListQuery) -> Result:
    context = ctx_module.current()
    members, total = member_service.list_members(
        context.db,
        query=params.query,
        status=params.status,
        notify=params.notify,
        sort=params.sort,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Result(
        data={
            "members": members,
            "signup_open": setting_service.get_bool(context.db, SettingKey.SIGNUP_OPEN),
        },
        pagination=page_meta(
            limit=pagination.limit,
            count=len(members),
            page=pagination.page,
            total_count=total,
        ),
        cache_control=CACHE_NO_STORE,
    )


@route(bp, "/admin/members", methods=("POST",))
@require(CURATOR)
@audited("member.create")
@body(MemberCreateIn)
def create_member(payload: MemberCreateIn) -> Result:
    """대행 가입. **가입 잠금 상태에서도 생성 가능하다** — 잠금은 외부 가입을 막는 장치다."""
    context = ctx_module.current()
    created = auth_service.signup(
        context.db,
        phone=payload.phone,
        password=payload.initial_password,
        name=payload.name,
        created_via=auth_service.VIA_CURATOR,
    )
    member = member_service.member_item(context.db, created.id)
    context.audit_entries.append(
        {"target_type": "member", "target_id": str(created.id), "summary": "대행 가입"}
    )
    return Result(data={"member": member}, status=201, cache_control=CACHE_NO_STORE)


@route(bp, "/admin/members/{member_id}/block", methods=("POST",))
@require(CURATOR)
@audited("member.block")
@body(BlockIn)
def block_member(member_id: str, payload: BlockIn) -> Result:
    """이미 같은 상태면 그대로 200이다(멱등)."""
    context = ctx_module.current()
    member = member_service.set_blocked(
        context.db, _member_uuid(member_id), blocked=True, reason=payload.reason
    )
    context.audit_entries.append({"target_type": "member", "target_id": member_id, "summary": "회원 차단"})
    return Result(data={"member": member}, cache_control=CACHE_NO_STORE)


@route(bp, "/admin/members/{member_id}/unblock", methods=("POST",))
@require(CURATOR)
@audited("member.unblock")
def unblock_member(member_id: str) -> Result:
    context = ctx_module.current()
    member = member_service.set_blocked(context.db, _member_uuid(member_id), blocked=False)
    context.audit_entries.append({"target_type": "member", "target_id": member_id, "summary": "차단 해제"})
    return Result(data={"member": member}, cache_control=CACHE_NO_STORE)


@route(bp, "/admin/members/{member_id}/reset-password", methods=("POST",))
@require(CURATOR)
@audited("member.reset_password")
@body(ResetPasswordIn)
def reset_member_password(member_id: str, payload: ResetPasswordIn) -> Result:
    """`token_version+1`로 해당 회원의 모든 세션을 무효화한다."""
    context = ctx_module.current()
    member = member_service.reset_password(
        context.db, _member_uuid(member_id), new_password=payload.new_password
    )
    # 감사 기록에 비밀번호는 남기지 않는다.
    context.audit_entries.append(
        {"target_type": "member", "target_id": member_id, "summary": "비밀번호 초기화"}
    )
    return Result(data={"member": member}, cache_control=CACHE_NO_STORE)


# ── 전역 설정 (API 문서 §9.17) ─────────────────────────────────────────────


@route(bp, "/admin/settings")
@require(CURATOR)
def get_settings() -> Result:
    context = ctx_module.current()
    return Result(data={"settings": setting_service.list_all(context.db)}, cache_control=CACHE_NO_STORE)


@route(bp, "/admin/settings", methods=("PATCH",))
@require(CURATOR)
@audited("setting.update")
@body(AppSettingsPatchIn)
def patch_settings(payload: AppSettingsPatchIn) -> Result:
    """변경할 키만 담는다. 가입 잠금도 이 경로로 조작한다."""
    context = ctx_module.current()
    settings = setting_service.update_many(context.db, payload.settings, actor_id=context.actor_id)
    context.audit_entries.append(
        {
            "target_type": "app_setting",
            "target_id": ",".join(sorted(payload.settings)),
            "summary": "전역 설정 변경",
            "changes": {"after": payload.settings},
        }
    )
    return Result(data={"settings": settings}, cache_control=CACHE_NO_STORE)


# ── 공지 (API 문서 §9.18) ──────────────────────────────────────────────────


@route(bp, "/admin/notices")
@require(CURATOR)
@paginated(PAGE, default_limit=NOTICE_LIST_DEFAULT_LIMIT, max_limit=PAGINATION_MAX_LIMIT)
@query(NoticeListQuery)
def list_notices(pagination: PageParams, params: NoticeListQuery) -> Result:
    context = ctx_module.current()
    notices, total = notice_service.list_notices(
        context.db,
        include_past=params.include_past,
        today=context.today,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Result(
        data={"notices": notices},
        pagination=page_meta(
            limit=pagination.limit,
            count=len(notices),
            page=pagination.page,
            total_count=total,
        ),
        cache_control=CACHE_NO_STORE,
    )


@route(bp, "/admin/notices", methods=("POST",))
@require(CURATOR)
@audited("notice.create")
@body(NoticeCreateIn)
def create_notice(payload: NoticeCreateIn) -> Result:
    context = ctx_module.current()
    notice = notice_service.create_notice(
        context.db,
        starts_on=_date_or_422(payload.starts_on, "starts_on"),
        ends_on=_date_or_422(payload.ends_on, "ends_on"),
        body=payload.body,
        actor_id=context.actor_id,
    )
    context.audit_entries.append(
        {"target_type": "notice", "target_id": notice["id"], "summary": "휴관 공지 등록"}
    )
    return Result(data={"notice": notice}, status=201, cache_control=CACHE_NO_STORE)


@route(bp, "/admin/notices/{notice_id}", methods=("PATCH",))
@require(CURATOR)
@audited("notice.update")
@body(NoticePatchIn)
def update_notice(notice_id: str, payload: NoticePatchIn) -> Result:
    context = ctx_module.current()
    parsed = parse_uuid(notice_id)
    if parsed is None:
        raise AppError(ErrorCode.NOT_FOUND, details={"resource": "notice"})
    notice = notice_service.update_notice(
        context.db,
        parsed,
        starts_on=_date_or_422(payload.starts_on, "starts_on") if payload.starts_on else None,
        ends_on=_date_or_422(payload.ends_on, "ends_on") if payload.ends_on else None,
        body=payload.body,
    )
    context.audit_entries.append(
        {"target_type": "notice", "target_id": notice_id, "summary": "휴관 공지 수정"}
    )
    return Result(data={"notice": notice}, cache_control=CACHE_NO_STORE)


@route(bp, "/admin/notices/{notice_id}", methods=("DELETE",))
@require(CURATOR)
@audited("notice.cancel")
def cancel_notice(notice_id: str) -> Result:
    """실제로는 `is_active=false` 처리다 — 무엇을 언제 걸었는지가 남는다."""
    context = ctx_module.current()
    parsed = parse_uuid(notice_id)
    if parsed is None:
        raise AppError(ErrorCode.NOT_FOUND, details={"resource": "notice"})
    notice_service.cancel_notice(context.db, parsed)
    context.audit_entries.append(
        {"target_type": "notice", "target_id": notice_id, "summary": "휴관 공지 취소"}
    )
    return Result(data={}, cache_control=CACHE_NO_STORE)


# ── 통계 (v1.1, API 문서 §9.19) ────────────────────────────────────────────


@route(bp, "/admin/stats/daily")
@require(CURATOR)
@query(StatsRangeQuery)
def stats_daily(params: StatsRangeQuery) -> Result:
    context = ctx_module.current()
    to_date = _date_or_422(params.to, "to") if params.to else context.today
    from_date = (
        _date_or_422(params.from_, "from")
        if params.from_
        else to_date - _dt.timedelta(days=STATS_DAILY_DAYS - 1)
    )
    if to_date < from_date:
        raise AppError(ErrorCode.VALIDATION_FAILED, doc_hint="to 는 from 보다 빠를 수 없습니다")
    if (to_date - from_date).days + 1 > STATS_MAX_RANGE_DAYS:
        raise AppError(ErrorCode.VALIDATION_FAILED, doc_hint="조회 범위가 너무 넓습니다")

    return Result(
        data={"days": stats_service.daily(context.db, from_date=from_date, to_date=to_date)},
        cache_control=CACHE_NO_STORE,
    )


@route(bp, "/admin/stats/members")
@require(CURATOR)
@query(StatsMemberSearchQuery)
def stats_member_search(params: StatsMemberSearchQuery) -> Result:
    context = ctx_module.current()
    return Result(
        data={"members": stats_service.search_members(context.db, query=params.query)},
        cache_control=CACHE_NO_STORE,
    )


@route(bp, "/admin/stats/members/{member_id}")
@require(CURATOR)
@query(StatsMemberDetailQuery)
def stats_member_detail(member_id: str, params: StatsMemberDetailQuery) -> Result:
    context = ctx_module.current()
    days = min(params.days or STATS_MEMBER_DEFAULT_DAYS, STATS_MEMBER_MAX_DAYS)
    from_date = context.today - _dt.timedelta(days=days - 1)
    return Result(
        data=stats_service.member_detail(
            context.db,
            user_id=_member_uuid(member_id),
            from_date=from_date,
            to_date=context.today,
        ),
        cache_control=CACHE_NO_STORE,
    )
