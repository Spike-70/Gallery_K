"""환경변수를 읽는 **유일한 지점** (백엔드 문서 §8.1).

  * 로컬 개발: `backend/.env` (`.env.example`을 복사해 만든다. 커밋 금지)
  * 배포:      Chalice 스테이지 환경변수

`.env`가 없어도 배포 환경에서 동작해야 하며, 필수 값이 비어 있으면 **기동 시점에
실패**한다 — 요청 처리 중에 발견되지 않게 한다.

다른 모듈에서 `os.environ` 직접 접근은 ruff 규칙(TID251)으로 금지되어 있다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

AppEnv = Literal["dev", "prod"]

_BACKEND_ROOT: Final = Path(__file__).resolve().parents[2]


class ConfigError(RuntimeError):
    """필수 환경변수 누락·형식 오류. 기동을 중단시킨다."""


def _load_dotenv() -> None:
    """로컬 개발용 `.env` 로드. 배포 환경에는 파일이 없고, 없어도 정상이다."""
    dotenv_path = _BACKEND_ROOT / ".env"
    if not dotenv_path.is_file():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - 배포 패키지에는 항상 포함된다
        return
    load_dotenv(dotenv_path, override=False)


def _get(key: str, default: str | None = None) -> str | None:
    value = os.environ.get(key, default)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _require(key: str) -> str:
    value = _get(key)
    if value is None:
        raise ConfigError(f"필수 환경변수가 없습니다: {key}")
    return value


def _get_int(key: str, default: int) -> int:
    raw = _get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"정수여야 하는 환경변수입니다: {key}={raw!r}") from exc


def _get_bool(key: str, default: bool) -> bool:
    raw = _get(key)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    """검증이 끝난 단일 설정 객체. 사용처는 이 객체만 참조한다."""

    app_env: AppEnv
    app_version: str
    log_level: str

    database_url: str
    db_connect_timeout_seconds: int
    db_statement_timeout_ms: int

    jwt_secret: str
    jwt_algorithm: str

    media_bucket: str
    aws_region: str
    s3_endpoint_url: str | None

    vapid_public_key: str | None
    vapid_private_key: str | None
    vapid_subject: str | None

    dev_cors_origin: str | None

    @property
    def is_production(self) -> bool:
        return self.app_env == "prod"

    @property
    def is_development(self) -> bool:
        return self.app_env == "dev"

    @property
    def push_enabled(self) -> bool:
        """VAPID 키가 모두 있을 때만 웹 푸시를 시도한다."""
        return bool(self.vapid_public_key and self.vapid_private_key and self.vapid_subject)


def load_settings() -> Settings:
    _load_dotenv()

    app_env_raw = (_get("APP_ENV", "dev") or "dev").lower()
    if app_env_raw not in {"dev", "prod"}:
        raise ConfigError(f"APP_ENV는 dev|prod 중 하나여야 합니다: {app_env_raw!r}")
    app_env: AppEnv = "prod" if app_env_raw == "prod" else "dev"

    jwt_secret = _require("JWT_SECRET")
    if app_env == "prod" and len(jwt_secret) < 32:
        raise ConfigError("프로덕션 JWT_SECRET은 32자 이상이어야 합니다")

    return Settings(
        app_env=app_env,
        app_version=_get("APP_VERSION", "dev") or "dev",
        log_level=(_get("LOG_LEVEL", "INFO") or "INFO").upper(),
        database_url=_require("DATABASE_URL"),
        db_connect_timeout_seconds=_get_int("DB_CONNECT_TIMEOUT_SECONDS", 5),
        # Lambda 타임아웃보다 짧게 둔다 (백엔드 문서 §4.4)
        db_statement_timeout_ms=_get_int("DB_STATEMENT_TIMEOUT_MS", 8_000),
        jwt_secret=jwt_secret,
        jwt_algorithm="HS256",
        media_bucket=_require("MEDIA_BUCKET"),
        aws_region=_get("AWS_REGION", "ap-northeast-2") or "ap-northeast-2",
        # 로컬에서 S3 호환 스토리지를 붙일 때만 쓴다. 배포에서는 비운다.
        s3_endpoint_url=_get("S3_ENDPOINT_URL"),
        vapid_public_key=_get("VAPID_PUBLIC_KEY"),
        vapid_private_key=_get("VAPID_PRIVATE_KEY"),
        vapid_subject=_get("VAPID_SUBJECT"),
        # 동일 오리진 배포이므로 프로덕션에는 CORS가 없다 (API 문서 §2.11)
        dev_cors_origin=_get("DEV_CORS_ORIGIN", "http://localhost:5173") if app_env == "dev" else None,
    )


@dataclass(frozen=True, slots=True)
class SeedSettings:
    """마이그레이션 시드 전용 값 (DB 문서 §9).

    큐레이터 없는 배포는 동작 불가 상태이므로, 이 값이 없으면 **마이그레이션이 실패**한다.
    애플리케이션 기동에는 필요하지 않으므로 `Settings`와 분리한다.
    """

    curator_phone: str
    curator_name: str
    curator_password: str


def load_seed_settings() -> SeedSettings:
    _load_dotenv()
    return SeedSettings(
        curator_phone=_require("CURATOR_SEED_PHONE"),
        curator_name=_require("CURATOR_SEED_NAME"),
        curator_password=_require("CURATOR_SEED_PASSWORD"),
    )


settings: Final = load_settings()
