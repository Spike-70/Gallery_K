# 갤러리 K — 소셜 로그인 설계서

| | |
|---|---|
| **문서 버전** | v1.0 |
| **상위 문서** | `PRD.md`, `01-DATABASE-MODEL.md`, `02-API-SPEC.md`, `04-BACKEND-ARCHITECTURE.md` |
| **프로토콜** | OAuth 2.0 Authorization Code + PKCE (RFC 7636) · OpenID Connect Core 1.0 |
| **지원 제공자** | 카카오 · 구글 |
| **상태** | 확정 (구현 기준선) |

이 문서가 소셜 로그인의 **단일 진실 원천**이다. 스키마는 `01`, 엔드포인트 표는 `02`, 화면은 `06`에 함께 반영되어 있으며, 셋이 어긋나면 이 문서가 기준이다.

---

## 1. 원칙

| # | 원칙 | 이유 |
|---|---|---|
| SA-1 | **리다이렉트 방식만 쓴다. 팝업을 쓰지 않는다** | 대상 사용자가 60–70대다(PRD §3). 팝업은 iOS Safari에서 차단되기 쉽고, 차단되면 아무 일도 일어나지 않아 사용자가 원인을 알 수 없다. 리다이렉트는 화면이 실제로 넘어가므로 "지금 무슨 일이 일어나는지"가 보인다 |
| SA-2 | **전화번호가 여전히 신원의 근간이다** | 아침 알림 타겟팅·대행 가입·차단·B-3 회원 관리가 전부 전화번호에 걸려 있다(PRD §6.4·§6.13). 소셜은 **로그인 수단**이지 신원이 아니다 |
| SA-3 | 토큰은 서버 밖으로 나가지 않는다 | 제공자 access token·refresh token을 브라우저에 전달하지 않고 저장하지도 않는다. 로그인 성립 후에는 **버린다** |
| SA-4 | 제공자 추가는 서술자 한 줄이다 | 흐름 코드는 제공자를 모른다. 차이는 `config/oauth.py`의 서술자에만 있다 |
| SA-5 | 계정 존재 여부를 노출하지 않는다 | 기존 §5.2 규칙을 소셜 경로에도 그대로 적용한다 |
| SA-6 | 연결 해제로 로그인 수단이 0이 되지 않는다 | 비밀번호 없는 계정이 유일한 소셜 연결을 끊으면 영구 잠금이다 |

---

## 2. 왜 리다이렉트인가 — 쿠키 관점의 근거

세션 쿠키는 `SameSite=Lax`다(API 문서 §2.7).

| 방식 | 콜백의 성격 | `SameSite=Lax` 쿠키 |
|---|---|---|
| **리다이렉트** | 제공자 → 우리 서버로의 **top-level GET 내비게이션** | **전송된다** ✔ |
| 팝업 + `postMessage` | 팝업 창의 top-level GET (동일) + 부모창과의 메시지 | 전송되지만, 세션 발급을 부모창이 받아야 해 오리진 검증이 추가로 필요 |
| iframe 방식 | 서드파티 컨텍스트 | **차단된다** ✗ (`SameSite=None; Secure` 필요) |

리다이렉트를 고르면 쿠키 정책을 **하나도 느슨하게 하지 않고** 소셜 로그인이 성립한다. `SameSite=None`으로 내리는 순간 CSRF 방어의 한 겹이 통째로 사라지므로, 이것이 SA-1의 기술적 근거다.

---

## 3. 전체 흐름

```
A-1 로그인 화면
  │
  │ [카카오로 시작하기]  ← 평범한 <a href>. JS 없이도 동작한다
  ▼
GET /api/auth/social/{provider}/start?next=/gallery
  │  ① state·code_verifier·nonce 생성
  │  ② 셋을 서명 쿠키 gk_oauth 에 담는다 (TTL 10분, HttpOnly, SameSite=Lax)
  │  ③ 302 → 제공자 인가 URL
  ▼
제공자 동의 화면 (kauth.kakao.com / accounts.google.com)
  │
  │  사용자가 동의 또는 취소
  ▼
GET /api/auth/social/{provider}/callback?code=...&state=...
  │  ④ state 대조 (URL 값 == 쿠키 서명 값). 불일치면 즉시 중단
  │  ⑤ code + code_verifier → 토큰 교환 (서버 대 서버)
  │  ⑥ 프로필 조회 → provider_uid 확정
  │  ⑦ social_identity 조회
  ▼
  ├─ 연결됨 ──────→ 세션 쿠키 발급 → 302 {next}
  │
  └─ 미연결 ──────→ 연결 티켓 쿠키(gk_oauth_link, TTL 10분) 발급
                    → 302 /auth/link
                         │
                         ├─ [기존 회원] POST /api/auth/social/link
                         │     {phone, password} → 비밀번호로 소유 증명 → 연결
                         │
                         └─ [처음]     POST /api/auth/social/signup
                               {phone, name, agreed_terms} → signup_open 검사 → 생성
                         ▼
                    세션 쿠키 발급 → /gallery
```

