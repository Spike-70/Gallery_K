"""설정 계층 계약 (백엔드 문서 §8.1)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from chalicelib.config import constants
from chalicelib.config.settings import ConfigError, Settings, load_settings, settings


def test_settings_is_a_frozen_single_object() -> None:
    assert isinstance(settings, Settings)
    with pytest.raises(FrozenInstanceError):
        settings.app_env = "prod"  # type: ignore[misc]


def test_missing_required_variable_fails_at_load(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setattr("chalicelib.config.settings._load_dotenv", lambda: None)
    with pytest.raises(ConfigError, match="JWT_SECRET"):
        load_settings()


def test_production_rejects_short_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("JWT_SECRET", "short")
    monkeypatch.setattr("chalicelib.config.settings._load_dotenv", lambda: None)
    with pytest.raises(ConfigError):
        load_settings()


def test_constants_mirror_the_frontend_contract() -> None:
    """프런트 `shared/config/constants.ts`와 어긋나면 계약이 깨진다 (교차검토 §4)."""
    assert constants.ARTWORK_COUNT == 12
    assert constants.ARCHIVE_MAX_LIMIT == 30
    assert constants.UPLOAD_MAX_BYTES == 20 * 1024 * 1024
    assert constants.UPLOAD_ALLOWED_MIME == ("image/jpeg", "image/png", "image/webp")
    assert constants.PASSWORD_MIN_LENGTH == 8
    assert constants.PASSWORD_MAX_LENGTH == 64
    assert constants.LIMIT_ARTWORK_DESCRIPTION == 300
    assert constants.SESSION_COOKIE_NAME == "gk_session"
    assert constants.CSRF_HEADER_VALUE == "gallery-k"
