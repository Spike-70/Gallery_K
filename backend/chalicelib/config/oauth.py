"""소셜 제공자 서술자 (소셜 문서 §6).

**흐름 코드는 제공자를 모른다**(SA-4). 카카오와 구글의 차이는 전부 이 파일의 서술자
안에 있고, `services/social_auth_service.py`는 서술자만 읽는다. 제공자를 하나 더
지원하는 일은 여기에 `ProviderSpec` 하나를 더하고 `SocialProvider`에 값을 넣는 것이다.

이 모듈은 **설정일 뿐 HTTP를 하지 않는다.** 실제 요청은 `integrations/oauth.py`가 한다.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Final

from chalicelib.config.settings import settings
from chalicelib.db.models.enums import SocialProvider

#: 콜백 경로. 제공자 콘솔에 등록하는 값의 뒷부분이며 **요청에서 받지 않는다**(소셜 문서 §7).
CALLBACK_PATH_TEMPLATE: Final = "/api/auth/social/{provider}/callback"

#: 인가 왕복 쿠키의 수명. 동의 화면에서 머뭇거릴 시간은 주되, 방치된 상태가 오래
#: 살아 있지 않게 한다.
OAUTH_STATE_TTL_SECONDS: Final = 600
#: 연결 티켓(A-4 화면) 수명. 전화번호와 비밀번호를 입력할 시간이다.
LINK_TICKET_TTL_SECONDS: Final = 600

#: JWKS 프로세스 캐시 수명. 제공자 키 회전 주기(수개월)에 비하면 짧다.
JWKS_CACHE_TTL_SECONDS: Final = 3600


@dataclass(frozen=True, slots=True)
class SocialProfile:
    """제공자 응답에서 뽑아낸 것. **여기까지가 제공자를 아는 마지막 지점이다.**"""

    provider: str
    #: 제공자가 발급하는 불변 식별자. 유일한 신원이다(소셜 문서 §6).
    uid: str
    email: str | None
    display_name: str | None


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    provider: str
    #: 화면에 그대로 쓰는 한국어 이름. 문구가 코드 곳곳에 흩어지지 않게 한다.
    label: str
    authorize_url: str
    token_url: str
    profile_url: str
    scope: str
    #: OIDC 발급자. `id_token`의 `iss`가 이 값이어야 한다.
    issuer: str
    jwks_url: str
    #: 인가 URL에 덧붙이는 제공자 고유 파라미터.
    extra_authorize_params: dict[str, str] = field(default_factory=dict)
    #: 프로필 응답(JSON) + 검증된 id_token 클레임 → `SocialProfile`
    parse_profile: Callable[[dict[str, Any], dict[str, Any]], SocialProfile] = field(
        default=lambda profile, claims: SocialProfile("", "", None, None)
    )


def _kakao_profile(profile: dict[str, Any], claims: dict[str, Any]) -> SocialProfile:
    """카카오 `/v2/user/me` (소셜 문서 §6).

    현재 scope(`openid`)에서는 `email`·`nickname`이 **오지 않으며 `None`이 된다.**
    동의항목을 늘리면 그대로 채워지도록 추출 자체는 남겨 둔다 — 신원 판정은 어차피
    `sub`(또는 `id`) 하나뿐이라 값이 없어도 로그인은 성립한다.
    """
    account = profile.get("kakao_account") or {}
    kakao_profile = account.get("profile") or {}
    uid = str(claims.get("sub") or profile.get("id") or "")
    email = account.get("email") if account.get("is_email_valid") is not False else None
    return SocialProfile(
        provider=SocialProvider.KAKAO,
        uid=uid,
        email=email or claims.get("email"),
        display_name=kakao_profile.get("nickname") or claims.get("nickname"),
    )


def _google_profile(profile: dict[str, Any], claims: dict[str, Any]) -> SocialProfile:
    """구글 userinfo (OIDC 표준).

    현재 scope(`openid`)에서는 `email`·`name`이 오지 않는다. `email` scope를 다시
    켤 경우를 대비해 `email_verified`가 거짓이면 버리는 규칙은 남겨 둔다 —
    검증되지 않은 이메일을 표시하면 사용자가 신뢰할 근거가 있다고 오해한다.
    """
    verified = profile.get("email_verified", claims.get("email_verified"))
    email = profile.get("email") or claims.get("email")
    return SocialProfile(
        provider=SocialProvider.GOOGLE,
        uid=str(claims.get("sub") or profile.get("sub") or ""),
        email=email if verified else None,
        display_name=profile.get("name") or claims.get("name"),
    )


PROVIDERS: Final[dict[str, ProviderSpec]] = {
    SocialProvider.KAKAO: ProviderSpec(
        provider=SocialProvider.KAKAO,
        label="카카오",
        authorize_url="https://kauth.kakao.com/oauth/authorize",
        token_url="https://kauth.kakao.com/oauth/token",
        profile_url="https://kapi.kakao.com/v2/user/me",
        # **`openid` 하나뿐이다.** 닉네임·이메일은 받지 않는다 — 화면 어디에서도 쓰지
        # 않으므로 받아 봐야 지킬 책임만 늘어난다(PRD §8.4 최소 수집). 동의항목을
        # 켜지 않으므로 제공자 콘솔의 동의 목적 심사도 필요 없다.
        scope="openid",
        issuer="https://kauth.kakao.com",
        jwks_url="https://kauth.kakao.com/.well-known/jwks.json",
        parse_profile=_kakao_profile,
    ),
    SocialProvider.GOOGLE: ProviderSpec(
        provider=SocialProvider.GOOGLE,
        label="구글",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        profile_url="https://openidconnect.googleapis.com/v1/userinfo",
        scope="openid",
        issuer="https://accounts.google.com",
        jwks_url="https://www.googleapis.com/oauth2/v3/certs",
        extra_authorize_params={
            # refresh token을 받지 않는다. 로그인 성립 후 제공자 토큰을 버리므로(SA-3)
            # 장기 자격을 받아 둘 이유가 없고, 받아 두면 보관 책임만 생긴다.
            "access_type": "online",
            # 계정을 여러 개 쓰는 사용자가 어느 계정으로 들어가는지 매번 고르게 한다.
            "prompt": "select_account",
        },
        parse_profile=_google_profile,
    ),
}


def spec_of(provider: str) -> ProviderSpec | None:
    return PROVIDERS.get(provider)


def redirect_uri(provider: str) -> str | None:
    """제공자 콘솔에 등록해야 하는 값과 **글자 그대로 같아야 한다**(소셜 문서 §7)."""
    base = settings.social_redirect_base_url
    if not base:
        return None
    return f"{base}{CALLBACK_PATH_TEMPLATE.format(provider=provider)}"


def enabled_providers() -> list[ProviderSpec]:
    """켜진 제공자만. 화면은 이 목록만 보고 버튼을 그린다(소셜 문서 §8)."""
    return [spec for provider, spec in PROVIDERS.items() if settings.social_enabled(provider)]
