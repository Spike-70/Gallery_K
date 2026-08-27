"""관리자 전시 API (API 문서 §9.1–§9.12).

전 엔드포인트 `CURATOR` 권한, `Cache-Control: no-store`, 변경 계열은 `audit_log` 기록을
남긴다. 세 가지 모두 데코레이터가 강제하고 계약 테스트가 누락을 검출한다.
"""

from __future__ import annotations

import datetime as _dt

from chalicelib.api.routes._base import blueprint, route
from chalicelib.config.constants import (
    ARTWORK_POSITION_MAX,
    ARTWORK_POSITION_MIN,
    CACHE_NO_STORE,
    CALENDAR_DEFAULT_LIMIT,
    CALENDAR_MAX_LIMIT,
    CALENDAR_MAX_RANGE_DAYS,
)
from chalicelib.core import context as ctx_module
from chalicelib.core.decorators import (
    CURATOR,
    audited,
    body,
    current_request,
    paginated,
    query,
    require,
    throttled,
)
from chalicelib.core.envelope import Result
from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.ids import parse_uuid
from chalicelib.core.pagination import CURSOR, Cursor, CursorParams, cursor_meta
from chalicelib.core.timeutil import parse_date
from chalicelib.schemas.admin import (
    ArtworkSaveIn,
    CalendarQuery,
    CarryDraftIn,
    ExhibitionSaveIn,
    HideIn,
    ImageCompleteIn,
    ReorderIn,
    UploadUrlsIn,
)
from chalicelib.services import (
    exhibition_admin_service,
    exhibition_service,
    media_service,
    setting_service,
    throttle_service,
)
from chalicelib.services.setting_service import SettingKey

bp = blueprint(__name__)

#: 과거 스크롤의 바닥. 무한히 거슬러 올라가지 않는다.
PAST_SCROLL_LIMIT_DAYS = 365


def _date_or_400(raw: str) -> _dt.date:
    parsed = parse_date(raw)
    if parsed is None:
        raise AppError(ErrorCode.VALIDATION_FAILED, doc_hint=f"날짜 형식이 아닙니다: {raw}")
    return parsed


@route(bp, "/admin/summary")
@require(CURATOR)
def summary() -> Result:
    context = ctx_module.current()
    return Result(
        data=exhibition_admin_service.summary(context.db, today=context.today),
        cache_control=CACHE_NO_STORE,
    )


@route(bp, "/admin/exhibitions/calendar")
@require(CURATOR)
@paginated(CURSOR, default_limit=CALENDAR_DEFAULT_LIMIT, max_limit=CALENDAR_MAX_LIMIT)
@query(CalendarQuery)
def calendar(pagination: CursorParams, params: CalendarQuery) -> Result:
    """기본은 오늘을 맨 위로 하는 7일치. 위로 스크롤하면 과거를 이어 받는다 (PRD §6.9)."""
    context = ctx_module.current()
    today = context.today
    # 기본 조회 일수는 운영 중 조정되는 값이다 (DB 문서 §4.9 `admin_calendar_days`).
    # 클라이언트가 `limit`을 주면 그쪽이 우선한다.
    window = pagination.limit
    if current_request().query_params is None or "limit" not in (current_request().query_params or {}):
        window = setting_service.get_int(context.db, SettingKey.ADMIN_CALENDAR_DAYS)

    if params.direction == "past":
        anchor = _date_or_400(str(pagination.cursor.key)) if pagination.cursor else today
        to_date = anchor - _dt.timedelta(days=1)
        from_date = to_date - _dt.timedelta(days=window - 1)
        floor = today - _dt.timedelta(days=PAST_SCROLL_LIMIT_DAYS)
        has_more = from_date > floor
        next_cursor = Cursor(key=from_date.isoformat(), id="").encode() if has_more else None
    else:
        from_date = _date_or_400(params.from_) if params.from_ else today
        to_date = _date_or_400(params.to) if params.to else from_date + _dt.timedelta(days=window - 1)
        if to_date < from_date:
            raise AppError(ErrorCode.VALIDATION_FAILED, doc_hint="to 는 from 보다 빠를 수 없습니다")
        if (to_date - from_date).days + 1 > CALENDAR_MAX_RANGE_DAYS:
            raise AppError(ErrorCode.VALIDATION_FAILED, doc_hint="조회 범위가 너무 넓습니다")
        has_more = False
        next_cursor = None

    days = exhibition_admin_service.calendar(context.db, from_date=from_date, to_date=to_date, today=today)
    return Result(
        data={"days": days},
        pagination=cursor_meta(
            limit=window,
            count=len(days),
            has_more=has_more,
            next_cursor=next_cursor,
        ),
        cache_control=CACHE_NO_STORE,
    )


