"""직렬화기 ↔ 응답 스키마 정합 (API 문서 §3).

`chalicelib/schemas`의 `*Out`은 **계약의 문서이자 검사기**다(그 모듈 docstring). 그런데
지금까지 그 검사는 일부 라우트에서 `model_validate`로만 이루어졌고, pydantic은 기본적으로
**모르는 필드를 무시**하므로 다음 둘 중 어느 것도 잡히지 않았다.

  * 직렬화기가 스키마에 없는 키를 내보낸다   → 문서가 실물보다 좁다
  * 스키마에만 있고 직렬화기가 안 내보낸다   → 문서가 실물보다 넓다

실제로 `SessionUser.has_password`가 서비스에는 있고 스키마에는 없는 상태로 지나갔다.
여기서는 **키 집합이 정확히 같은지**를 본다.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

import pytest

from chalicelib.db.models import AppUser, PushSubscription, SocialIdentity
from chalicelib.schemas.auth import SessionUserOut, SocialIdentityOut
from chalicelib.schemas.me import PushSubscriptionOut
from chalicelib.services import member_service, push_service, social_auth_service

NOW = dt.datetime(2026, 8, 28, 0, 0, tzinfo=dt.UTC)
UID = uuid.UUID("00000000-0000-4000-8000-00000000000a")


def _session_user() -> dict[str, Any]:
    user = AppUser(
        id=UID,
        phone="01012345678",
        password_hash="x" * 60,
        name="관람자",
        role="viewer",
        font_scale="normal",
        notify_enabled=True,
        notify_at=dt.time(7, 30),
        must_change_password=False,
        created_at=NOW,
        updated_at=NOW,
    )
    return member_service.serialize_session_user(user)


def _push_subscription() -> dict[str, Any]:
    row = PushSubscription(
        id=UID,
        user_id=UID,
        endpoint="https://example.com/push/abc",
        endpoint_hash="h" * 64,
        p256dh="k",
        auth="a",
        platform="ios",
        is_active=True,
        failure_count=0,
        last_success_at=None,
        created_at=NOW,
        updated_at=NOW,
    )
    return push_service.serialize_subscription(row)


def _social_identity() -> dict[str, Any]:
    row = SocialIdentity(
        id=UID,
        user_id=UID,
        provider="kakao",
        provider_uid="12345",
        email=None,
        display_name=None,
        linked_at=NOW,
        last_login_at=None,
        created_at=NOW,
        updated_at=NOW,
    )
    return social_auth_service.serialize_identity(row)


@pytest.mark.parametrize(
    ("name", "serialize", "schema"),
    [
        ("SessionUser", _session_user, SessionUserOut),
        ("PushSubscription", _push_subscription, PushSubscriptionOut),
        ("SocialIdentity", _social_identity, SocialIdentityOut),
    ],
)
def test_serializer_keys_match_the_response_schema(name: str, serialize: Any, schema: type) -> None:
    produced = set(serialize())
    declared = set(schema.model_fields)

    assert produced == declared, (
        f"{name}: 직렬화기와 응답 스키마가 어긋났습니다. "
        f"직렬화기에만={sorted(produced - declared)} 스키마에만={sorted(declared - produced)}"
    )


@pytest.mark.parametrize(
    ("name", "serialize", "schema"),
    [
        ("SessionUser", _session_user, SessionUserOut),
        ("PushSubscription", _push_subscription, PushSubscriptionOut),
        ("SocialIdentity", _social_identity, SocialIdentityOut),
    ],
)
def test_serializer_output_validates_against_the_schema(name: str, serialize: Any, schema: type) -> None:
    """키뿐 아니라 타입도 스키마를 만족해야 한다."""
    schema.model_validate(serialize())