**모든 실패는 `302 /login?social_error={code}`로 끝난다.** 콜백은 브라우저 주소창이 향하는 곳이므로 JSON 오류 봉투를 띄워 봐야 사용자에게는 흰 화면에 영어 덩어리로 보인다. 화면이 코드를 읽어 한국어 배너로 바꾼다.

---

## 4. CSRF·리플레이 방어

| 위협 | 방어 | 구현 |
|---|---|---|
| 공격자가 자기 `code`를 피해자 브라우저에 주입 (로그인 CSRF) | `state` 대조 | URL의 `state`와 서명 쿠키 안의 `state`가 같아야 한다. 쿠키는 우리 오리진에서만 설정되므로 공격자가 만들 수 없다 |
| 인가 코드 가로채기 | **PKCE (S256)** | `code_verifier`는 쿠키에만 있고 URL에 없다. 코드만 훔쳐도 교환할 수 없다 |
| `id_token` 재사용 | `nonce` 대조 | OIDC 제공자(구글·카카오)의 `id_token.nonce`가 쿠키의 값과 같아야 한다 |
| 연결 티켓 탈취 후 임의 계정 연결 | 티켓에 `provider_uid`를 **서명해 봉인** + TTL 10분 + 1회용 | 티켓은 "누구를 연결할지"를 담을 뿐, "어떤 계정에 연결할지"는 담지 않는다. 계정 지정에는 비밀번호가 필요하다 |
| 열린 리다이렉트 | `next` 화이트리스트 | `/`로 시작하고 `//`·`\`로 시작하지 않는 앱 내부 경로만 허용한다. 그 외에는 `/gallery`로 떨어뜨린다 |
| 링크 화면 비밀번호 무차별 대입 | 기존 `login` 스코프 시도 제한 재사용 | 전화번호 기준 5회/10분(API 문서 §2.10) |

`state`·`code_verifier`·`nonce`를 **DB가 아니라 서명 쿠키**에 두는 이유 — Lambda는 인스턴스 메모리를 신뢰할 수 없고(백엔드 §4), 이 값들은 10분 뒤 무의미해진다. DB에 두면 만료 행을 지우는 정리 작업이 하나 더 생긴다. 서명 쿠키는 만료가 곧 소멸이다.

---

## 5. 계정 정책

### 5.1 스키마가 바뀌는 곳은 두 군데다

| 변경 | 내용 | 이유 |
|---|---|---|
| **신규** `social_identity` | `(provider, provider_uid)` UNIQUE, `user_id` FK | DB 문서 §11이 예약해 둔 확장 훅 그대로 |
| **변경** `app_user.password_hash` | `NOT NULL` → **NULL 허용** | 소셜로만 가입한 회원은 비밀번호가 없다 |

`app_user.phone`은 **`NOT NULL`·UNIQUE를 유지한다**(SA-2). 소셜만으로는 계정이 만들어지지 않으며, 반드시 전화번호 연결 화면을 거친다.

### 5.2 그래서 로그인 수단은 회원마다 다르다

| 가입 경로 | `phone` | `password_hash` | `social_identity` |
|---|---|---|---|
| 전화번호 가입 (A-3) | 있음 | 있음 | 없음 |
| 큐레이터 대행 가입 (B-3) | 있음 | 있음(초기 비밀번호) | 없음 |
| 소셜 가입 (A-4) | 있음 | **없음** | 1건 이상 |
| 소셜 연결한 기존 회원 | 있음 | 있음 | 1건 이상 |

`SessionUser.has_password`가 이 사실을 화면에 알린다. `false`면 D 설정 화면이 **비밀번호 변경 항목을 감춘다** — 없는 비밀번호를 바꾸라고 하면 안 된다.

### 5.3 연결 해제 (SA-6)

`DELETE /me/social-identities/{id}`는 다음일 때 `SOCIAL_LAST_IDENTITY`로 거부한다.

```
비밀번호가 없다  AND  이 연결이 마지막 소셜 연결이다
```

화면은 "비밀번호를 먼저 설정해 주세요"로 안내한다.

### 5.4 이미 다른 회원에게 연결된 소셜 계정

`(provider, provider_uid)`가 UNIQUE이므로 두 회원이 같은 카카오 계정을 가질 수 없다. 연결 시도 시 `SOCIAL_ALREADY_LINKED`(409)를 준다. **어느 회원인지는 알려주지 않는다**(SA-5).

---

## 6. 제공자 서술자

흐름 코드는 제공자를 모른다. 아래 표가 `chalicelib/config/oauth.py`의 서술자와 1:1 대응한다.

| | 카카오 | 구글 |
|---|---|---|
| `authorize_url` | `https://kauth.kakao.com/oauth/authorize` | `https://accounts.google.com/o/oauth2/v2/auth` |
| `token_url` | `https://kauth.kakao.com/oauth/token` | `https://oauth2.googleapis.com/token` |
| `profile_url` | `https://kapi.kakao.com/v2/user/me` | `https://openidconnect.googleapis.com/v1/userinfo` |
| `scope` | `openid` | `openid` |
| PKCE | 지원 | 지원 |
| `nonce` | `id_token`에 반영됨 | `id_token`에 반영됨 |
| `provider_uid` 원천 | `id_token.sub` (없으면 프로필 `id`) | `id_token.sub` |
| 이메일 | **받지 않는다** | **받지 않는다** |
| 이름 | **받지 않는다** — 회원 이름은 A-4에서 직접 입력받는다 | 동상 |
| 추가 파라미터 | — | `access_type=online`, `prompt=select_account` |

