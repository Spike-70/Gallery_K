"""회원 API — 실제 DB (API 문서 §8, DB 문서 §10)."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from sqlalchemy.orm import Session

from chalicelib.core.errors import ErrorCode
from chalicelib.db import query as q
from chalicelib.db.models import (
    AppUser,
    Artwork,
    ArtworkViewLog,
    AuditLog,
    Exhibition,
    NotificationLog,
    PushSubscription,
    ViewLog,
)
from chalicelib.schemas.me import PushSubscribeOut, PushSubscriptionsOut

from .helpers import auth_headers, json_body, session_token, signup

pytestmark = pytest.mark.integration


def _member(api_client: Any) -> str:
    token = session_token(signup(api_client))
    assert token
    return token


def test_me_returns_the_session_user(api_client: Any) -> None:
    token = _member(api_client)
    response = api_client.http.get("/me", headers=auth_headers(token, csrf=False))
    assert response.status_code == 200
    assert response.json_body["data"]["user"]["phone_masked"] == "010-****-5678"


def test_me_requires_a_session(api_client: Any) -> None:
    response = api_client.http.get("/me")
    assert response.status_code == 401
    assert response.json_body["error"]["code"] == ErrorCode.AUTH_REQUIRED


def test_settings_patch_applies_only_the_sent_fields(api_client: Any) -> None:
    token = _member(api_client)
    response = api_client.http.patch(
        "/me/settings", headers=auth_headers(token), body=json_body({"notify_at": "08:00"})
    )
    user = response.json_body["data"]["user"]
    assert user["notify_at"] == "08:00"
    assert user["notify_enabled"] is True
    assert user["font_scale"] == "normal"


def test_turning_notifications_off_keeps_the_time(api_client: Any) -> None:
    """끄더라도 값은 보존한다 — 다시 켤 때 쓰던 시각이 그대로 있어야 한다 (DB 문서 §4.1)."""
    token = _member(api_client)
    api_client.http.patch("/me/settings", headers=auth_headers(token), body=json_body({"notify_at": "09:30"}))
    response = api_client.http.patch(
        "/me/settings", headers=auth_headers(token), body=json_body({"notify_enabled": False})
    )
    user = response.json_body["data"]["user"]
    assert user["notify_enabled"] is False
    assert user["notify_at"] == "09:30"


def test_empty_settings_body_is_rejected(api_client: Any) -> None:
    """의도 없는 PATCH는 버그 신호다 (API 문서 §8.2)."""
    token = _member(api_client)
    response = api_client.http.patch("/me/settings", headers=auth_headers(token), body=json_body({}))
    assert response.status_code == 422
    assert response.json_body["error"]["code"] == ErrorCode.VALIDATION_FAILED


def test_notify_time_outside_the_morning_window_is_rejected(api_client: Any) -> None:
    token = _member(api_client)
    response = api_client.http.patch(
        "/me/settings", headers=auth_headers(token), body=json_body({"notify_at": "23:00"})
    )
    assert response.status_code == 422


def test_unknown_settings_field_is_rejected(api_client: Any) -> None:
    token = _member(api_client)
    response = api_client.http.patch(
        "/me/settings", headers=auth_headers(token), body=json_body({"nickname": "별명"})
    )
    assert response.status_code == 422


def test_push_subscription_round_trip(api_client: Any) -> None:
    token = _member(api_client)
    payload = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/abc123",
        "keys": {"p256dh": "public-key", "auth": "auth-secret"},
        "platform": "ios",
    }

    created = api_client.http.post(
        "/me/push-subscriptions", headers=auth_headers(token), body=json_body(payload)
    )
    assert created.status_code == 201
    first = PushSubscribeOut.model_validate(created.json_body["data"])
    assert first.is_new is True

    again = api_client.http.post(
        "/me/push-subscriptions", headers=auth_headers(token), body=json_body(payload)
    )
    assert again.status_code == 200
    assert PushSubscribeOut.model_validate(again.json_body["data"]).is_new is False

    listed = api_client.http.get("/me/push-subscriptions", headers=auth_headers(token, csrf=False))
    subscriptions = PushSubscriptionsOut.model_validate(listed.json_body["data"]).subscriptions
    assert len(subscriptions) == 1
    assert subscriptions[0].platform == "ios"
    # 엔드포인트 원문은 응답에 담지 않는다 (API 문서 §8.5).
    assert "fcm.googleapis.com" not in str(listed.json_body)


def test_subscribing_turns_notifications_back_on(api_client: Any, write_session: Session) -> None:
    """브라우저 권한을 허용한 시점이 곧 알림을 켜겠다는 의사표시다 (API 문서 §8.4)."""
    token = _member(api_client)
    api_client.http.patch(
        "/me/settings", headers=auth_headers(token), body=json_body({"notify_enabled": False})
    )
    api_client.http.post(
        "/me/push-subscriptions",
        headers=auth_headers(token),
        body=json_body(
            {
                "endpoint": "https://example.com/push/1",
                "keys": {"p256dh": "k", "auth": "a"},
            }
        ),
    )
    user = q.fetch_one(write_session, AppUser, where={"phone": "01012345678"})
    assert user is not None
    write_session.refresh(user)
    assert user.notify_enabled is True


def test_deleting_another_members_subscription_answers_not_found(
    api_client: Any, write_session: Session
) -> None:
    """소유가 아니면 부재로 응답한다 — 남의 자원 ID로 존재를 떠보지 못하게 한다."""
    owner_token = _member(api_client)
    created = api_client.http.post(
        "/me/push-subscriptions",
        headers=auth_headers(owner_token),
        body=json_body({"endpoint": "https://example.com/push/owner", "keys": {"p256dh": "k", "auth": "a"}}),
    )
    subscription_id = created.json_body["data"]["subscription_id"]

    intruder_token = session_token(signup(api_client, phone="01055556666", name="침입자"))
    response = api_client.http.delete(
        f"/me/push-subscriptions/{subscription_id}", headers=auth_headers(intruder_token)
    )
    assert response.status_code == 404
    assert response.json_body["error"]["code"] == ErrorCode.NOT_FOUND
    assert q.count(write_session, PushSubscription) == 1


def test_deleting_own_subscription_keeps_notifications_enabled(
    api_client: Any, write_session: Session
) -> None:
    """다른 단말에서는 계속 받을 수 있어야 한다 (API 문서 §8.6)."""
    token = _member(api_client)
    created = api_client.http.post(
        "/me/push-subscriptions",
        headers=auth_headers(token),
        body=json_body({"endpoint": "https://example.com/push/mine", "keys": {"p256dh": "k", "auth": "a"}}),
    )
    subscription_id = created.json_body["data"]["subscription_id"]

    response = api_client.http.delete(
        f"/me/push-subscriptions/{subscription_id}", headers=auth_headers(token)
    )
    assert response.status_code == 200
    assert q.count(write_session, PushSubscription) == 0
    user = q.fetch_one(write_session, AppUser, where={"phone": "01012345678"})
    assert user is not None
    assert user.notify_enabled is True


def test_withdrawal_anonymises_logs_and_deletes_personal_rows(
    api_client: Any, write_session: Session
) -> None:
    """DB 문서 §10의 탈퇴 트랜잭션."""
    token = _member(api_client)
    user = q.fetch_one(write_session, AppUser, where={"phone": "01012345678"})
    assert user is not None

    exhibition = q.insert(
        write_session,
        Exhibition,
        {
            "exhibition_date": dt.date(2026, 8, 27),
            "title": "전시",
            "theme": "테마",
            "is_published": True,
            "published_at": dt.datetime(2026, 8, 26, 22, 0, tzinfo=dt.UTC),
        },
    )
    artwork = q.insert(
        write_session, Artwork, {"exhibition_id": exhibition.id, "position": 1, "title": "그림"}
    )
    now = dt.datetime(2026, 8, 27, 0, 0, tzinfo=dt.UTC)
    q.insert(
        write_session,
        ViewLog,
        {
            "user_id": user.id,
            "viewed_on": dt.date(2026, 8, 27),
            "exhibition_id": exhibition.id,
            "first_entered_at": now,
            "last_entered_at": now,
        },
    )
    q.insert(
        write_session,
        ArtworkViewLog,
        {
            "user_id": user.id,
            "artwork_id": artwork.id,
            "exhibition_id": exhibition.id,
            "first_viewed_on": dt.date(2026, 8, 27),
            "first_viewed_at": now,
            "last_viewed_at": now,
        },
    )
    q.insert(
        write_session,
        PushSubscription,
        {
            "user_id": user.id,
            "endpoint": "https://example.com/push/x",
            "endpoint_hash": "hash",
            "p256dh": "k",
            "auth": "a",
        },
    )
    q.insert(
        write_session,
        NotificationLog,
        {
            "user_id": user.id,
            "kind": "morning_exhibition",
            "dedupe_key": "morning:x",
            "status": "pending",
            "scheduled_for": now,
        },
    )
    write_session.commit()

    response = api_client.http.delete("/me", headers=auth_headers(token), body=json_body({"confirm": True}))
    assert response.status_code == 200

    assert q.count(write_session, AppUser, where={"phone": "01012345678"}) == 0
    assert q.count(write_session, PushSubscription) == 0
    assert q.count(write_session, NotificationLog) == 0

    view_logs = q.fetch(write_session, ViewLog)
    assert len(view_logs) == 1
    assert view_logs[0].user_id is None
    assert view_logs[0].is_anonymized is True

    artwork_logs = q.fetch(write_session, ArtworkViewLog)
    assert artwork_logs[0].user_id is None
    assert artwork_logs[0].is_anonymized is True


def test_withdrawal_audit_row_identifies_nobody(api_client: Any, write_session: Session) -> None:
    """탈퇴 감사 기록에는 탈퇴자를 식별할 값을 어디에도 남기지 않는다 (DB 문서 §10)."""
    token = _member(api_client)
    api_client.http.delete("/me", headers=auth_headers(token), body=json_body({"confirm": True}))

    rows = q.fetch(write_session, AuditLog)
    assert len(rows) == 1
    entry = rows[0]
    assert entry.action == "member.withdraw"
    assert entry.actor_id is None
    assert entry.target_id is None
    assert "01012345678" not in str(entry.changes)


def test_withdrawal_requires_explicit_confirmation(api_client: Any) -> None:
    token = _member(api_client)
    response = api_client.http.delete("/me", headers=auth_headers(token), body=json_body({}))
    assert response.status_code == 422


def test_curator_cannot_withdraw(api_client: Any, write_session: Session) -> None:
    from chalicelib.core.security import hash_password

    q.insert(
        write_session,
        AppUser,
        {
            "phone": "01000000000",
            "password_hash": hash_password("curatorpass123"),
            "name": "큐레이터",
            "role": "curator",
            "created_via": "curator",
        },
    )
    write_session.commit()

    from .helpers import login

    token = session_token(login(api_client, phone="01000000000", password="curatorpass123"))
    response = api_client.http.delete("/me", headers=auth_headers(token), body=json_body({"confirm": True}))
    assert response.status_code == 403
    assert response.json_body["error"]["code"] == ErrorCode.MEMBER_CURATOR_IMMUTABLE


def test_unusable_push_subscription_uses_the_documented_code(api_client: Any) -> None:
    """스키마가 아니라 **쓸 수 있는 값인가**를 보는 실패다 (API 문서 §8.4)."""
    token = _member(api_client)
    response = api_client.http.post(
        "/me/push-subscriptions",
        headers=auth_headers(token),
        body=json_body(
            {
                # https가 아닌 엔드포인트로는 푸시를 보낼 수 없다.
                "endpoint": "http://insecure.example.com/push/1",
                "keys": {"p256dh": "k", "auth": "a"},
            }
        ),
    )
    assert response.status_code == 422
    assert response.json_body["error"]["code"] == ErrorCode.PUSH_SUBSCRIPTION_INVALID