@route(bp, "/admin/exhibitions/{date}")
@require(CURATOR)
def exhibition_detail(date: str) -> Result:
    """행이 없어도 빈 12슬롯과 `edit_mode`를 계산해 반환한다 — 부재 오류가 없다."""
    context = ctx_module.current()
    return Result(
        data=exhibition_admin_service.admin_detail(
            context.db, exhibition_date=_date_or_400(date), today=context.today
        ),
        cache_control=CACHE_NO_STORE,
    )


@route(bp, "/admin/exhibitions/{date}", methods=("PUT",))
@require(CURATOR)
@audited("exhibition.save")
@body(ExhibitionSaveIn)
def save_exhibition(date: str, payload: ExhibitionSaveIn) -> Result:
    context = ctx_module.current()
    exhibition_date = _date_or_400(date)
    result = exhibition_admin_service.save_title_theme(
        context.db,
        exhibition_date=exhibition_date,
        title=payload.title,
        theme=payload.theme,
        version=payload.version,
        today=context.today,
        actor_id=context.actor_id,
    )
    context.audit_entries.append(
        {
            "target_type": "exhibition",
            "target_id": date,
            "summary": "제목·테마 저장",
            "changes": {"after": {"title": payload.title, "has_theme": bool(payload.theme)}},
        }
    )
    return Result(data=result, cache_control=CACHE_NO_STORE)


@route(bp, "/admin/exhibitions/{date}/preview")
@require(CURATOR)
def preview(date: str) -> Result:
    """관람자 화면과 동일한 스키마. 미발행 상태여도 반환한다."""
    context = ctx_module.current()
    data = exhibition_service.preview_detail(context.db, exhibition_date=_date_or_400(date))
    if data is None:
        raise AppError(ErrorCode.EXHIBITION_NOT_FOUND, details={"date": date})
    return Result(data=data, cache_control=CACHE_NO_STORE)


@route(bp, "/admin/exhibitions/{date}/hide", methods=("POST",))
@require(CURATOR)
@audited("exhibition.hide")
@body(HideIn)
def hide_exhibition(date: str, payload: HideIn) -> Result:
    context = ctx_module.current()
    result = exhibition_admin_service.hide(
        context.db, exhibition_date=_date_or_400(date), reason=payload.reason, today=context.today
    )
    context.audit_entries.append({"target_type": "exhibition", "target_id": date, "summary": "전시 숨김"})
    return Result(data=result, cache_control=CACHE_NO_STORE)


@route(bp, "/admin/exhibitions/{date}/unhide", methods=("POST",))
@require(CURATOR)
@audited("exhibition.unhide")
def unhide_exhibition(date: str) -> Result:
    context = ctx_module.current()
    result = exhibition_admin_service.unhide(
        context.db, exhibition_date=_date_or_400(date), today=context.today
    )
    context.audit_entries.append(
        {"target_type": "exhibition", "target_id": date, "summary": "전시 숨김 해제"}
    )
    return Result(data=result, cache_control=CACHE_NO_STORE)


@route(bp, "/admin/exhibitions/{date}/carry-draft", methods=("POST",))
@require(CURATOR)
@audited("exhibition.carry_draft")
@body(CarryDraftIn)
def carry_draft(date: str, payload: CarryDraftIn) -> Result:
    """과거 미발행일의 드래프트를 오늘 날짜로 **이동**한다."""
    context = ctx_module.current()
    result = exhibition_admin_service.carry_draft(
        context.db,
        from_date=_date_or_400(date),
        today=context.today,
        actor_id=context.actor_id,
    )
    context.audit_entries.append(
        {
            "target_type": "exhibition",
            "target_id": date,
            "summary": f"이어쓰기 → {result['to_date']}",
        }
    )
    return Result(data=result, cache_control=CACHE_NO_STORE)


# ── 그림 슬롯 ──────────────────────────────────────────────────────────────


def _position_or_400(raw: str) -> int:
    try:
        position = int(raw)
    except ValueError as exc:
        raise AppError(ErrorCode.VALIDATION_FAILED, doc_hint="자리 번호가 정수가 아닙니다") from exc
    if not ARTWORK_POSITION_MIN <= position <= ARTWORK_POSITION_MAX:
        raise AppError(ErrorCode.VALIDATION_FAILED, doc_hint="자리 번호가 범위를 벗어났습니다")
    return position


