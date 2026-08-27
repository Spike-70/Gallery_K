"""소셜 제공자 HTTP 어댑터 (소셜 문서 §6).

**외부 HTTP는 여기서만 나간다**(백엔드 문서 §5, import-linter `boto3-isolated`).
상위 계층은 상태 코드를 해석하지 않는다 — 이 모듈이 실패를 `OAuthTransportError`
하나로 접어 돌려주고, 서비스는 그것을 도메인 오류로 바꾼다.

토큰 응답과 프로필 응답을 **가공하지 않고** 그대로 올려 보낸다. 제공자별 필드 해석은
`config/oauth.py`의 서술자가 하며, 그래야 제공자 지식이 두 곳에 생기지 않는다.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Final

import jwt
import requests
from jwt import PyJWKClient

from chalicelib.config.oauth import JWKS_CACHE_TTL_SECONDS, ProviderSpec
from chalicelib.core.logging import get_logger, log_event

logger = get_logger("oauth")

#: 제공자 응답을 기다리는 시간. Lambda 타임아웃과 프런트 10초 타임아웃 사이에 둔다.
_TIMEOUT_SECONDS: Final = 5


class OAuthTransportError(RuntimeError):
    """제공자와의 통신·검증 실패. 사유는 로그에만 남고 사용자에게는 한 문장으로 나간다."""


@dataclass(frozen=True, slots=True)
class TokenResponse:
    access_token: str
    id_token: str | None


def _post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    try:
        response = requests.post(
            url,
            data=data,
            headers={"Accept": "application/json"},
            timeout=_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise OAuthTransportError(f"요청 실패: {url}") from exc

    if response.status_code >= 400:
        # 본문에는 client_secret이 반사될 수 있다. 상태 코드만 남긴다.
        log_event(logger, "oauth.token.rejected", status=response.status_code)
        raise OAuthTransportError(f"제공자가 거부했습니다: {response.status_code}")
    try:
        return dict(response.json())
    except ValueError as exc:
        raise OAuthTransportError("토큰 응답이 JSON이 아닙니다") from exc


def exchange_code(
    spec: ProviderSpec,
    *,
    code: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str | None,
    code_verifier: str,
) -> TokenResponse:
    """인가 코드 → 토큰 (RFC 6749 §4.1.3 + PKCE RFC 7636 §4.5).

    `code_verifier`가 함께 가는 것이 PKCE의 전부다. 코드만 가로챈 상대는
    verifier가 없어 교환할 수 없다.
    """
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }
    if client_secret:
        payload["client_secret"] = client_secret

    try:
        body = _post_form(spec.token_url, payload)
    except OAuthTransportError:
        # 제공자 콘솔에서 client_secret 을 **켜 두고** 환경변수를 비워 두면 정확히 여기서
        # 실패한다. 상태 코드만으로는 그 사실이 드러나지 않아 원인을 찾는 데 오래 걸린다.
        log_event(
            logger,
            "oauth.token.failed",
            provider=spec.provider,
            client_secret_sent=bool(client_secret),
        )
        raise
    access_token = body.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise OAuthTransportError("토큰 응답에 access_token이 없습니다")
    id_token = body.get("id_token")
    return TokenResponse(
        access_token=access_token,
        id_token=id_token if isinstance(id_token, str) else None,
    )


def fetch_profile(spec: ProviderSpec, *, access_token: str) -> dict[str, Any]:
    try:
        response = requests.get(
            spec.profile_url,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            timeout=_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise OAuthTransportError(f"프로필 조회 실패: {spec.provider}") from exc

    if response.status_code >= 400:
        log_event(logger, "oauth.profile.rejected", status=response.status_code)
        raise OAuthTransportError(f"프로필 조회를 거부했습니다: {response.status_code}")
    try:
        return dict(response.json())
    except ValueError as exc:
        raise OAuthTransportError("프로필 응답이 JSON이 아닙니다") from exc


# ── id_token 검증 ──────────────────────────────────────────────────────────
#
# 제공자 JWKS를 매 로그인마다 받지 않는다. 키 회전 주기는 수개월이고 로그인은 초 단위다.

_jwks_lock = threading.Lock()
_jwks_cache: dict[str, tuple[float, PyJWKClient]] = {}


def _jwk_client(spec: ProviderSpec) -> PyJWKClient:
    now = time.monotonic()
    with _jwks_lock:
        cached = _jwks_cache.get(spec.provider)
        if cached and now - cached[0] < JWKS_CACHE_TTL_SECONDS:
            return cached[1]
        client = PyJWKClient(spec.jwks_url, cache_keys=True)
        _jwks_cache[spec.provider] = (now, client)
        return client


def verify_id_token(spec: ProviderSpec, *, id_token: str, client_id: str, nonce: str) -> dict[str, Any]:
    """`id_token`을 **서명 검증**한다 (OIDC Core §3.1.3.7).

    프로필 API 응답이 아무리 정상이어도 이 검증에 실패하면 로그인시키지 않는다 —
    토큰 응답을 위조할 수 있는 상대라면 프로필 응답도 위조할 수 있다.

    `nonce` 대조가 리플레이를 막는다. 예전에 가로챈 `id_token`은 이번 요청의
    nonce를 가질 수 없다.
    """
    try:
        signing_key = _jwk_client(spec).get_signing_key_from_jwt(id_token)
        claims: dict[str, Any] = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=client_id,
            issuer=spec.issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except (jwt.PyJWTError, requests.RequestException) as exc:
        log_event(logger, "oauth.id_token.invalid", provider=spec.provider)
        raise OAuthTransportError("id_token 검증에 실패했습니다") from exc

    if claims.get("nonce") != nonce:
        log_event(logger, "oauth.id_token.nonce_mismatch", provider=spec.provider)
        raise OAuthTransportError("id_token의 nonce가 일치하지 않습니다")
    return claims