### 6.1 최소 수집 — `openid` 하나만 요청한다

닉네임도 이메일도 **요청하지 않는다.** 근거는 셋이다.

1. **쓰지 않는다.** 회원 이름은 A-4 연결 화면에서 본인이 직접 입력하고(SA-2), 설정 화면은 제공자 이름과 연결일만 보여준다. 받아도 그릴 곳이 없다.
2. **신원에 필요 없다.** 신원은 `(provider, provider_uid)` 하나뿐이다. 이메일 기반 자동 병합은 제공자가 이메일 소유를 검증하지 않을 때 계정 탈취 경로가 되므로 **애초에 하지 않는다**.
3. **받으면 지킬 책임이 생긴다.** 폐쇄형 서비스의 개인정보 최소 수집 원칙(PRD §8.4)에 어긋나고, 제공자 콘솔의 동의항목·동의 목적 심사가 따라붙는다.

`social_identity.email`·`display_name` 컬럼은 남겨 두되 **항상 `NULL`이다.** 나중에 동의항목을 늘리기로 하면 스키마 변경 없이 scope 한 줄로 열린다 — 컬럼을 지웠다 되살리는 마이그레이션보다 싸다.

**프로필 API도 부르지 않는다.** 검증된 `id_token`에 `sub`가 있으면 그것으로 신원이 확정되므로, `/v2/user/me`를 호출하면 쓰지도 않을 데이터를 받게 된다. 제공자 콘솔에서 OIDC가 꺼져 `id_token`이 없을 때만 대체 경로로 쓴다.

### 6.2 `id_token` 검증

제공자가 OIDC를 지원하면 `id_token`을 **서명 검증한다**. 검증 항목은 `iss`·`aud`·`exp`·`nonce`이며, 서명 키는 제공자 JWKS에서 받아 프로세스 캐시(TTL 1시간)에 둔다.

검증에 실패하면 프로필 API 응답이 아무리 정상이어도 **로그인시키지 않는다** — 토큰 교환 응답을 위조할 수 있는 상대라면 프로필 응답도 위조할 수 있다.

**OIDC는 필수가 아니다.** 제공자 콘솔에서 꺼져 있어 `id_token`이 오지 않으면 프로필 API의 식별자로 대체하며, 로그인은 그대로 성립한다. 켜면 두 겹이 더 붙는다.

| | OIDC ON | OIDC OFF |
|---|---|---|
| 신원의 출처 | `id_token.sub` (서명 검증됨) | 프로필 API의 `id` (TLS만 신뢰) |
| `id_token` 서명 검증 | 있음 | — |
| `nonce` 리플레이 방어 | 있음 | — |
| 인가 코드 가로채기 방어 | PKCE·`state` (동일) | PKCE·`state` (동일) |
| 프로필 API 왕복 | 없음 | 있음 |

**켜는 쪽을 권한다.** 콘솔 스위치 하나로 방어가 두 겹 늘고, 지금 보내는 `scope=openid`와도 일관된다. 끄기로 하면 카카오 서술자의 `scope`를 비워야 하며(OIDC가 꺼진 채 `openid`를 요청하면 제공자가 거부할 수 있다), 그 순간 `nonce` 검증도 의미를 잃는다.