@route(bp, "/admin/exhibitions/{date}/artworks/{position}", methods=("PUT",))
@require(CURATOR)
@audited("artwork.save")
@body(ArtworkSaveIn)
def save_artwork(date: str, position: str, payload: ArtworkSaveIn) -> Result:
    context = ctx_module.current()
    slot = _position_or_400(position)
    result = exhibition_admin_service.save_artwork_slot(
        context.db,
        exhibition_date=_date_or_400(date),
        position=slot,
        values=payload.model_dump(exclude={"version"}),
        expected_version=payload.version,
        today=context.today,
        actor_id=context.actor_id,
    )
    context.audit_entries.append(
        {"target_type": "artwork", "target_id": f"{date}#{slot}", "summary": "그림 저장"}
    )
    return Result(data=result, cache_control=CACHE_NO_STORE)


@route(bp, "/admin/exhibitions/{date}/artworks/{position}", methods=("DELETE",))
@require(CURATOR)
@audited("artwork.clear")
def clear_artwork(date: str, position: str) -> Result:
    """발행된 전시에서 슬롯을 비워도 `is_published`는 유지된다 (PRD §6.10)."""
    context = ctx_module.current()
    slot = _position_or_400(position)
    result = exhibition_admin_service.clear_artwork_slot(
        context.db,
        exhibition_date=_date_or_400(date),
        position=slot,
        today=context.today,
        actor_id=context.actor_id,
    )
    context.audit_entries.append(
        {"target_type": "artwork", "target_id": f"{date}#{slot}", "summary": "슬롯 비우기"}
    )
    return Result(data=result, cache_control=CACHE_NO_STORE)


@route(bp, "/admin/exhibitions/{date}/artworks/reorder", methods=("POST",))
@require(CURATOR)
@audited("artwork.reorder")
@body(ReorderIn)
def reorder_artworks(date: str, payload: ReorderIn) -> Result:
    context = ctx_module.current()
    for item in payload.order:
        if parse_uuid(item.artwork_id) is None:
            raise AppError(ErrorCode.ARTWORK_NOT_FOUND)

    result = exhibition_admin_service.reorder_artwork_slots(
        context.db,
        exhibition_date=_date_or_400(date),
        order=[item.model_dump() for item in payload.order],
    )
    context.audit_entries.append({"target_type": "exhibition", "target_id": date, "summary": "순서 변경"})
    return Result(data=result, cache_control=CACHE_NO_STORE)


# ── 업로드 (API 문서 §9.8·§9.9) ────────────────────────────────────────────


@route(bp, "/admin/exhibitions/{date}/artworks/upload-urls", methods=("POST",))
@require(CURATOR)
@audited("artwork.upload_urls")
@body(UploadUrlsIn)
@throttled(throttle_service.UPLOAD_URL, count_attempts=True)
def upload_urls(date: str, payload: UploadUrlsIn) -> Result:
    """20MB 파일은 API Gateway를 통과할 수 없으므로 클라이언트가 S3로 직접 올린다."""
    context = ctx_module.current()
    uploads = media_service.issue_upload_credentials(
        context.db,
        exhibition_date=_date_or_400(date),
        files=[
            media_service.UploadRequest(
                position=item.position,
                filename=item.filename,
                content_type=item.content_type,
                size_bytes=item.size_bytes,
            )
            for item in payload.files
        ],
        overwrite=payload.overwrite,
    )
    context.audit_entries.append(
        {
            "target_type": "exhibition",
            "target_id": date,
            "summary": f"업로드 자격 {len(uploads)}건 발급",
        }
    )
    return Result(data={"uploads": uploads}, cache_control=CACHE_NO_STORE)


@route(bp, "/admin/artworks/{artwork_id}/image/complete", methods=("POST",))
@require(CURATOR)
@audited("artwork.image_complete")
@body(ImageCompleteIn)
def complete_image(artwork_id: str, payload: ImageCompleteIn) -> Result:
    """서버가 **이 요청 안에서 동기로** 검증·변환하고 `ready`로 전환한 뒤 응답한다."""
    context = ctx_module.current()
    parsed = parse_uuid(artwork_id)
    if parsed is None:
        raise AppError(ErrorCode.ARTWORK_NOT_FOUND)

    result = media_service.complete_upload(
        context.db,
        artwork_id=parsed,
        object_key=payload.object_key,
        today=context.today,
    )
    context.audit_entries.append(
        {
            "target_type": "artwork",
            "target_id": artwork_id,
            "summary": f"이미지 처리 {result['image_status']}",
        }
    )
    return Result(data=result, cache_control=CACHE_NO_STORE)
