"""열거형 — **단일 진실 원천** (DB 문서 §5).

프런트엔드 `shared/types/enums.ts`가 이 파일을 미러링한다. 값을 바꿀 때 두 파일을
함께 바꾼다(교차검토 §4 계약 표).

DB에는 네이티브 ENUM을 쓰지 않는다. `text` + `CHECK`이며, 값 추가가 마이그레이션
한 줄로 끝나기 때문이다. `VALUES` 튜플이 그 CHECK의 원천이다.
"""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    VIEWER = "viewer"
    CURATOR = "curator"


class FontScale(StrEnum):
    NORMAL = "normal"
    LARGE = "large"


class CreatedVia(StrEnum):
    SELF = "self"
    CURATOR = "curator"


class ImageStatus(StrEnum):
    EMPTY = "empty"
    UPLOADING = "uploading"
    READY = "ready"
    FAILED = "failed"


class NotificationKind(StrEnum):
    #: 예약 발송 — 사용자의 알림 시각에 맞춰 나간다
    MORNING_EXHIBITION = "morning_exhibition"
    #: 알림 시각이 이미 지난 뒤 발행된 경우. 도달률을 사후에 분리 관측한다(교차검토 X-16)
    LATE_PUBLISH = "late_publish"
    #: 연장 2일 연속 시 큐레이터에게 1회 (PRD §6.12)
    CURATOR_CARRYOVER = "curator_carryover"
    #: 신규 가입 시 큐레이터에게 (PRD §6.4)
    CURATOR_SIGNUP = "curator_signup"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    SKIPPED = "skipped"
    FAILED = "failed"


class NotificationSkipReason(StrEnum):
    """보내지 않은 이유는 남아야 문의에 답할 수 있다 (DB 문서 §4.10)."""

    CUTOFF_PASSED = "cutoff_passed"
    NOTIFY_DISABLED = "notify_disabled"
    NO_SUBSCRIPTION = "no_subscription"
    USER_BLOCKED = "user_blocked"
    NOTICE_PERIOD = "notice_period"
    CARRIED_OVER = "carried_over"


class ThrottleScope(StrEnum):
    LOGIN = "login"
    SIGNUP = "signup"
    PASSWORD_RESET = "password_reset"
    #: DB 문서 §5 목록에는 없으나 API 문서 §2.10이 업로드 URL 발급 한도(60회/10분)를
    #: 규정한다. 시도 상태를 담을 스코프가 필요해 추가했다.
    UPLOAD_URL = "upload_url"


class PushPlatform(StrEnum):
    IOS = "ios"
    ANDROID = "android"
    DESKTOP = "desktop"
    UNKNOWN = "unknown"


class ImageErrorCode(StrEnum):
    """이미지 처리 실패 사유. 재업로드로만 복구한다 (백엔드 문서 §10.1)."""

    NOT_AN_IMAGE = "not_an_image"
    MIME_MISMATCH = "mime_mismatch"
    TOO_LARGE = "too_large"
    TOO_MANY_PIXELS = "too_many_pixels"
    DECODE_FAILED = "decode_failed"
    OBJECT_MISSING = "object_missing"
    PROCESSING_FAILED = "processing_failed"


# ── 컬럼이 아닌 파생 열거형 ────────────────────────────────────────────────
# DB에 저장되지 않는다. API 응답에서 서버가 계산해 내리는 값이며, 프런트가 날짜 비교로
# 재구현하면 규칙이 두 곳에 존재하게 된다(API 문서 §3.9).


class ExhibitionDayStatus(StrEnum):
    PUBLISHED = "published"
    CARRIED_OVER = "carried_over"
    EMPTY = "empty"


class EditMode(StrEnum):
    CREATE = "create"
    EDIT = "edit"
    CARRY_DRAFT = "carry_draft"
    LOCKED = "locked"


class PushStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    NONE = "none"


def values(enum_type: type[StrEnum]) -> tuple[str, ...]:
    """CHECK 제약과 스키마 검증이 함께 참조하는 값 목록."""
    return tuple(member.value for member in enum_type)