**한 번 정하면 바꾸지 않는다.** 회원이 가입한 뒤 스위치를 반대로 돌리면 신원의 출처가 바뀐다. 제공자가 `sub`와 프로필 `id`를 같은 값으로 주지 않는다면 **같은 사람이 다른 계정이 되어 로그인할 수 없게 된다.** 카카오는 둘 다 회원번호로 같지만, 제공자를 늘릴 때는 이 등가성을 먼저 확인한다.

---

## 7. 리다이렉트 URI

제공자 콘솔에 등록해야 하는 값이다. **경로는 고정이고 오리진만 환경마다 다르다.**

```
{오리진}/api/auth/social/{provider}/callback
```

| 환경 | 카카오 | 구글 |
|---|---|---|
| 로컬 개발 | `http://localhost:5173/api/auth/social/kakao/callback` | `http://localhost:5173/api/auth/social/google/callback` |
| 프로덕션 | `https://{서비스 도메인}/api/auth/social/kakao/callback` | `https://{서비스 도메인}/api/auth/social/google/callback` |

로컬에서 **5173(프런트)**을 쓰는 이유 — Vite dev 서버가 `/api`를 8000으로 프록시하므로 브라우저가 보는 오리진은 5173 하나다. 백엔드 포트를 직접 등록하면 쿠키가 다른 오리진에 심겨 세션이 성립하지 않는다.

서버는 이 값을 `SOCIAL_REDIRECT_BASE_URL` 환경변수 + 고정 경로로 조립한다. **콜백 URI를 요청에서 받지 않는다** — 받으면 열린 리다이렉트가 된다.

---

## 8. 환경변수

| 이름 | 필수 | 설명 |
|---|:---:|---|
| `SOCIAL_REDIRECT_BASE_URL` | 소셜 사용 시 | 브라우저가 보는 오리진. 예: `https://gallery-k.example.com` |
| `KAKAO_CLIENT_ID` | 카카오 사용 시 | 카카오 REST API 키 |
| `KAKAO_CLIENT_SECRET` | **콘솔 설정에 따름** | 카카오 콘솔의 `보안 > Client Secret`이 **활성화(ON)면 필수**다. OFF면 비워 둔다 |
| `GOOGLE_CLIENT_ID` | 구글 사용 시 | |
| `GOOGLE_CLIENT_SECRET` | 구글 사용 시 | 웹 애플리케이션 클라이언트는 항상 요구한다 |

**한 제공자는 `client_id`가 있을 때만 켜진다.** 키가 없으면 그 제공자는 목록에서 빠지고, 화면에 버튼도 뜨지 않는다. 프런트는 `GET /public/landing`이 아니라 `GET /auth/social/providers`로 켜진 목록을 받는다 — 화면이 환경변수를 알 필요가 없다.

### 8.1 `client_secret`이 어긋났을 때

토큰 교환 요청에는 `client_secret`이 **설정되어 있을 때만** 실린다. 빈 문자열을 보내면 오히려 거부하는 제공자가 있기 때문이다.

문제는 **서버가 제공자 콘솔의 설정을 알 수 없다**는 점이다. 콘솔에서 secret을 켜 두고 환경변수를 비워 두면 이렇게 된다.

```
버튼이 보인다 → 동의 화면까지 간다 → 사용자가 동의한다
                                        → 콜백에서 토큰 교환 거부
                                        → /login?social_error=SOCIAL_EXCHANGE_FAILED
```

`client_id`만으로 제공자를 켜는 판정에 secret을 넣지 않는 이유는, secret이 **정당하게 비어 있을 수 있기** 때문이다(카카오 OFF). 대신 교환 실패 시 `oauth.token.failed` 로그에 `client_secret_sent`를 함께 남긴다 — 상태 코드만으로는 이 원인이 드러나지 않고, 사용자가 동의를 마친 뒤에야 실패하므로 재현이 번거롭다.

**증상이 위와 같다면 콘솔의 secret 설정과 환경변수를 먼저 대조한다.**

---

## 9. 엔드포인트

| 메서드 | 경로 | 권한 | 응답 |
|---|---|---|---|
| `GET` | `/auth/social/providers` | PUBLIC | 봉투 — 켜진 제공자 목록 |
| `GET` | `/auth/social/{provider}/start` | PUBLIC | **302** → 제공자 |
| `GET` | `/auth/social/{provider}/callback` | PUBLIC | **302** → 앱 |
| `POST` | `/auth/social/link` | PUBLIC | 봉투 — `{user}` + 세션 쿠키 |
| `POST` | `/auth/social/signup` | PUBLIC | 봉투 — `{user}` + 세션 쿠키 |
| `GET` | `/me/social-identities` | MEMBER | 봉투 — 연결 목록 |
| `DELETE` | `/me/social-identities/{identity_id}` | MEMBER | 봉투 — `{}` |

