"""라우트 통합 테스트 보조.

Chalice 테스트 클라이언트는 쿠키를 관리하지 않는다. 세션 쿠키를 손으로 옮기는 편이
오히려 낫다 — 어떤 요청이 어떤 세션으로 갔는지가 테스트에 그대로 드러난다.
"""

from __future__ import annotations

from typing import Any

from chalicelib.config.constants import CSRF_HEADER_NAME, CSRF_HEADER_VALUE, SESSION_COOKIE_NAME

CSRF = {CSRF_HEADER_NAME: CSRF_HEADER_VALUE, "Content-Type": "application/json"}


def set_cookie_values(response: Any) -> list[str]:
    raw = response.headers.get("Set-Cookie")
    if raw is None:
        return []
    return list(raw) if isinstance(raw, list) else [raw]


def session_token(response: Any) -> str | None:
    for cookie in set_cookie_values(response):
        name, _, rest = cookie.partition("=")
        if name == SESSION_COOKIE_NAME:
            value = rest.split(";", 1)[0]
            return value or None
    return None


def auth_headers(token: str | None, *, csrf: bool = True) -> dict[str, str]:
    """실제 프런트 HTTP 클라이언트와 같은 헤더 조합을 만든다.

    본문이 있는 요청에는 `Content-Type: application/json`이 항상 붙는다 — Chalice는
    그 헤더가 없으면 본문을 파싱하지 않는다.
    """
    headers: dict[str, str] = dict(CSRF) if csrf else {}
    if token:
        headers["Cookie"] = f"{SESSION_COOKIE_NAME}={token}"
    return headers


def signup(
    client: Any, *, phone: str = "01012345678", password: str = "password123", name: str = "관람자"
) -> Any:
    return client.http.post(
        "/auth/signup",
        headers=CSRF,
        body=_json({"phone": phone, "password": password, "name": name, "agreed_terms": True}),
    )


def login(client: Any, *, phone: str, password: str) -> Any:
    return client.http.post(
        "/auth/login",
        headers=CSRF,
        body=_json({"phone": phone, "password": password}),
    )


def _json(payload: dict[str, Any]) -> bytes:
    import json

    return json.dumps(payload).encode("utf-8")


def json_body(payload: dict[str, Any]) -> bytes:
    return _json(payload)


def make_curator(session: Any, *, phone: str = "01000000000", password: str = "curatorpass123") -> Any:
    """큐레이터는 시드로 1건만 존재한다. 테스트도 같은 전제를 따른다."""
    from chalicelib.core.security import hash_password
    from chalicelib.db import query as q
    from chalicelib.db.models import AppUser

    user = q.insert(
        session,
        AppUser,
        {
            "phone": phone,
            "password_hash": hash_password(password),
            "name": "큐레이터",
            "role": "curator",
            "created_via": "curator",
        },
    )
    session.commit()
    return user


def curator_token(client: Any, session: Any) -> str:
    make_curator(session)
    token = session_token(login(client, phone="01000000000", password="curatorpass123"))
    assert token
    return token
