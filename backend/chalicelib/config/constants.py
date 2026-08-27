"""사양으로 고정된 상수.

여기 있는 값은 **배포로도 바뀌지 않는다.** 문서가 값을 규정하고 있고, 값이 바뀌면
프런트엔드 계약도 함께 바뀌어야 하는 것들이다.

구분 기준 (백엔드 문서 §8.1, DB 문서 §4.9)
  * 사양 고정값        → 이 파일
  * 배포로 바뀌는 값    → 환경변수 (`config/settings.py`)
  * 운영 중 조정되는 값 → `app_setting` 테이블 (`services/setting_service.py`)
"""

from __future__ import annotations

from typing import Final

# ── API 규약 (API 문서 §2) ──────────────────────────────────────────────────
API_VERSION: Final = "v1"
API_PREFIX: Final = "/api"

REQUEST_ID_HEADER: Final = "X-Request-Id"

#: 변경 메서드에 요구하는 커스텀 헤더 (API 문서 §2.7)
CSRF_HEADER_NAME: Final = "X-Requested-With"
CSRF_HEADER_VALUE: Final = "gallery-k"

#: 세션 쿠키. 이름·속성이 프런트엔드와의 계약이다 (API 문서 §2.7)
SESSION_COOKIE_NAME: Final = "gk_session"
SESSION_COOKIE_PATH: Final = "/"
SESSION_COOKIE_MAX_AGE_SECONDS: Final = 7_776_000  # 90일
SESSION_COOKIE_SAMESITE: Final = "Lax"

#: 만료가 이 값 이내로 남으면 응답에서 자동 재발급한다 (슬라이딩 세션)
SESSION_SLIDING_RENEW_WITHIN_SECONDS: Final = 2_592_000  # 30일

#: 소셜 인가 왕복용 임시 쿠키 (소셜 문서 §4). 둘 다 HttpOnly·SameSite=Lax·TTL 10분이며
#: 쓰는 즉시 삭제된다. 세션 쿠키와 이름 공간을 나눠 두어 혼동을 막는다.
OAUTH_STATE_COOKIE_NAME: Final = "gk_oauth"
OAUTH_LINK_COOKIE_NAME: Final = "gk_oauth_link"

MUTATING_METHODS: Final = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# ── 시간 (DB 문서 §2) ──────────────────────────────────────────────────────
KST_TZ_NAME: Final = "Asia/Seoul"

#: 요일 표시 라벨. `2026. 08. 27. 목` 의 마지막 한 글자 (API 문서 §6.1)
KST_WEEKDAY_LABELS: Final = ("월", "화", "수", "목", "금", "토", "일")

# ── 도메인 (PRD §4.1, §6.13) ───────────────────────────────────────────────
#: 한 전시의 그림 수. 슬롯 번호는 1..ARTWORK_COUNT
ARTWORK_COUNT: Final = 12
ARTWORK_POSITION_MIN: Final = 1
ARTWORK_POSITION_MAX: Final = ARTWORK_COUNT

#: 알림 시각 선택 범위 (PRD §6.13, API 문서 §8.2)
NOTIFY_AT_MIN: Final = "05:00"
NOTIFY_AT_MAX: Final = "11:00"

#: 큐레이터 연장 알림을 보내는 연속 연장 일수 (PRD §6.12)
CURATOR_CARRYOVER_ALERT_DAYS_DEFAULT: Final = 2

# ── 입력 길이 상한 (API 문서 §9.4·§9.5·§9.18, 프런트 constants.ts LIMITS) ──
LIMIT_EXHIBITION_TITLE: Final = 20
LIMIT_EXHIBITION_THEME: Final = 500
LIMIT_ARTWORK_TITLE: Final = 20
LIMIT_ARTWORK_ARTIST: Final = 40
LIMIT_ARTWORK_YEAR_TEXT: Final = 20
LIMIT_ARTWORK_DESCRIPTION: Final = 300
LIMIT_ARTWORK_COLLECTION: Final = 60
LIMIT_ARTWORK_SOURCE_URL: Final = 500
LIMIT_MEMBER_NAME: Final = 20
LIMIT_NOTICE_BODY: Final = 300
LIMIT_HIDDEN_REASON: Final = 200
LIMIT_BLOCKED_REASON: Final = 200
LIMIT_SEARCH_QUERY: Final = 20
LIMIT_UPLOAD_FILENAME: Final = 200

PASSWORD_MIN_LENGTH: Final = 8
PASSWORD_MAX_LENGTH: Final = 64

#: 로그인 ID. 하이픈 제거 후의 형식 (API 문서 §6.3)
PHONE_PATTERN: Final = r"^01[0-9]{8,9}$"

