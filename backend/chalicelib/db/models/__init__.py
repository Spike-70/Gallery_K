"""테이블 정의 11종 (DB 문서 §4).

이 패키지를 import 하면 `metadata`가 전 테이블을 담는다. Alembic과 테스트가
그 사실에 의존하므로, 새 모델은 반드시 여기에 등록한다.
"""

from chalicelib.db.models.base import (
    NAMING_CONVENTION,
    TimestampMixin,
    UUIDPKMixin,
    VersionMixin,
    metadata,
)
from chalicelib.db.models.exhibition import Artwork, Exhibition
from chalicelib.db.models.ops import AppSetting, AuditLog, Notice, NotificationLog
from chalicelib.db.models.user import AppUser, AuthThrottle, PushSubscription
from chalicelib.db.models.viewlog import ArtworkViewLog, ViewLog

#: 테이블 11종. 계약 테스트가 이 목록과 metadata를 대조한다.
ALL_MODELS = (
    AppUser,
    AuthThrottle,
    PushSubscription,
    Exhibition,
    Artwork,
    ViewLog,
    ArtworkViewLog,
    Notice,
    AppSetting,
    NotificationLog,
    AuditLog,
)

__all__ = [
    "ALL_MODELS",
    "NAMING_CONVENTION",
    "AppSetting",
    "AppUser",
    "Artwork",
    "ArtworkViewLog",
    "AuditLog",
    "AuthThrottle",
    "Exhibition",
    "Notice",
    "NotificationLog",
    "PushSubscription",
    "TimestampMixin",
    "UUIDPKMixin",
    "VersionMixin",
    "ViewLog",
    "metadata",
]
