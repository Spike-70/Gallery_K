"""소셜 로그인 흐름 (소셜 문서 §3–§5).

**이 모듈은 제공자를 모른다**(SA-4). 카카오와 구글의 차이는 `config/oauth.py`의
서술자에 있고, 여기서는 서술자를 읽어 같은 절차를 돈다.

절차는 둘로 나뉜다.

  ① 인가 왕복 — `begin()` → 제공자 → `complete_callback()`
  ② 계정 결정 — 연결된 계정이 있으면 즉시 로그인, 없으면 A-4 화면으로 넘긴다

②를 자동 가입으로 대신하지 않는 이유는 전화번호다. 아침 알림 타겟팅·대행 가입·차단·
회원 관리가 전부 전화번호에 걸려 있어, 전화번호 없는 회원은 운영 화면에서 다룰 수
없다(SA-2). 소셜은 로그인 수단이지 신원이 아니다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Final
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from chalicelib.config.oauth import (
    LINK_TICKET_TTL_SECONDS,
    OAUTH_STATE_TTL_SECONDS,
    ProviderSpec,
    SocialProfile,
    enabled_providers,
    redirect_uri,
    spec_of,
)
from chalicelib.config.settings import settings
from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.logging import get_logger, log_event
from chalicelib.core.security import (
    LinkTicket,
    OAuthTicket,
    build_oauth_link_cookie,
    build_oauth_state_cookie,
    code_challenge_of,
    new_state_secret,
    verify_password,
)
from chalicelib.core.timeutil import now_utc
from chalicelib.db import query as q
from chalicelib.db.models import AppUser, SocialIdentity
from chalicelib.db.models.enums import CreatedVia, ThrottleScope
from chalicelib.integrations import oauth as oauth_client
from chalicelib.services import (
    auth_service,
    member_service,
    notification_service,
    setting_service,
    throttle_service,
)
from chalicelib.services.setting_service import SettingKey
from chalicelib.utils.text import normalize_phone

logger = get_logger("social")

#: 로그인 후 돌아갈 기본 경로. A-1의 성공 목적지와 같다(PRD §6.2).
DEFAULT_NEXT_PATH: Final = "/gallery"


# ── 열린 리다이렉트 방어 (소셜 문서 §4) ────────────────────────────────────


def safe_next_path(raw: str | None) -> str:
    """앱 내부 경로만 통과시킨다.

    `//evil.com`과 `\\evil.com`을 막는 것이 요점이다. 둘 다 브라우저가 **다른 호스트로**
    해석하며, `/`로 시작하는지만 보는 검사는 이 둘을 통과시킨다.
    """
    if not raw or not raw.startswith("/"):
        return DEFAULT_NEXT_PATH
    if raw.startswith(("//", "/\\", "/%2f", "/%5c")):
        return DEFAULT_NEXT_PATH
    return raw


# ── 제공자 목록 ────────────────────────────────────────────────────────────


def list_providers() -> list[dict[str, str]]:
    """켜진 제공자만. **화면이 환경변수를 알 필요가 없다**(소셜 문서 §8)."""
    return [
        {
            "provider": spec.provider,
            "label": spec.label,
            "start_url": f"/api/auth/social/{spec.provider}/start",
        }
        for spec in enabled_providers()
    ]


def _require_spec(provider: str) -> ProviderSpec:
    spec = spec_of(provider)
    if spec is None:
        raise AppError(ErrorCode.SOCIAL_PROVIDER_UNKNOWN, details={"provider": provider})
    if not settings.social_enabled(provider):
        raise AppError(ErrorCode.SOCIAL_DISABLED, details={"provider": provider})
    return spec


# ── ① 인가 왕복 ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Authorization:
    """`start`가 만들어 내는 것 — 갈 곳과, 돌아왔을 때 대조할 쿠키."""

    authorize_url: str
    state_cookie: str


def begin(provider: str, *, next_path: str | None) -> Authorization:
    """인가 URL을 만들고 대조용 비밀을 쿠키에 봉인한다.

    `state`·`code_verifier`·`nonce` 셋 다 여기서 새로 만든다. URL에 나가는 것은
    `state`와 `code_challenge`(verifier의 SHA-256)뿐이며, **verifier 원문은 쿠키에만
    있다** — 코드를 가로챈 상대가 교환하지 못하게 하는 것이 PKCE의 전부다.
    """
    spec = _require_spec(provider)
    callback = redirect_uri(provider)
    if callback is None:  # pragma: no cover - social_enabled 가 이미 막는다
        raise AppError(ErrorCode.SOCIAL_DISABLED, details={"provider": provider})

    state = new_state_secret()
    code_verifier = new_state_secret()
    nonce = new_state_secret()

    params = {
        "response_type": "code",
        "client_id": settings.social_client_id(provider) or "",
        "redirect_uri": callback,
        "scope": spec.scope,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge_of(code_verifier),
        "code_challenge_method": "S256",
        **spec.extra_authorize_params,
    }
    log_event(logger, "social.start", provider=provider)
    return Authorization(
        authorize_url=f"{spec.authorize_url}?{urlencode(params)}",
        state_cookie=build_oauth_state_cookie(
            OAuthTicket(
                provider=provider,
                state=state,
                code_verifier=code_verifier,
                nonce=nonce,
                next_path=safe_next_path(next_path),
            ),
            ttl_seconds=OAUTH_STATE_TTL_SECONDS,
        ),
    )


def resolve_profile(
    provider: str, *, code: str, state: str | None, ticket: OAuthTicket | None
) -> SocialProfile:
    """콜백에서 제공자 신원을 확정한다. 여기까지가 외부와 닿는 마지막 지점이다.

    검증 순서가 곧 방어 순서다 — `state`가 틀리면 토큰 교환을 **시도조차 하지 않는다**.
    """
    spec = _require_spec(provider)

    if ticket is None or ticket.provider != provider or not state or ticket.state != state:
        log_event(logger, "social.state.mismatch", provider=provider)
        raise AppError(ErrorCode.SOCIAL_STATE_INVALID)

    callback = redirect_uri(provider)
    client_id = settings.social_client_id(provider)
    if callback is None or client_id is None:  # pragma: no cover
        raise AppError(ErrorCode.SOCIAL_DISABLED, details={"provider": provider})

    try:
        token = oauth_client.exchange_code(
            spec,
            code=code,
            redirect_uri=callback,
            client_id=client_id,
            client_secret=settings.social_client_secret(provider),
            code_verifier=ticket.code_verifier,
        )
        claims: dict[str, Any] = {}
        if token.id_token:
            claims = oauth_client.verify_id_token(
                spec, id_token=token.id_token, client_id=client_id, nonce=ticket.nonce
            )
        # 검증된 `id_token`에 `sub`가 있으면 **프로필 API를 부르지 않는다.**
        # scope가 `openid`뿐이라 그 응답에서 더 얻을 것이 없고, 부르면 쓰지도 않을
        # 데이터를 받게 된다 — 받지 않는 것이 최소 수집이다(PRD §8.4).
        # 제공자 콘솔에서 OIDC가 꺼져 `id_token`이 없을 때만 대체 경로로 쓴다.
        raw_profile = (
            {} if claims.get("sub") else oauth_client.fetch_profile(spec, access_token=token.access_token)
        )
    except oauth_client.OAuthTransportError as exc:
        log_event(logger, "social.exchange.failed", provider=provider)
        raise AppError(ErrorCode.SOCIAL_EXCHANGE_FAILED, details={"provider": provider}) from exc

    profile = spec.parse_profile(raw_profile, claims)
    if not profile.uid:
        # 식별자가 없으면 이 사람이 누구인지 알 수 없다. 로그인시키지 않는다.
        log_event(logger, "social.profile.no_uid", provider=provider)
        raise AppError(ErrorCode.SOCIAL_EXCHANGE_FAILED, details={"provider": provider})
    return profile


def build_link_cookie(profile: SocialProfile, *, next_path: str) -> str:
    """A-4 화면이 들고 갈 티켓. **어떤 계정에 연결할지는 담지 않는다**(소셜 문서 §4)."""
    return build_oauth_link_cookie(
        LinkTicket(
            provider=profile.provider,
            provider_uid=profile.uid,
            email=profile.email,
            display_name=profile.display_name,
            next_path=safe_next_path(next_path),
        ),
        ttl_seconds=LINK_TICKET_TTL_SECONDS,
    )


# ── ② 계정 결정 ────────────────────────────────────────────────────────────


def find_linked_user(session: Session, profile: SocialProfile) -> auth_service.AuthenticatedUser | None:
    """연결된 계정이 있으면 로그인시킨다. 없으면 `None` — 호출부가 A-4로 보낸다."""
    identity = q.fetch_one(
        session,
        SocialIdentity,
        where={"provider": profile.provider, "provider_uid": profile.uid},
    )
    if identity is None:
        return None

    user = q.fetch_one(session, AppUser, where={"id": identity.user_id})
    if user is None:  # pragma: no cover - FK CASCADE 가 막는다
        return None
    if user.is_blocked:
        # 차단 사실을 알리지 않는다(PRD §6.4). 전화번호 로그인과 **같은 문으로 나간다** —
        # 두 경로의 응답이 다르면 그 차이가 곧 차단 여부를 알려 준다.
        log_event(logger, "social.login.blocked", provider=profile.provider)
        raise AppError(ErrorCode.AUTH_INVALID_CREDENTIALS)

    now = now_utc()
    q.update(session, SocialIdentity, where={"id": identity.id}, values={"last_login_at": now})
    q.update(session, AppUser, where={"id": user.id}, values={"last_login_at": now})
    session.refresh(user)
    log_event(logger, "social.login.succeeded", provider=profile.provider)
    return _authenticated(user)


def link_existing(
    session: Session, ticket: LinkTicket, *, phone: str, password: str
) -> auth_service.AuthenticatedUser:
    """A-4 `이미 회원이신가요?` — 전화번호와 **비밀번호로 소유를 증명**하고 연결한다.

    번호만으로 연결하면 남의 번호를 적어 계정을 가져갈 수 있다. 연결은 인증이다.

    실패 사유(미가입·비밀번호 불일치·차단)를 구분하지 않는 것도 A-1과 같다(§5.2).
    """
    normalized = normalize_phone(phone)
    user = q.fetch_one(session, AppUser, where={"phone": normalized})

    password_ok = verify_password(password, user.password_hash if user else None)
    blocked = bool(user and user.is_blocked)

    if user is None or not password_ok or blocked:
        retry_after = throttle_service.register_hit(ThrottleScope.LOGIN, normalized)
        log_event(
            logger,
            "social.link.failed",
            reason="not_found" if user is None else ("blocked" if blocked else "bad_password"),
        )
        if retry_after > 0:
            raise AppError(ErrorCode.AUTH_TOO_MANY_ATTEMPTS, details={"retry_after_seconds": retry_after})
        raise AppError(ErrorCode.AUTH_INVALID_CREDENTIALS)

    throttle_service.clear(ThrottleScope.LOGIN, normalized)
    _attach_identity(session, user_id=user.id, ticket=ticket)
    q.update(session, AppUser, where={"id": user.id}, values={"last_login_at": now_utc()})
    session.refresh(user)
    log_event(logger, "social.link.succeeded", provider=ticket.provider)
    return _authenticated(user)


def signup_with_social(
    session: Session, ticket: LinkTicket, *, phone: str, name: str
) -> auth_service.AuthenticatedUser:
    """A-4 `처음이신가요?` — 새 계정을 만들고 연결한다. 비밀번호는 만들지 않는다.

    **가입 잠금을 그대로 따른다.** 소셜이 잠금의 뒷문이 되면 폐쇄형 서비스라는 전제가
    깨진다(API 문서 §9.14).
    """
    normalized = normalize_phone(phone)

    if not setting_service.get_bool(session, SettingKey.SIGNUP_OPEN):
        raise AppError(ErrorCode.SIGNUP_CLOSED)
    if q.exists(session, AppUser, where={"phone": normalized}):
        # 이 번호는 §6.14(연결)로 가야 한다. A-1의 가입 화면과 같은 코드를 쓴다.
        raise AppError(ErrorCode.SIGNUP_PHONE_TAKEN)
    _guard_not_linked(session, ticket)

    default_time = setting_service.get_str(session, SettingKey.NOTIFY_DEFAULT_TIME)
    now = now_utc()
    user = q.insert(
        session,
        AppUser,
        {
            "phone": normalized,
            # 비밀번호가 없는 계정이다. D 설정 화면이 `has_password`로 이 사실을 안다.
            "password_hash": None,
            "name": name,
            "role": "viewer",
            "created_via": CreatedVia.SOCIAL,
            "must_change_password": False,
            "notify_enabled": True,
            "notify_at": _parse_time(default_time),
            "last_login_at": now,
        },
    )
    _attach_identity(session, user_id=user.id, ticket=ticket)
    notification_service.queue_curator_signup(session, new_user_id=user.id, new_user_name=user.name)
    log_event(logger, "social.signup", provider=ticket.provider)
    return _authenticated(user)


# ── 연결 관리 (API 문서 §8.7·§8.8) ─────────────────────────────────────────


def list_identities(session: Session, user_id: uuid.UUID) -> dict[str, Any]:
    identities = q.fetch(session, SocialIdentity, where={"user_id": user_id}, order_by=["linked_at"])
    user = member_service.get_user(session, user_id)
    return {
        "identities": [serialize_identity(row) for row in identities],
        # 마지막 로그인 수단을 끊으면 영구 잠금이다(SA-6). 화면이 이 값으로 버튼을 잠근다.
        "can_unlink": bool(user.password_hash) or len(identities) > 1,
    }


def unlink(session: Session, user_id: uuid.UUID, identity_id: uuid.UUID) -> None:
    identity = q.fetch_one(session, SocialIdentity, where={"id": identity_id, "user_id": user_id})
    if identity is None:
        # 남의 연결 id로 존재를 떠보는 것도 부재로 답한다.
        raise AppError(ErrorCode.NOT_FOUND, details={"resource": "social_identity"})

    user = member_service.get_user(session, user_id)
    remaining = q.count(session, SocialIdentity, where={"user_id": user_id}) - 1
    if not user.password_hash and remaining <= 0:
        raise AppError(ErrorCode.SOCIAL_LAST_IDENTITY)

    q.delete(session, SocialIdentity, where={"id": identity_id})
    log_event(logger, "social.unlink", provider=identity.provider)


def serialize_identity(row: SocialIdentity) -> dict[str, Any]:
    """`SocialIdentity` (API 문서 §3.10). **제공자 토큰은 담기지 않는다**(SA-3)."""
    from chalicelib.core.timeutil import format_rfc3339

    spec = spec_of(row.provider)
    return {
        "id": str(row.id),
        "provider": row.provider,
        "label": spec.label if spec else row.provider,
        "email": row.email,
        "display_name": row.display_name,
        "linked_at": format_rfc3339(row.linked_at),
        "last_login_at": format_rfc3339(row.last_login_at) if row.last_login_at else None,
    }


# ── 내부 ───────────────────────────────────────────────────────────────────


def _guard_not_linked(session: Session, ticket: LinkTicket) -> None:
    if q.exists(
        session,
        SocialIdentity,
        where={"provider": ticket.provider, "provider_uid": ticket.provider_uid},
    ):
        # 어느 계정인지는 알려주지 않는다 — 회원 명단 조회 수단이 된다(SA-5).
        raise AppError(ErrorCode.SOCIAL_ALREADY_LINKED)


def _attach_identity(session: Session, *, user_id: uuid.UUID, ticket: LinkTicket) -> None:
    _guard_not_linked(session, ticket)
    now = now_utc()
    q.insert(
        session,
        SocialIdentity,
        {
            "user_id": user_id,
            "provider": ticket.provider,
            "provider_uid": ticket.provider_uid,
            "email": ticket.email,
            "display_name": ticket.display_name,
            "linked_at": now,
            "last_login_at": now,
        },
    )


def _authenticated(user: AppUser) -> auth_service.AuthenticatedUser:
    return auth_service.AuthenticatedUser(
        id=user.id,
        role=user.role,
        token_version=user.token_version,
        user=member_service.serialize_session_user(user),
    )


def _parse_time(raw: str) -> Any:
    from chalicelib.core.timeutil import parse_time_of_day

    return parse_time_of_day(raw)