# ── 페이지네이션 (API 문서 §2.4) ───────────────────────────────────────────
PAGINATION_MAX_LIMIT: Final = 100
ARCHIVE_DEFAULT_LIMIT: Final = 30
ARCHIVE_MAX_LIMIT: Final = 30
CALENDAR_DEFAULT_LIMIT: Final = 7
CALENDAR_MAX_LIMIT: Final = 30
CALENDAR_MAX_RANGE_DAYS: Final = 90
MEMBER_LIST_DEFAULT_LIMIT: Final = 30
NOTICE_LIST_DEFAULT_LIMIT: Final = 30
#: 관람 현황 기본 조회 범위 — B-1은 최근 7일, B-1-1은 30일 (UX 문서 §3.17)
STATS_DAILY_DAYS: Final = 7
STATS_MAX_RANGE_DAYS: Final = 90
STATS_MEMBER_DEFAULT_DAYS: Final = 30
STATS_MEMBER_MAX_DAYS: Final = 90
STATS_MEMBER_SEARCH_LIMIT: Final = 20

# ── 업로드·이미지 (API 문서 §9.8, PRD §8.2) ────────────────────────────────
UPLOAD_MAX_BYTES: Final = 20 * 1024 * 1024
UPLOAD_ALLOWED_MIME: Final = ("image/jpeg", "image/png", "image/webp")
UPLOAD_MIME_EXTENSIONS: Final = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
UPLOAD_URL_TTL_SECONDS: Final = 900  # 15분

#: 파생 이미지 규격 (PRD §8.2)
IMAGE_THUMB_SIZE: Final = 400
IMAGE_THUMB_QUALITY: Final = 80
IMAGE_DISPLAY_LONG_EDGE: Final = 1600
IMAGE_DISPLAY_QUALITY: Final = 85
IMAGE_LQIP_WIDTH: Final = 16
IMAGE_LQIP_QUALITY: Final = 40
#: 디코딩 폭탄 방어. 원본 픽셀 수 상한
IMAGE_MAX_PIXELS: Final = 60_000_000

#: 오브젝트 키 접두. 착지 경로와 확정 경로를 나눈다 (백엔드 문서 §10.2)
MEDIA_UPLOAD_PREFIX: Final = "uploads"
MEDIA_ARTWORK_PREFIX: Final = "artworks"

# ── 시도 제한 (API 문서 §2.10) ─────────────────────────────────────────────
THROTTLE_LOGIN_MAX_FAILURES: Final = 5
THROTTLE_LOGIN_LOCK_SECONDS: Final = 600  # 10분
THROTTLE_SIGNUP_MAX_ATTEMPTS: Final = 10
THROTTLE_SIGNUP_WINDOW_SECONDS: Final = 3_600
THROTTLE_PASSWORD_RESET_MAX_ATTEMPTS: Final = 5
THROTTLE_PASSWORD_RESET_WINDOW_SECONDS: Final = 3_600
THROTTLE_PASSWORD_RESET_RESEND_SECONDS: Final = 60
THROTTLE_UPLOAD_URL_MAX_ATTEMPTS: Final = 60
THROTTLE_UPLOAD_URL_WINDOW_SECONDS: Final = 600

# ── 비밀번호 재설정 (v1.1, API 문서 §6.8) ──────────────────────────────────
RESET_CODE_TTL_SECONDS: Final = 180
RESET_CODE_MAX_ATTEMPTS: Final = 5

# ── 알림 (PRD §6.12, API 문서 §11.3) ───────────────────────────────────────
NOTIFICATION_SEND_BATCH_SIZE: Final = 100
NOTIFICATION_MAX_ATTEMPTS: Final = 3
PUSH_FAILURE_DEACTIVATE_THRESHOLD: Final = 5
PUSH_TTL_SECONDS: Final = 3_600
#: 같은 날 배너가 쌓이지 않게 하는 태그 (백엔드 문서 §11)
PUSH_TAG_MORNING: Final = "gallery-k-morning"
PUSH_TAG_CURATOR: Final = "gallery-k-curator"

# ── 캐시 (API 문서 §2.9) ───────────────────────────────────────────────────
CACHE_LANDING: Final = "private, max-age=60"
CACHE_EXHIBITION_CURRENT: Final = "private, max-age=0, must-revalidate"
CACHE_EXHIBITION_BY_DATE: Final = "private, max-age=300"
CACHE_NO_STORE: Final = "no-store"

#: 설정 캐시 TTL. 인스턴스가 여럿이므로 이만큼 전파가 늦다 (백엔드 문서 §8.5)
SETTING_CACHE_TTL_SECONDS: Final = 60

# ── 보안 헤더 (백엔드 문서 §13) ────────────────────────────────────────────
SECURITY_HEADERS: Final = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), interest-cohort=()",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Robots-Tag": "noindex, nofollow, noarchive",
}