`start`·`callback` 둘은 **봉투 규약의 두 번째 예외**다(첫 번째는 `304`, API 문서 §2.9). 브라우저 내비게이션의 종착지이므로 JSON이 아니라 `Location` 헤더가 응답의 본체다. 계약 테스트가 이 둘을 명시적으로 면제한다.

### 9.1 `GET /auth/social/providers`

```json
{ "providers": [ { "provider": "kakao", "label": "카카오", "start_url": "/api/auth/social/kakao/start" } ] }
```

### 9.2 `POST /auth/social/link`

연결 티켓 쿠키 + `{ "phone": "01012345678", "password": "..." }`.
비밀번호가 맞아야 연결된다. 실패는 `AUTH_INVALID_CREDENTIALS` 하나로 수렴한다(SA-5).

### 9.3 `POST /auth/social/signup`

연결 티켓 쿠키 + `{ "phone": "...", "name": "...", "agreed_terms": true }`.
`signup_open`이 꺼져 있으면 `SIGNUP_CLOSED`. 번호가 이미 있으면 `SIGNUP_PHONE_TAKEN`.
생성되는 계정은 `password_hash = NULL`, `created_via = 'social'`이다.

---

## 10. 오류 코드

| code | HTTP | message(기본) | retryable |
|---|---|---|:---:|
| `SOCIAL_PROVIDER_UNKNOWN` | 404 | 지원하지 않는 로그인 방식입니다. | false |
| `SOCIAL_DISABLED` | 503 | 지금은 이 방식으로 로그인할 수 없습니다. | true |
| `SOCIAL_STATE_INVALID` | 400 | 로그인 요청이 만료되었습니다. 처음부터 다시 시도해 주세요. | false |
| `SOCIAL_EXCHANGE_FAILED` | 502 | 로그인 제공자와 연결하지 못했습니다. 잠시 후 다시 시도해 주세요. | true |
| `SOCIAL_LINK_EXPIRED` | 400 | 연결 시간이 지났습니다. 처음부터 다시 시도해 주세요. | false |
| `SOCIAL_ALREADY_LINKED` | 409 | 이미 다른 계정에 연결된 소셜 계정입니다. | false |
| `SOCIAL_LAST_IDENTITY` | 409 | 마지막 로그인 수단은 해제할 수 없습니다. 비밀번호를 먼저 설정해 주세요. | false |

`302`로 끝나는 두 경로는 이 코드를 `?social_error=` 쿼리로 실어 보내고, 화면이 같은 문구로 번역한다.

---

## 11. 화면

| 화면 | 변경 |
|---|---|
| **A-1 로그인** | 전화번호 폼 아래 구분선 + 제공자 버튼. 버튼은 `<a href="/api/auth/social/{p}/start?next=...">`이며 **JS 이벤트 핸들러가 아니다** |
| **A-4 계정 연결** *(신규)* | `/auth/link`. 기본은 "이미 회원이신가요?"(전화번호+비밀번호), 하단 링크로 "처음이신가요?"(전화번호+이름+약관)로 전환 |
| **D 설정** | `연결된 로그인` 섹션 — 연결 목록·해제, 미연결 제공자 연결 버튼. `has_password=false`면 비밀번호 변경 항목을 감춘다 |

A-1의 소셜 버튼이 `<a>`인 것이 중요하다. `onClick`으로 `location.href`를 바꾸면 JS 로드 전 클릭이 무반응이고, 대상 사용자는 반응 없는 버튼을 두 번 세 번 누른다.

---

## 12. 이 문서가 바꾸는 상위 문서

| 문서 | 변경 |
|---|---|
| `01-DATABASE-MODEL.md` | §4에 `social_identity` 추가 · `app_user.password_hash` NULL 허용 · §11 확장 훅에서 소셜 로그인 행 제거(구현됨) |
| `02-API-SPEC.md` | §3.6 `has_password` · §4 총람 7행 · §5.2 오류 7종 · §6.11–§6.15 · §8.7–§8.8 |
| `PRD.md` | 로드맵 표에서 카카오 로그인을 MVP로 이동하고 구글을 추가 |
| `06-USER-EXPERIENCE.md` | A-1 개정 · A-4 신규 · D 개정 |
