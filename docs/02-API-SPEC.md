# 갤러리 K — API 명세서

| | |
|---|---|
| **문서 버전** | v1.0 |
| **작성일** | 2026-08-27 |
| **상위 문서** | `docs/PRD.md` v1.1, `docs/01-DATABASE-MODEL.md` v1.0 |
| **런타임** | AWS Chalice (API Gateway REST + Lambda) |
| **기준 URL** | `https://{도메인}/api` |
| **상태** | 확정 (구현 기준선) |

---

## 1. 설계 원칙

| # | 원칙 | 적용 |
|---|---|---|
| **AP-1** | **응답 봉투를 단일화한다** | 성공·실패 모두 동일한 최상위 구조를 갖는다. 프런트엔드는 단 하나의 응답 파서와 단 하나의 오류 처리 경로만 구현한다 |
| **AP-2** | **오류는 코드로 말한다** | 사용자 문구는 서버가 주지만, 분기는 항상 `error.code`로 한다. 문구 변경이 프런트 로직을 깨뜨리지 않는다 |
| **AP-3** | **화면 단위로 응답을 설계한다** | "3번의 탭 안에"(제품 원칙 3)를 지키려면 화면 진입당 왕복 1회가 원칙이다. 리소스 순수주의보다 화면 성능이 우선이다 |
| **AP-4** | **부수효과는 GET에 두지 않는다** | 입장·열람 기록은 별도 POST로 분리한다. 조회 응답이 캐시 가능해야 오프라인 캐시(PWA)가 성립한다 |
| **AP-5** | **목록은 예외 없이 페이지네이션 규약을 따른다** | 항목이 30개뿐인 목록도 동일한 `meta.pagination` 구조를 반환한다. 프런트의 목록 훅이 하나로 유지된다 |
| **AP-6** | **관람자 API는 관리 정보를 절대 노출하지 않는다** | 드래프트·발행 상태·회원 정보는 `/admin/*` 아래에만 존재한다. 응답 필드 수준에서 분리한다 |
| **AP-7** | **모든 응답에 `request_id`를 담는다** | 서버리스 환경에서 사용자 문의를 로그와 연결하는 유일한 수단이다 |

---

## 2. 공통 규약

### 2.1 엔드포인트 규약

| 항목 | 규약 |
|---|---|
| 프리픽스 | `/api` 하나뿐이다. CloudFront가 정적 자산과 API의 오리진을 가르는 데 필요한 최소 경로이며, 버전 프리픽스는 두지 않는다 |
| 경로 | 소문자 `kebab-case` 복수 명사. 동사는 하위 액션 세그먼트로만 (`/exhibitions/{date}/hide`) |
| 경로 변수 | 전시는 **날짜**(`YYYY-MM-DD`)로 식별한다. 큐레이터에게 전시의 자연키는 날짜이고 URL 가독성이 운영 실수를 줄인다. 그림·회원은 UUID |
| 필드명 | `snake_case`. 프런트엔드는 API 계층 경계에서만 이를 다루고 도메인 타입으로 변환한다 |
| 날짜 | `YYYY-MM-DD` (KST 캘린더) |
| 시각 | RFC 3339 UTC (`2026-08-27T22:30:00Z`). 표시 변환은 클라이언트 책임 |
| 시각(시분) | `HH:MM` 24시간 (KST). 알림 시각 전용 |
| 불리언 | JSON `true`/`false`. `"Y"/"N"` 같은 문자열 플래그를 쓰지 않는다 |
| null | 값 없음은 `null`. 키 자체를 생략하지 않는다 — 프런트 타입이 옵셔널 지옥이 되는 것을 막는다 |
| 빈 목록 | `[]`. `null`이 아니다 |

### 2.2 표준 응답 봉투

**성공**

| 필드 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| `success` | boolean | ● | 항상 `true` |
| `data` | object \| array \| null | ● | 리소스 본문. 액션형 API도 최소 `{}`를 반환한다 |
| `meta` | object | ● | 아래 §2.3 |
| `error` | null | ● | 항상 `null` |

**실패**

| 필드 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| `success` | boolean | ● | 항상 `false` |
| `data` | null | ● | 항상 `null` |
| `meta` | object | ● | §2.3 |
| `error` | object | ● | §2.5 |

성공·실패의 키 집합이 **완전히 동일**하다. 프런트엔드는 `success` 하나만 보고 분기하며, 타입 정의도 판별 유니온 하나로 끝난다.

**봉투 규약의 예외는 셋뿐이다.**

| 예외 | 응답 | 이유 |
|---|---|---|
| `304 Not Modified`(§2.9) | 본문 없음 | 조건부 요청의 정의상 본문을 보내지 않는다 |
| `GET /auth/social/{provider}/start`(§6.12) | `302` + `Location` | 브라우저 내비게이션의 종착지다. 응답의 본체가 헤더다 |
| `GET /auth/social/{provider}/callback`(§6.13) | `302` + `Location` | 동상 |

셋 다 **계약 테스트가 이름으로 면제**한다. 면제 목록에 없는 새 경로가 봉투를 벗어나면 빌드가 실패한다.

### 2.3 `meta` 구조

| 필드 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| `request_id` | string | ● | 요청 추적 ID(26자 ULID). 응답 헤더 `X-Request-Id`와 동일 |
| `server_time` | string | ● | 서버 시각(RFC 3339 UTC) |
| `server_date` | string | ● | 서버 기준 **KST 오늘 날짜**. 클라이언트는 단말 시계로 날짜를 계산하지 않는다(PRD §6.1) |
| `api_version` | string | ● | `v1` |
| `pagination` | object \| null | ○ | 목록 응답에만. §2.4 |
| `deprecation` | object \| null | ○ | 폐기 예정 엔드포인트에만. `{sunset_on, replacement}` |

### 2.4 페이지네이션 규약

두 가지 모드를 두고 **응답 구조는 동일**하게 유지한다.

| 필드 | 타입 | 설명 |
|---|---|---|
| `mode` | string | `cursor` \| `page` |
| `limit` | integer | 이번 응답의 요청 크기 |
| `count` | integer | 이번 응답의 실제 항목 수 |
| `has_more` | boolean | 다음 페이지 존재 여부 |
| `next_cursor` | string \| null | `mode=cursor`일 때만 유효 |
| `page` | integer \| null | `mode=page`일 때만 유효 (1부터) |
| `total_count` | integer \| null | `mode=page`일 때만 유효 |
| `total_pages` | integer \| null | `mode=page`일 때만 유효 |

**모드 선택 기준**

| 모드 | 사용처 | 이유 |
|---|---|---|
| `cursor` | 아카이브(C-3), 관리자 달력 과거 스크롤 | 시간순 무한 스크롤. 삽입으로 인한 페이지 밀림이 없다 |
| `page` | 회원 목록(B-3), 통계 목록 | 전체 개수와 페이지 이동이 필요한 관리 화면 |

**요청 파라미터**

| 파라미터 | 모드 | 기본 | 최대 | 설명 |
|---|---|---|---|---|
| `limit` | 공통 | 엔드포인트별 | 100 | |
| `cursor` | cursor | — | — | 직전 응답의 `next_cursor`를 그대로 전달. **불투명 문자열**이며 클라이언트가 해석하지 않는다 |
| `page` | page | 1 | — | |

커서는 `base64url(json({"k": 정렬키, "id": 타이브레이커}))` 형식이며 서버 내부 규약이다. 잘못된 커서는 `400 PAGINATION_INVALID_CURSOR`.

### 2.5 오류 구조

| 필드 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| `code` | string | ● | §5 카탈로그의 값. `SCREAMING_SNAKE_CASE` |
| `message` | string | ● | **최종 사용자에게 그대로 보여줄 수 있는 한국어 문장.** 기술 용어·스택·식별자를 담지 않는다 |
| `field_errors` | array \| null | ● | 입력 검증 실패 시에만 채워진다. 아래 구조 |
| `details` | object \| null | ● | 코드별 부가 정보(§5의 `details` 열). 없으면 `null` |
| `retryable` | boolean | ● | 동일 요청 재시도로 해결될 수 있는지. 클라이언트 자동 재시도 판단 근거 |
| `doc_hint` | string \| null | ● | 개발 환경에서만 채워지는 원인 요약. 프로덕션에서는 항상 `null` |

**`field_errors[]` 항목**

| 필드 | 타입 | 설명 |
|---|---|---|
| `field` | string | 요청 바디 기준 경로. 중첩은 점 표기, 배열은 인덱스 (`artworks.3.description`) |
| `code` | string | `REQUIRED` \| `TOO_LONG` \| `TOO_SHORT` \| `INVALID_FORMAT` \| `OUT_OF_RANGE` \| `NOT_ALLOWED` |
| `message` | string | 해당 필드 옆에 그대로 출력할 한국어 문장 |
| `limit` | number \| null | 길이·범위 제약 값 (예: 300) |

프런트엔드는 `field_errors`를 폼 라이브러리의 필드 오류로 그대로 매핑하고, 비어 있으면 `error.message`를 전역 토스트로 띄운다. **이 두 갈래 외의 오류 표시 경로를 만들지 않는다.**

### 2.6 목록 필터·정렬 규약

| 항목 | 규약 |
|---|---|
| 필터 | 최상위 쿼리 파라미터로 노출한다. 이름은 필드명과 일치시킨다 (`status`, `blocked`, `from`, `to`) |
| 다중 값 | 콤마 구분 (`status=blocked,active`) |
| 기간 | 항상 `from`·`to` 쌍(포함). 날짜 형식 `YYYY-MM-DD`. `from > to`이면 `400 VALIDATION_FAILED` |
| 검색어 | `query` 단일 파라미터. 서버가 대상 필드를 결정한다 (회원: 이름 부분일치 또는 전화번호 완전일치) |
| 정렬 | `sort` 단일 파라미터. `-` 접두는 내림차순 (`sort=-created_at`). 엔드포인트별 허용 목록 외의 값은 `400 QUERY_INVALID_SORT` |
| 미지원 파라미터 | **무시하지 않고 `400 QUERY_UNKNOWN_PARAM`으로 거부한다.** 오타로 필터가 조용히 풀리는 사고를 막는다 |

### 2.7 인증·세션

| 항목 | 규약 |
|---|---|
| 방식 | JWT(HS256) 를 **HttpOnly 쿠키**로 전달. 요청 본문·헤더에 토큰을 싣지 않는다 |
| 쿠키명 | `gk_session` |
| 쿠키 속성 | `HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=7776000`(90일) |
| 클레임 | `sub`(user_id), `role`, `tv`(token_version), `iat`, `exp`, `jti` |
| 갱신 | 만료 30일 이내이면 응답에서 **자동 재발급**한다(슬라이딩 세션). 클라이언트는 아무 것도 하지 않는다 |
| 무효화 | `app_user.token_version`과 클레임 `tv`가 다르면 즉시 거부(`401 AUTH_SESSION_REVOKED`) |
| CSRF | `SameSite=Lax` + 변경 요청에 `X-Requested-With: gallery-k` 헤더 필수. 헤더 없으면 `403 CSRF_HEADER_MISSING` |
| 미디어 | 별도 자격증명 없음. 이미지 URL 자체가 만료 있는 presigned GET URL이다. §6.16 |
| 소셜 로그인 | OAuth 2.0 Authorization Code + PKCE. **리다이렉트 방식만 쓴다**(팝업·iframe 금지). 성립 후에는 위 `gk_session` 쿠키 하나로 수렴하며, 제공자 토큰은 저장하지 않는다. 상세는 `08-SOCIAL-AUTH.md` |
| 소셜 임시 쿠키 | `gk_oauth`(인가 왕복용 `state`·PKCE·nonce) · `gk_oauth_link`(연결 티켓). 둘 다 `HttpOnly; SameSite=Lax`, TTL 10분, 사용 즉시 삭제 |

**권한 등급**

| 등급 | 표기 | 조건 |
|---|---|---|
| 공개 | `PUBLIC` | 인증 불필요. 비로그인 접근 가능 |
| 회원 | `MEMBER` | 유효 세션 필요 |
| 관리자 | `CURATOR` | 유효 세션 + `role='curator'` |

`CURATOR` 판정은 **서버에서만** 수행한다(PRD §8.4). 관리자 엔드포인트에 `MEMBER`가 접근하면 `404 NOT_FOUND`가 아니라 `403 AUTH_FORBIDDEN`을 반환한다 — 폐쇄형 서비스이고 회원은 이미 신뢰 관계 안에 있으므로 존재를 숨길 이유가 없다.

### 2.8 HTTP 상태 코드 사용 원칙

| 코드 | 사용 |
|---|---|
| `200` | 조회·수정·액션 성공 |
| `201` | 리소스 신규 생성(가입, 대행 가입, 공지 생성) |
| `204` | 사용하지 않는다 — 봉투를 항상 반환하기 위해 `200` + `data: {}` |
| `400` | 파라미터 형식·조합 오류 |
| `401` | 미인증·세션 만료·자격 증명 불일치 |
| `403` | 권한 부족·정책상 금지(가입 잠금, CSRF) |
| `404` | 리소스 없음 |
| `409` | 상태 충돌(중복 가입, 버전 충돌, 백필 시도) |
| `413` | 업로드 용량 초과 |
| `422` | 스키마 검증 실패(`field_errors` 포함) |
| `429` | 요청 제한 |
| `500` | 서버 내부 오류 |
| `503` | 점검 모드·의존 서비스 장애 |

### 2.9 캐싱·조건부 요청

| 대상 | 헤더 | 근거 |
|---|---|---|
| `GET /public/landing` | `Cache-Control: private, max-age=60` | 1분 이내 재방문에서 재요청하지 않는다 |
| `GET /exhibitions/current` | `Cache-Control: private, max-age=0, must-revalidate` + `ETag` | 발행 즉시 반영되어야 하나 본문 전송은 아낀다 |
| `GET /exhibitions/{date}` | `Cache-Control: private, max-age=300` + `ETag` | 과거 전시는 거의 불변 |
| 관리자 전 API | `Cache-Control: no-store` | 운영 데이터는 캐시하지 않는다 |
| 액션·기록 API | `no-store` | |

`ETag`는 전시의 `updated_at` + `version`으로 생성한다. 클라이언트가 `If-None-Match`를 보내고 일치하면 `304`를 반환하며, 이때 본문은 비어 있다 — **`304`는 봉투 규약의 유일한 예외**이며 프런트 HTTP 클라이언트가 캐시 본문으로 대체한다.

### 2.10 요청 제한

| 스코프 | 한도 | 초과 시 |
|---|---|---|
| 로그인(전화번호별) | 5회 연속 실패 → 10분 차단 | `429 AUTH_TOO_MANY_ATTEMPTS`, `details.retry_after_seconds` |
| 가입(IP별) | 10회 / 1시간 | `429 RATE_LIMITED` |
| 비밀번호 재설정 요청(전화번호별) | 5회 / 1시간, 재발송 60초 간격 | `429 RATE_LIMITED` |
| 업로드 URL 발급 | 60회 / 10분 | `429 RATE_LIMITED` |
| 기타 인증 API | 300회 / 분 (API Gateway 스로틀) | `429 RATE_LIMITED` |

응답에 `Retry-After` 헤더를 함께 보낸다.

### 2.11 CORS

프런트엔드와 API는 **동일 오리진**으로 배포한다(CloudFront 단일 배포에서 `/api/*`를 API Gateway로 오리진 분기). 따라서 프로덕션에서 CORS 프리플라이트가 발생하지 않으며, 쿠키의 `SameSite=Lax`가 그대로 유효하다. 로컬 개발에서만 `http://localhost:5173`을 허용 오리진으로 두고 `credentials: true`를 켠다.

### 2.12 멱등성

| 유형 | 처리 |
|---|---|
| 기록 API(`.../view`) | 서버 측 UPSERT로 자연 멱등. 중복 호출은 `200`과 동일 결과 |
| 액션 API(차단, 숨김 등) | 목표 상태 지정형(`block`/`unblock`)이라 자연 멱등. 이미 그 상태면 `200`으로 성공 처리 |
| 생성 API(가입, 공지 생성) | 자연키 충돌로 `409` |
| 업로드 URL 발급 | 발급마다 새 키. 멱등하지 않음 |

별도의 `Idempotency-Key` 헤더 체계는 도입하지 않는다 — 결제가 없고 모든 변경 API가 위 네 유형 중 하나에 들어간다.

---

## 3. 공용 리소스 스키마

각 엔드포인트는 아래 스키마를 조합해 응답한다. 동일 개념이 화면마다 다른 모양으로 나가는 것을 금지한다.

### 3.1 `ImageSet` — 그림 이미지 3종

| 필드 | 타입 | Null | 설명 |
|---|---|:---:|---|
| `thumb_url` | string | N | 400×400 WebP. C 그리드용 |
| `display_url` | string | N | 긴 변 1600px WebP. C-2용 |
| `origin_url` | string | Y | 원본. **전체 화면 확대 요청 시에만 사용**하며 그 외에는 미리 로드하지 않는다 |
| `lqip` | string | Y | 16px 폭 WebP data URL. 블러 플레이스홀더 |
| `width` | integer | Y | 원본 픽셀 폭 |
| `height` | integer | Y | 원본 픽셀 높이 |
| `aspect_ratio` | number | Y | `width/height`. 소수점 4자리. 레이아웃 시프트 방지용 |

URL은 **응답 시점에 발급되는 presigned GET URL**이며 만료가 있다(§6.10). 응답 본문은 캐시하지 않고, 이미지 바이트만 브라우저·CDN 캐시가 받는다.

### 3.2 `ArtworkSummary` — 그리드용 그림 요약

| 필드 | 타입 | Null | 설명 |
|---|---|:---:|---|
| `id` | string(uuid) | N | |
| `position` | integer | N | 1–12 |
| `artist` | string | N | C 그리드에는 작가명만 노출(PRD §6.5) |
| `title` | string | N | 대체 텍스트 구성용. 그리드에 시각적으로 표시하지 않는다 |
| `image` | ImageSet | **Y** | 이미지가 아직 `ready`가 아니면 `null`이다. **프런트가 자리표시자를 그린다**(§9.12). 발행된 전시는 12점이 모두 `ready`여야 하므로 관람자 경로에서는 사실상 채워져 있지만, 미리보기는 미완성 상태를 그대로 보여준다 |
| `is_viewed` | boolean | N | 이 회원이 **이 전시에서** 이미 열어봤는지 |

### 3.3 `ArtworkDetail` — 그림 상세

`ArtworkSummary`의 모든 필드에 더해:

| 필드 | 타입 | Null | 설명 |
|---|---|:---:|---|
| `year_text` | string | N | `1665년경` |
| `description` | string | N | 최대 300자. 줄바꿈 보존 |
| `collection` | string | Y | 소장처 |
| `source_url` | string | Y | 출처 |
| `prev_artwork_id` | string(uuid) | Y | 스와이프 대상. 첫 점이면 `null` |
| `next_artwork_id` | string(uuid) | Y | 마지막 점이면 `null` |

### 3.4 `ExhibitionSummary` — 전시 요약(아카이브 목록용)

| 필드 | 타입 | Null | 설명 |
|---|---|:---:|---|
| `exhibition_date` | string(date) | N | 발행일 |
| `title` | string | N | |
| `cover_image` | ImageSet | Y | 1번 슬롯 그림의 이미지 |
| `artwork_count` | integer | N | 항상 12 (발행된 전시만 노출되므로) |
| `viewed_artwork_count` | integer | N | 이 회원이 이 전시에서 열어본 그림 수 |
| `is_viewed` | boolean | N | `viewed_artwork_count > 0` |

### 3.5 `ExhibitionDetail` — 전시 상세(C 화면)

| 필드 | 타입 | Null | 설명 |
|---|---|:---:|---|
| `exhibition_date` | string(date) | N | **발행일** |
| `title` | string | N | 20자 이내 |
| `theme` | string | N | 500자 이내. 줄바꿈 보존 |
| `artists` | array\<string> | N | 중복 제거된 작가 목록. C-1 하단용(PRD §6.6) |
| `artworks` | array\<ArtworkSummary> | N | `position` 오름차순 12건 |
| `viewing_date` | string(date) | N | **관람일**. 서버 기준 오늘 |
| `is_carried_over` | boolean | N | `exhibition_date < viewing_date` |
| `carried_over_label` | string | Y | 연장 시에만 `8월 30일의 전시` 형태. 서버가 완성된 문구로 준다 |
| `is_archive_view` | boolean | N | 아카이브에서 특정 날짜를 열었는지 |

`is_carried_over`와 `carried_over_label`을 **서버가 계산해서 준다.** 클라이언트가 날짜를 비교해 문구를 만들면 단말 시계 오차가 UI에 새어 나온다(PRD §6.1).

### 3.6 `SessionUser` — 세션 사용자

| 필드 | 타입 | Null | 설명 |
|---|---|:---:|---|
| `id` | string(uuid) | N | |
| `name` | string | N | |
| `phone_masked` | string | N | `010-****-5678`. **전체 전화번호는 어떤 관람자 API에서도 반환하지 않는다** |
| `role` | string | N | `viewer` \| `curator` |
| `font_scale` | string | N | `normal` \| `large` |
| `notify_enabled` | boolean | N | |
| `notify_at` | string(HH:MM) | N | |
| `must_change_password` | boolean | N | true면 프런트가 비밀번호 변경 화면으로 유도 |
| `has_password` | boolean | N | false면 **소셜로만 로그인하는 계정**이다. D 설정 화면이 비밀번호 변경 항목을 감춘다(소셜 문서 §5.2) |
| `created_at` | string(datetime) | N | |

### 3.7 `NoticeItem` — 휴관 공지

| 필드 | 타입 | Null | 설명 |
|---|---|:---:|---|
| `id` | string(uuid) | N | |
| `starts_on` / `ends_on` | string(date) | N | 포함 구간 |
| `body` | string | N | 최대 300자 |
| `is_active` | boolean | N | |

### 3.8 `MemberItem` — 회원 목록 항목(관리자 전용)

| 필드 | 타입 | Null | 설명 |
|---|---|:---:|---|
| `id` | string(uuid) | N | |
| `name` | string | N | |
| `phone` | string | N | **관리자 응답에서만 전체 번호를 반환**한다(B-3이 전화 한 통으로 돕는 화면이므로) |
| `role` | string | N | |
| `created_at` | string(datetime) | N | 가입일 |
| `created_via` | string | N | `self` \| `curator` |
| `is_blocked` | boolean | N | |
| `blocked_at` | string(datetime) | Y | |
| `notify_enabled` | boolean | N | |
| `notify_at` | string(HH:MM) | N | |
| `push_status` | string | N | `active` \| `inactive` \| `none`. 구독은 있는데 실패 중이면 `inactive` |
| `push_platforms` | array\<string> | N | `["ios"]` 등. iOS 안내가 필요한 회원을 식별 |
| `last_login_at` | string(datetime) | Y | |
| `last_viewed_on` | string(date) | Y | 마지막 입장 관람일 |

### 3.9 `AdminExhibitionDay` — 관리자 달력 행

| 필드 | 타입 | Null | 설명 |
|---|---|:---:|---|
| `date` | string(date) | N | 달력의 날짜 |
| `status` | string | N | `published`(Y) \| `carried_over`(↑) \| `empty`(N) |
| `title` | string | Y | 그 날짜 전시 제목(드래프트 포함) |
| `carried_from_date` | string(date) | Y | `carried_over`일 때 실제로 걸린 전시의 발행일 |
| `carried_from_title` | string | Y | 위 전시의 제목 |
| `has_draft` | boolean | N | 미발행 작업물 존재 여부 |
| `draft_progress` | object | N | `{artwork_count, complete_artwork_count, has_title, has_theme}` |
| `is_hidden` | boolean | N | 숨김 처리된 전시 |
| `is_editable` | boolean | N | `UP` 버튼 활성 여부 |
| `edit_mode` | string | N | `create`(신규 작성) \| `edit`(수정) \| `carry_draft`(이어쓰기 제안) \| `locked`(불가) |
| `is_today` | boolean | N | |
| `updated_at` | string(datetime) | Y | |

`edit_mode`를 **서버가 결정**한다. 백필 금지·이어쓰기 조건은 도메인 규칙이며 프런트가 날짜 비교로 재구현하면 규칙이 두 곳에 존재하게 된다.

### 3.10 `SocialIdentity` — 연결된 외부 계정

| 필드 | 타입 | Null | 설명 |
|---|---|:---:|---|
| `id` | string(uuid) | N | |
| `provider` | string | N | `kakao` \| `google` |
| `label` | string | N | 화면에 그대로 쓰는 한국어 이름. 예: `카카오` |
| `email` | string | Y | **항상 null.** `openid` scope만 요청하므로 수집하지 않는다(소셜 문서 §6.1) |
| `display_name` | string | Y | **항상 null.** 동상 |
| `linked_at` | string(datetime) | N | |
| `last_login_at` | string(datetime) | Y | |

**제공자 access token·refresh token은 어떤 응답에도 담기지 않는다.** 로그인이 성립한 뒤 서버가 버린다(소셜 문서 SA-3).

---

## 4. 엔드포인트 총람

| # | 메서드 | 경로 | 권한 | 설명 | 릴리스 |
|---|---|---|---|---|---|
| 1 | GET | `/public/landing` | PUBLIC | A 첫 화면 통합 조회 | MVP |
| 2 | GET | `/public/notice` | PUBLIC | 현재 유효 휴관 공지 | MVP |
| 3 | POST | `/auth/signup` | PUBLIC | 회원가입 | MVP |
| 4 | POST | `/auth/login` | PUBLIC | 로그인 | MVP |
| 5 | POST | `/auth/logout` | MEMBER | 로그아웃 | MVP |
| 6 | GET | `/auth/session` | PUBLIC | 세션 확인 | MVP |
| 7 | POST | `/auth/password` | MEMBER | 비밀번호 변경 | MVP |
| 8 | POST | `/auth/password/reset/request` | PUBLIC | 재설정 인증번호 발송 | v1.1 |
| 9 | POST | `/auth/password/reset/confirm` | PUBLIC | 인증번호 확인 + 새 비밀번호 | v1.1 |
| 10 | GET | `/auth/social/providers` | PUBLIC | 켜진 소셜 제공자 목록 | MVP |
| 11 | GET | `/auth/social/{provider}/start` | PUBLIC | **302** 제공자 인가 화면으로 | MVP |
| 12 | GET | `/auth/social/{provider}/callback` | PUBLIC | **302** 앱으로(세션 발급 또는 연결 화면) | MVP |
| 13 | POST | `/auth/social/link` | PUBLIC | 기존 계정에 연결(비밀번호로 소유 증명) | MVP |
| 14 | POST | `/auth/social/signup` | PUBLIC | 소셜 신규 가입(전화번호+이름) | MVP |
| 15 | GET | `/exhibitions/current` | MEMBER | 현재 전시(C 화면) | MVP |
| 16 | GET | `/exhibitions/{date}` | MEMBER | 특정 발행일 전시 | MVP |
| 17 | GET | `/exhibitions` | MEMBER | 아카이브 목록(C-3) | MVP |
| 18 | POST | `/exhibitions/{date}/view` | MEMBER | 입장 기록 | MVP |
| 19 | GET | `/artworks/{id}` | MEMBER | 그림 상세(C-2) | MVP |
| 20 | POST | `/artworks/{id}/view` | MEMBER | 그림 열람 기록 | MVP |
| 21 | GET | `/me` | MEMBER | 내 정보 | MVP |
| 22 | PATCH | `/me/settings` | MEMBER | 알림·글씨 설정 변경(C-4) | MVP |
| 23 | DELETE | `/me` | MEMBER | 탈퇴 | MVP |
| 24 | POST | `/me/push-subscriptions` | MEMBER | 푸시 구독 등록·갱신 | MVP |
| 25 | GET | `/me/push-subscriptions` | MEMBER | 이 회원의 푸시 구독 목록 | MVP |
| 26 | DELETE | `/me/push-subscriptions/{id}` | MEMBER | 푸시 구독 해제 | MVP |
| 27 | GET | `/me/social-identities` | MEMBER | 연결된 소셜 계정 목록 | MVP |
| 28 | DELETE | `/me/social-identities/{identity_id}` | MEMBER | 소셜 연결 해제 | MVP |
| 29 | GET | `/admin/summary` | CURATOR | B 홈 요약 숫자 | MVP |
| 30 | GET | `/admin/exhibitions/calendar` | CURATOR | 날짜별 발행 상태(B) | MVP |
| 31 | GET | `/admin/exhibitions/{date}` | CURATOR | 전시 편집 상태 조회(B-2) | MVP |
| 32 | PUT | `/admin/exhibitions/{date}` | CURATOR | 제목·테마 저장(B-2-1) | MVP |
| 33 | POST | `/admin/exhibitions/{date}/hide` | CURATOR | 전시 숨김 | MVP |
| 34 | POST | `/admin/exhibitions/{date}/unhide` | CURATOR | 숨김 해제 | MVP |
| 35 | POST | `/admin/exhibitions/{date}/carry-draft` | CURATOR | 드래프트 오늘로 이어쓰기 | MVP |
| 36 | GET | `/admin/exhibitions/{date}/preview` | CURATOR | 관람자 화면과 동일 렌더용 | MVP |
| 37 | PUT | `/admin/exhibitions/{date}/artworks/{position}` | CURATOR | 그림 메타 저장(B-2-2) | MVP |
| 38 | DELETE | `/admin/exhibitions/{date}/artworks/{position}` | CURATOR | 슬롯 비우기 | MVP |
| 39 | POST | `/admin/exhibitions/{date}/artworks/reorder` | CURATOR | 순서 변경 | MVP |
| 40 | POST | `/admin/exhibitions/{date}/artworks/upload-urls` | CURATOR | presigned POST 자격 다중 발급 | MVP |
| 41 | POST | `/admin/artworks/{id}/image/complete` | CURATOR | 업로드 완료 통지 + 동기 이미지 처리 | MVP |
| 42 | GET | `/admin/members` | CURATOR | 회원 목록(B-3) | MVP |
| 43 | POST | `/admin/members` | CURATOR | 대행 가입 | MVP |
| 44 | POST | `/admin/members/{id}/block` | CURATOR | 차단 | MVP |
| 45 | POST | `/admin/members/{id}/unblock` | CURATOR | 차단 해제 | MVP |
| 46 | POST | `/admin/members/{id}/reset-password` | CURATOR | 비밀번호 초기화 | MVP |
| 47 | GET | `/admin/settings` | CURATOR | 전역 설정 조회 | MVP |
| 48 | PATCH | `/admin/settings` | CURATOR | 전역 설정 변경(가입 잠금 포함) | MVP |
| 49 | GET | `/admin/notices` | CURATOR | 공지 목록 | MVP |
| 50 | POST | `/admin/notices` | CURATOR | 공지 생성 | MVP |
| 51 | PATCH | `/admin/notices/{id}` | CURATOR | 공지 수정 | MVP |
| 52 | DELETE | `/admin/notices/{id}` | CURATOR | 공지 취소 | MVP |
| 53 | GET | `/admin/stats/daily` | CURATOR | 날짜별 입장 현황(B-1) | v1.1 |
| 54 | GET | `/admin/stats/members` | CURATOR | 회원 검색(B-1 입력) | v1.1 |
| 55 | GET | `/admin/stats/members/{id}` | CURATOR | 회원별 감상 상세(B-1-1) | v1.1 |
| 56 | GET | `/system/health` | PUBLIC | 헬스 체크 | MVP |

v1.1 표시 엔드포인트도 **경로와 스키마를 MVP 시점에 확정**한다. 프런트엔드가 나중에 붙일 때 계약 협의를 다시 하지 않기 위함이다.

---

## 5. 오류 코드 카탈로그

`code`는 **전역 유일**하며 값이 한 번 배포되면 의미를 바꾸지 않는다. 새 상황은 새 코드를 추가한다.

### 5.1 공통

| code | HTTP | message(기본) | retryable | details |
|---|---|---|:---:|---|
| `VALIDATION_FAILED` | 422 | 입력한 내용을 다시 확인해 주세요. | false | — (`field_errors` 사용) |
| `QUERY_INVALID_SORT` | 400 | 잘못된 정렬 조건입니다. | false | `allowed[]` |
| `QUERY_UNKNOWN_PARAM` | 400 | 지원하지 않는 검색 조건입니다. | false | `unknown[]` |
| `PAGINATION_INVALID_CURSOR` | 400 | 목록을 다시 불러와 주세요. | false | — |
| `NOT_FOUND` | 404 | 요청하신 내용을 찾을 수 없습니다. | false | `resource` |
| `CONFLICT_VERSION` | 409 | 다른 곳에서 먼저 수정되었습니다. 새로고침 후 다시 시도해 주세요. | false | `current_version` |
| `RATE_LIMITED` | 429 | 잠시 후 다시 시도해 주세요. | true | `retry_after_seconds` |
| `CSRF_HEADER_MISSING` | 403 | 요청을 처리할 수 없습니다. 새로고침 후 다시 시도해 주세요. | false | — |
| `MAINTENANCE_MODE` | 503 | 잠시 점검 중입니다. | true | `until` |
| `SYSTEM_INTERNAL` | 500 | 문제가 생겼습니다. 잠시 후 다시 시도해 주세요. | true | — |
| `SYSTEM_DEPENDENCY_UNAVAILABLE` | 503 | 일시적으로 연결이 원활하지 않습니다. | true | `dependency` |

### 5.2 인증·계정

| code | HTTP | message(기본) | retryable | details |
|---|---|---|:---:|---|
| `AUTH_REQUIRED` | 401 | 로그인이 필요합니다. | false | — |
| `AUTH_INVALID_CREDENTIALS` | 401 | 전화번호 또는 비밀번호가 맞지 않습니다. | false | — |
| `AUTH_TOO_MANY_ATTEMPTS` | 429 | 로그인 시도가 많았습니다. 10분 뒤에 다시 시도해 주세요. | true | `retry_after_seconds` |
| `AUTH_SESSION_EXPIRED` | 401 | 로그인이 만료되었습니다. 다시 입장해 주세요. | false | — |
| `AUTH_SESSION_REVOKED` | 401 | 로그인이 만료되었습니다. 다시 입장해 주세요. | false | — |
| `AUTH_FORBIDDEN` | 403 | 접근 권한이 없습니다. | false | — |
| `SIGNUP_CLOSED` | 403 | 지금은 새로운 회원을 받고 있지 않습니다. | false | — |
| `SIGNUP_PHONE_TAKEN` | 409 | 이미 가입된 번호입니다. | false | — |
| `PASSWORD_POLICY_VIOLATION` | 422 | 비밀번호는 8자 이상이어야 합니다. | false | `min_length` |
| `PASSWORD_CURRENT_MISMATCH` | 401 | 현재 비밀번호가 맞지 않습니다. | false | — |
| `RESET_CODE_INVALID` | 422 | 인증번호가 맞지 않습니다. | false | `attempts_left` |
| `RESET_CODE_EXPIRED` | 422 | 인증번호가 만료되었습니다. 다시 받아 주세요. | false | — |
| `SOCIAL_PROVIDER_UNKNOWN` | 404 | 지원하지 않는 로그인 방식입니다. | false | `provider` |
| `SOCIAL_DISABLED` | 503 | 지금은 이 방식으로 로그인할 수 없습니다. | true | `provider` |
| `SOCIAL_STATE_INVALID` | 400 | 로그인 요청이 만료되었습니다. 처음부터 다시 시도해 주세요. | false | — |
| `SOCIAL_EXCHANGE_FAILED` | 502 | 로그인 제공자와 연결하지 못했습니다. 잠시 후 다시 시도해 주세요. | true | `provider` |
| `SOCIAL_LINK_EXPIRED` | 400 | 연결 시간이 지났습니다. 처음부터 다시 시도해 주세요. | false | — |
| `SOCIAL_ALREADY_LINKED` | 409 | 이미 다른 계정에 연결된 소셜 계정입니다. | false | — |
| `SOCIAL_LAST_IDENTITY` | 409 | 마지막 로그인 수단은 해제할 수 없습니다. 비밀번호를 먼저 설정해 주세요. | false | — |

> **클라이언트 전용 코드** — `NETWORK_OFFLINE`, `CLIENT_TIMEOUT`, `CHUNK_LOAD_FAILED`는 서버가 반환하지 않으며 프런트엔드 HTTP 클라이언트가 생성한다. 코드 이름 공간을 공유하되 서버 카탈로그에는 등록하지 않는다(프런트 문서 §7.1).

**계정 존재 여부를 노출하지 않는다**(PRD §6.2). 미가입 번호 로그인, 차단 회원 로그인, 비밀번호 불일치는 **모두 `AUTH_INVALID_CREDENTIALS`**로 동일하게 응답한다. 비밀번호 재설정 요청도 미가입 번호에 성공 응답을 준다. §6.14 소셜 연결도 같은 규칙을 따른다.

`SOCIAL_ALREADY_LINKED`는 **어느 회원에게 연결되어 있는지 알려주지 않는다.** 소셜 계정을 가진 사람이 우리 서비스의 회원 명단을 조회하는 수단이 되면 안 된다.

### 5.3 전시·그림

| code | HTTP | message(기본) | retryable | details |
|---|---|---|:---:|---|
| `EXHIBITION_NOT_FOUND` | 404 | 전시를 찾을 수 없습니다. | false | `date` |
| `EXHIBITION_NOT_OPENED` | 404 | 첫 전시를 준비하고 있습니다. | false | — |
| `EXHIBITION_BACKFILL_FORBIDDEN` | 409 | 지난 날짜에는 새 전시를 걸 수 없습니다. | false | `date`, `today` |
| `EXHIBITION_ALREADY_HIDDEN` | 409 | 이미 숨겨진 전시입니다. | false | — |
| `EXHIBITION_NOT_PUBLISHED` | 409 | 아직 발행되지 않은 전시입니다. | false | — |
| `ARTWORK_NOT_FOUND` | 404 | 그림을 찾을 수 없습니다. | false | — |
| `ARTWORK_SLOT_OCCUPIED` | 409 | 이미 그림이 있는 자리입니다. | false | `position` |
| `ARTWORK_IMAGE_NOT_READY` | 409 | 이미지 준비가 끝나지 않았습니다. | true | `image_status` |
| `DRAFT_TARGET_OCCUPIED` | 409 | 오늘 날짜에 이미 작업 중인 전시가 있습니다. | false | `target_date` |
| `DRAFT_NOT_FOUND` | 404 | 이어 쓸 작업물이 없습니다. | false | — |
| `UPLOAD_FILE_TOO_LARGE` | 413 | 이미지는 20MB까지 올릴 수 있습니다. | false | `max_bytes` |
| `UPLOAD_MIME_NOT_ALLOWED` | 422 | JPG, PNG, WebP 파일만 올릴 수 있습니다. | false | `allowed[]` |
| `UPLOAD_EXPIRED` | 409 | 업로드 시간이 지났습니다. 다시 시도해 주세요. | true | — |

### 5.4 회원 관리·설정

| code | HTTP | message(기본) | retryable | details |
|---|---|---|:---:|---|
| `MEMBER_NOT_FOUND` | 404 | 회원을 찾을 수 없습니다. | false | — |
| `MEMBER_CURATOR_IMMUTABLE` | 403 | 관리자 계정은 변경할 수 없습니다. | false | — |
| `NOTICE_PERIOD_OVERLAP` | 409 | 이미 같은 기간에 공지가 있습니다. | false | `conflict_notice_id` |
| `NOTICE_PERIOD_INVALID` | 422 | 종료일은 시작일보다 빠를 수 없습니다. | false | — |
| `SETTING_IMMUTABLE` | 403 | 변경할 수 없는 설정입니다. | false | `key` |
| `SETTING_UNKNOWN_KEY` | 400 | 알 수 없는 설정입니다. | false | `key` |
| `PUSH_SUBSCRIPTION_INVALID` | 422 | 알림 설정에 실패했습니다. 다시 시도해 주세요. | false | — |

---

## 6. 공개 · 인증 API

### 6.1 `GET /public/landing` — A 첫 화면

**권한** `PUBLIC` · **캐시** `private, max-age=60`

A 화면이 필요로 하는 모든 것을 한 번에 준다. 비로그인 상태에서도 전시 제목이 보여야 하고(PRD §5.1 2단계), 휴관 공지와 관리자 링크 노출 여부도 여기서 결정된다.

**요청** 파라미터 없음.

**응답 `data`**

| 필드 | 타입 | Null | 설명 |
|---|---|:---:|---|
| `today` | string(date) | N | 서버 기준 KST 오늘 |
| `today_label` | string | N | `2026. 08. 27. 목` — **서버가 완성한 표시 문자열**. 요일 로케일 처리를 클라이언트에 분산시키지 않는다 |
| `exhibition_title` | string | Y | 현재 걸린 전시 제목. 개관 전이면 `null` |
| `has_exhibition` | boolean | N | 개관 여부 |
| `notice` | NoticeItem | Y | 오늘 유효한 휴관 공지. 없으면 `null` |
| `signup_open` | boolean | N | 가입 버튼 활성 여부 |
| `is_authenticated` | boolean | N | 유효 세션 존재 |
| `is_curator` | boolean | N | true일 때만 `Curator K` 링크를 렌더한다 |
| `member_name` | string | Y | 로그인 상태일 때 이름 |

**오류** — 없음. **이 엔드포인트는 실패하지 않는다.** DB 장애 시에도 `today`·`today_label`·`signup_open`(기본값)만 채우고 나머지를 `null`로 반환한다(PRD §6.1 "화면 자체는 항상 뜬다").

### 6.2 `GET /public/notice` — 현재 휴관 공지

**권한** `PUBLIC`

`/public/landing`에 포함되어 있으나, 공지만 갱신 확인하는 경량 폴링 경로로 별도 제공한다.

**응답 `data`** — `{ "notice": NoticeItem | null }`

### 6.3 `POST /auth/signup` — 회원가입 (D 화면)

**권한** `PUBLIC` · **성공** `201`

**요청 바디**

| 필드 | 타입 | 필수 | 제약 | 설명 |
|---|---|:---:|---|---|
| `phone` | string | ● | `^01[0-9]{8,9}$` (하이픈 제거 후) | 로그인 ID |
| `password` | string | ● | 8–64자 | |
| `name` | string | ● | 1–20자 | |
| `agreed_terms` | boolean | ● | `true`만 허용 | 이용·개인정보 처리 동의 1건 |

**응답 `data`** — `{ "user": SessionUser, "is_first_login": true }` + `Set-Cookie: gk_session=...`

가입 성공 시 **자동 로그인**되어 C 갤러리로 직행할 수 있다(PRD §6.4). 알림 권한 요청은 프런트가 가입 완료 직후 수행하며, 이 API는 관여하지 않는다.

**오류** — `SIGNUP_CLOSED`(403), `SIGNUP_PHONE_TAKEN`(409), `PASSWORD_POLICY_VIOLATION`(422), `VALIDATION_FAILED`(422), `RATE_LIMITED`(429)

**부수효과** — 큐레이터에게 가입 알림(`notification_log.kind='curator_signup'`)을 등록한다(PRD §6.4).

### 6.4 `POST /auth/login` — 로그인 (A-1 화면)

**권한** `PUBLIC`

**요청 바디**

| 필드 | 타입 | 필수 | 제약 |
|---|---|:---:|---|
| `phone` | string | ● | `^01[0-9]{8,9}$` |
| `password` | string | ● | 1–64자 |

**응답 `data`** — `{ "user": SessionUser }` + 세션 쿠키

**오류** — `AUTH_INVALID_CREDENTIALS`(401), `AUTH_TOO_MANY_ATTEMPTS`(429), `VALIDATION_FAILED`(422)

미가입·비밀번호 불일치·차단 회원을 **구분하지 않는다**(§5.2). 실패 시 `auth_throttle`이 증가하고 성공 시 초기화된다.

### 6.5 `POST /auth/logout`

**권한** `MEMBER` · **응답 `data`** `{}` · 세션 쿠키를 만료시키는 `Set-Cookie`를 반환한다.

### 6.6 `GET /auth/session` — 세션 확인 및 쿠키 갱신

**권한** `PUBLIC` (비로그인이어도 200)

앱 부팅 시 최초 1회 호출한다. 유효 세션이 있으면 사용자 정보를 내리고 세션 쿠키를 갱신한다.

**응답 `data`**

| 필드 | 타입 | Null | 설명 |
|---|---|:---:|---|
| `is_authenticated` | boolean | N | |
| `user` | SessionUser | Y | 미인증이면 `null` |

### 6.7 `POST /auth/password` — 비밀번호 변경

**권한** `MEMBER`

**요청 바디** — `current_password`(string, 필수), `new_password`(string, 필수, 8–64자)

**응답 `data`** — `{ "user": SessionUser }`. `token_version`이 증가하므로 **현재 세션은 즉시 재발급**되고 다른 단말 세션은 무효화된다.

**오류** — `PASSWORD_CURRENT_MISMATCH`(401), `PASSWORD_POLICY_VIOLATION`(422)

`must_change_password=true`인 사용자는 `current_password`에 초기 비밀번호를 넣어 이 API로 해소한다.

### 6.8 `POST /auth/password/reset/request` *(v1.1)*

**권한** `PUBLIC` · **요청 바디** `phone`(string, 필수)

**응답 `data`** — `{ "expires_in_seconds": 180, "resend_after_seconds": 60 }`

미가입 번호에도 **동일한 성공 응답**을 반환하며 실제 SMS는 발송하지 않는다(PRD §6.3).

**오류** — `RATE_LIMITED`(429)

### 6.9 `POST /auth/password/reset/confirm` *(v1.1)*

**요청 바디** — `phone`(필수), `code`(필수, 6자리 숫자), `new_password`(필수, 8–64자)

**응답 `data`** — `{}` (자동 로그인하지 않는다. A-1으로 돌아가 새 비밀번호로 입장한다)

**오류** — `RESET_CODE_INVALID`(422, `details.attempts_left`), `RESET_CODE_EXPIRED`(422), `PASSWORD_POLICY_VIOLATION`(422)

### 6.11 `GET /auth/social/providers` — 켜진 제공자 목록

**응답 `data`** — `{ providers: [{ provider, label, start_url }] }`

`client_id`가 설정된 제공자만 담긴다. **화면이 환경변수를 알 필요가 없다** — 목록이 비어 있으면 A-1에 소셜 영역 자체를 그리지 않는다.

### 6.12 `GET /auth/social/{provider}/start` — 인가 요청 시작

**응답** — `302` + `Location: {제공자 인가 URL}`. **봉투를 쓰지 않는다**(§2.2의 두 번째 예외).

**쿼리** — `next`(선택). 로그인 후 돌아갈 앱 내부 경로. `/`로 시작하고 `//`·`\`로 시작하지 않는 값만 허용하며, 그 외는 `/gallery`로 떨어뜨린다(열린 리다이렉트 방어).

서버가 `state`·`code_verifier`(PKCE S256)·`nonce`를 만들어 **서명 쿠키 `gk_oauth`**(HttpOnly, `SameSite=Lax`, TTL 10분)에 담고, 인가 URL에는 `state`와 `code_challenge`만 싣는다.

### 6.13 `GET /auth/social/{provider}/callback` — 인가 코드 수신

**응답** — `302`. 성공이면 `Location: {next}` + 세션 쿠키, 미연결이면 `Location: /auth/link` + 연결 티켓 쿠키.

| 단계 | 실패 시 |
|---|---|
| `state` 대조(URL ↔ 쿠키) | `302 /login?social_error=SOCIAL_STATE_INVALID` |
| 코드 → 토큰 교환(`code_verifier` 동봉) | `302 /login?social_error=SOCIAL_EXCHANGE_FAILED` |
| `id_token` 서명·`iss`·`aud`·`exp`·`nonce` 검증 | 동상 |
| 제공자 프로필 조회 | 동상 |
| 사용자가 동의 화면에서 취소 | `302 /login` (오류 없이 조용히) |

**모든 실패가 302로 끝나는 이유** — 이 경로는 브라우저 주소창이 향하는 곳이다. JSON 오류 봉투를 내리면 사용자는 흰 화면의 영어 덩어리를 본다. 화면이 `social_error` 코드를 §5.2의 한국어 문구로 번역해 로그인 화면 상단 배너에 띄운다.

### 6.14 `POST /auth/social/link` — 기존 계정에 연결

**전제** — 연결 티켓 쿠키(`gk_oauth_link`). 없거나 만료면 `SOCIAL_LINK_EXPIRED`.

**요청 바디** — `phone`(필수), `password`(필수)

**응답 `data`** — `{ user }` + 세션 쿠키. 이후 그 소셜로 바로 로그인된다.

**비밀번호를 요구하는 이유** — 전화번호만으로 연결하면 남의 번호를 적어 계정을 가져갈 수 있다. 연결은 **소유 증명**을 거쳐야 한다.

**오류** — `AUTH_INVALID_CREDENTIALS`(401 — 미가입·비밀번호 불일치·차단을 구분하지 않는다), `AUTH_TOO_MANY_ATTEMPTS`(429), `SOCIAL_ALREADY_LINKED`(409), `SOCIAL_LINK_EXPIRED`(400)

### 6.15 `POST /auth/social/signup` — 소셜 신규 가입

**전제** — 연결 티켓 쿠키.

**요청 바디** — `phone`(필수), `name`(필수, 1–20자), `agreed_terms`(필수, `true`)

**응답 `data`** — `{ user, is_first_login: true }` + 세션 쿠키

생성되는 계정은 `password_hash = NULL`, `created_via = 'social'`이다. **`signup_open`이 꺼져 있으면 만들지 않는다** — 가입 잠금은 외부 유입을 막는 장치이고, 소셜이 그 잠금의 뒷문이 되면 폐쇄형 서비스라는 전제가 깨진다.

**오류** — `SIGNUP_CLOSED`(403), `SIGNUP_PHONE_TAKEN`(409 — 이 번호는 §6.14로 연결해야 한다), `SOCIAL_ALREADY_LINKED`(409), `SOCIAL_LINK_EXPIRED`(400)

### 6.16 미디어 접근 규약

이미지 버킷은 비공개이며 **접근 수단은 presigned URL 하나뿐이다.** 전용 엔드포인트는 두지 않는다.

| 방향 | 방식 |
|---|---|
| 다운로드 | 이미지를 포함하는 응답이 **presigned GET URL**을 만들어 내린다. 유효기간은 전역 설정 값(`media_url_ttl_seconds`)을 따른다 |
| 업로드 | §9.8의 **presigned POST** 자격을 발급받아 클라이언트가 S3에 직접 올린다 |

서명 쿠키·키페어·전용 세션 갱신 API를 쓰지 않는다. 클라이언트가 관리해야 할 미디어 자격 상태가 없어지고, 만료된 URL은 화면을 다시 불러오면 그대로 해소된다.

---

## 7. 관람자 API

### 7.1 `GET /exhibitions/current` — 현재 전시 (C 화면)

**권한** `MEMBER` · **캐시** `private, max-age=0, must-revalidate` + `ETag`

PRD §4.3 규칙 1을 그대로 구현한다. 오늘 발행분이 없으면 **직전 발행 전시를 반환**하며, 이는 오류가 아니다.

**요청** 파라미터 없음.

**응답 `data`** — `ExhibitionDetail`

**오류** — `EXHIBITION_NOT_OPENED`(404, 개관 전), `AUTH_REQUIRED`(401)

**주의** — 이 API는 **입장을 기록하지 않는다**(AP-4). 프런트는 렌더 후 `POST /exhibitions/{date}/view`를 별도 호출한다.

### 7.2 `GET /exhibitions/{date}` — 특정 전시

**권한** `MEMBER` · **캐시** `private, max-age=300` + `ETag`

**경로 변수** — `date`: 전시 **발행일**(`YYYY-MM-DD`)

**응답 `data`** — `ExhibitionDetail` (`is_archive_view=true`)

**오류** — `EXHIBITION_NOT_FOUND`(404 — 미발행·숨김·미래 날짜 모두 동일하게 처리한다)

### 7.3 `GET /exhibitions` — 아카이브 목록 (C-3)

**권한** `MEMBER` · **페이지네이션** `cursor`

**쿼리 파라미터**

| 이름 | 타입 | 기본 | 제약 | 설명 |
|---|---|---|---|---|
| `limit` | integer | 30 | 1–30 | 최근 30개 전시(PRD §6.8) |
| `cursor` | string | — | | 다음 페이지 |

**응답 `data`** — `{ "exhibitions": ExhibitionSummary[] }` + `meta.pagination`

발행 전시만, 숨긴 전시 제외, 발행일 내림차순. 연장된 날은 별도 행으로 나타나지 않는다(전시 단위 목록이므로 자연히 그렇게 된다). **전체 목록 상한은 `app_setting.archive_size`(기본 30)**이며 그 이상은 `has_more=false`로 종료한다.

### 7.4 `POST /exhibitions/{date}/view` — 입장 기록

**권한** `MEMBER`

**경로 변수** — `date`: 화면에 실제로 렌더된 전시의 **발행일**

**요청 바디** — 없음

**응답 `data`**

| 필드 | 타입 | 설명 |
|---|---|---|
| `viewed_on` | string(date) | 서버가 판정한 관람일 |
| `is_first_entry_today` | boolean | 오늘 첫 입장 여부(신규 행 생성 여부) |

관람일은 **서버가 결정**한다(PRD §6.1). 하루 여러 번 호출해도 `entry_count`만 증가하며 지표에는 영향이 없다. 아카이브 진입도 동일하게 호출한다.

**오류** — `EXHIBITION_NOT_FOUND`(404)

### 7.5 `GET /artworks/{id}` — 그림 상세 (C-2)

**권한** `MEMBER`

새로고침·딥링크 진입에서도 단독으로 화면을 구성할 수 있어야 하므로 전시 문맥을 함께 담는다.

**응답 `data`**

| 필드 | 타입 | 설명 |
|---|---|---|
| `artwork` | ArtworkDetail | |
| `exhibition` | object | `{exhibition_date, title, is_carried_over, carried_over_label}` |
| `position_label` | string | `3 / 12` — 서버가 완성한 문자열 |

**오류** — `ARTWORK_NOT_FOUND`(404 — 미발행·숨김 전시의 그림도 동일)

### 7.6 `POST /artworks/{id}/view` — 그림 열람 기록

**권한** `MEMBER` · **요청 바디** 없음

**응답 `data`** — `{ "viewed_artwork_count": integer }` (해당 전시에서 지금까지 열어본 그림 수)

C-2 진입 시 호출한다. 스와이프로 빠르게 넘길 때 과도한 호출을 막기 위해 **프런트에서 화면 체류 1.5초 이상일 때만 전송**한다(프런트 문서 §9.3). 서버는 (회원, 그림) UPSERT이므로 중복에 안전하다.

---

## 8. 회원 API

### 8.1 `GET /me`

**권한** `MEMBER` · **응답 `data`** — `{ "user": SessionUser }`

### 8.2 `PATCH /me/settings` — 설정 변경 (C-4)

**권한** `MEMBER` · 부분 갱신. **보낸 필드만** 반영한다.

**요청 바디**

| 필드 | 타입 | 필수 | 제약 | 설명 |
|---|---|:---:|---|---|
| `notify_enabled` | boolean | ○ | | 아침 알림 on/off |
| `notify_at` | string | ○ | `HH:MM`, 05:00–11:00 | 알림 시각. 범위 밖은 `VALIDATION_FAILED` |
| `font_scale` | string | ○ | `normal`\|`large` | 큰 글씨 모드(v1.1 UI) |

빈 바디(`{}`)는 `422 VALIDATION_FAILED`로 거부한다 — 의도 없는 PATCH는 버그 신호다.

**응답 `data`** — `{ "user": SessionUser }`

### 8.3 `DELETE /me` — 탈퇴

**권한** `MEMBER`

**요청 바디** — `{ "confirm": true }` (필수). 실수 방지를 위해 명시적 확인 필드를 요구한다.

**응답 `data`** — `{}` + 세션 쿠키 만료

DB 문서 §10.1의 트랜잭션을 수행한다. **큐레이터 계정은 탈퇴할 수 없다** — `MEMBER_CURATOR_IMMUTABLE`(403).

### 8.4 `POST /me/push-subscriptions` — 푸시 구독 등록

**권한** `MEMBER` · **성공** `201`(신규) / `200`(갱신)

**요청 바디**

| 필드 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| `endpoint` | string | ● | 브라우저 PushSubscription의 endpoint |
| `keys.p256dh` | string | ● | |
| `keys.auth` | string | ● | |
| `platform` | string | ○ | `ios`\|`android`\|`desktop`\|`unknown`. 미지정 시 서버가 UA로 추정 |

**응답 `data`** — `{ "subscription_id": string(uuid), "is_new": boolean }`

**부수효과** — `notify_enabled`가 false였다면 **true로 함께 전환**한다. 사용자가 브라우저 권한을 허용한 시점이 곧 알림을 켜겠다는 의사표시다.

**오류** — `PUSH_SUBSCRIPTION_INVALID`(422)

### 8.5 `GET /me/push-subscriptions` — 구독 목록

**권한** `MEMBER`

프런트가 앱 부팅 시 브라우저의 실제 구독과 서버 등록 상태를 대조하기 위해 사용한다(프런트 문서 §10.3).

**응답 `data`** — `{ "subscriptions": [{ "id", "endpoint_hash", "platform", "is_active", "created_at", "last_success_at" }] }`

`endpoint` 원문은 반환하지 않는다. 클라이언트는 자신의 구독 endpoint를 SHA-256 해시해 대조한다 — 엔드포인트 URL은 푸시 서비스에 대한 발송 권한 그 자체이므로 불필요하게 왕복시키지 않는다.

### 8.6 `DELETE /me/push-subscriptions/{subscription_id}`

**권한** `MEMBER` · **응답 `data`** `{}`

해당 단말 구독만 해제한다. `notify_enabled`는 건드리지 않는다 — 다른 단말에서는 계속 받을 수 있어야 한다. 전면 해제는 `PATCH /me/settings`의 `notify_enabled=false`다.

### 8.7 `GET /me/social-identities` — 연결된 소셜 계정

**권한** `MEMBER` · **응답 `data`** — `{ identities: SocialIdentity[], can_unlink: boolean }`

`can_unlink`가 `false`면 화면이 해제 버튼을 비활성화한다. 비밀번호가 없고 연결이 하나뿐인 상태이며, 해제하면 로그인 수단이 0이 된다.

### 8.8 `DELETE /me/social-identities/{identity_id}` — 연결 해제

**권한** `MEMBER` · **응답 `data`** `{}`

**오류** — `NOT_FOUND`(404 — 남의 연결 id를 넣어 존재를 떠보는 것도 부재로 답한다), `SOCIAL_LAST_IDENTITY`(409)

---

## 9. 관리자 API

전 엔드포인트 `CURATOR` 권한, `Cache-Control: no-store`, 변경 계열은 `audit_log` 기록을 남긴다.

### 9.1 `GET /admin/summary` — B 홈 요약

PRD 부록 B가 지정한 두 숫자만 반환한다.

**응답 `data`**

| 필드 | 타입 | 설명 |
|---|---|---|
| `today_entrant_count` | integer | 오늘(KST) 입장한 고유 회원 수 |
| `weekly_active_ratio` | number | 이번 주(월요일 기준) 3일 이상 입장 회원 비율. 0–1, 소수 셋째 자리 |
| `weekly_active_count` | integer | 위 비율의 분자 |
| `total_member_count` | integer | 차단·탈퇴 제외 전체 회원 수(분모) |
| `carried_over_days` | integer | 오늘 기준 연속 연장 일수. 0이면 오늘 발행됨 |
| `pending_draft_count` | integer | 오늘 이후 날짜 중 작업 중인 드래프트 수 |
| `lead_time_days` | integer | 오늘부터 연속으로 발행 준비된 날 수(§3.2 사전 준비 리드타임) |

### 9.2 `GET /admin/exhibitions/calendar` — 날짜별 발행 상태 (B)

**쿼리 파라미터**

| 이름 | 타입 | 기본 | 제약 | 설명 |
|---|---|---|---|---|
| `from` | date | 오늘 | | 범위 시작(포함) |
| `to` | date | 오늘+6일 | `to >= from`, 최대 90일 | 범위 끝(포함) |
| `direction` | string | `future` | `future`\|`past` | 무한 스크롤 방향 |
| `cursor` | string | — | | 과거 스크롤용 |
| `limit` | integer | 7 | 1–30 | |

기본 응답은 **오늘을 맨 위로 하는 7일치**다(PRD §6.9). 위로 스크롤하면 `direction=past`로 과거 30일씩 이어 받는다.

**응답 `data`** — `{ "days": AdminExhibitionDay[] }` + `meta.pagination`

`days`는 요청 범위의 **모든 날짜를 빠짐없이** 포함한다(전시가 없는 날 포함). 클라이언트가 날짜 시리즈를 만들지 않는다.

### 9.3 `GET /admin/exhibitions/{date}` — 편집 상태 조회 (B-2)

**응답 `data`** — 아래 구조를 `AdminExhibitionDetail`이라 부르며 §9.4·§9.11·§9.12가 이를 참조한다.

| 필드 | 타입 | Null | 설명 |
|---|---|:---:|---|
| `exhibition_date` | string(date) | N | |
| `title` | string | Y | |
| `theme` | string | Y | |
| `is_published` | boolean | N | |
| `published_at` | string(datetime) | Y | |
| `is_hidden` | boolean | N | |
| `edit_mode` | string | N | `create`\|`edit`\|`carry_draft`\|`locked` |
| `can_publish` | boolean | N | 현재 상태로 발행 조건 충족 여부 |
| `publish_blockers` | array\<string> | N | `missing_title`\|`missing_theme`\|`incomplete_artwork:{position}` 목록 |
| `slots` | array\<AdminArtworkSlot> | N | **항상 12개**. 비어 있어도 자리 표시자를 반환한다 |
| `version` | integer | N | 낙관적 잠금 토큰 |
| `draft_updated_at` | string(datetime) | Y | |
| `carry_draft_source` | object | Y | `carry_draft` 모드일 때 `{from_date, artwork_count}` |

**`AdminArtworkSlot`**

| 필드 | 타입 | Null | 설명 |
|---|---|:---:|---|
| `position` | integer | N | 1–12 |
| `artwork_id` | string(uuid) | Y | 비어 있으면 `null` |
| `title` / `artist` / `year_text` / `description` | string | Y | |
| `collection` / `source_url` | string | Y | |
| `image_status` | string | N | `empty`\|`uploading`\|`ready`\|`failed` |
| `image` | ImageSet | Y | `ready`일 때만 |
| `image_error_code` | string | Y | |
| `is_complete` | boolean | N | |
| `version` | integer | Y | |

`slots`가 항상 12개라는 계약이 B-2 화면(3×4 버튼 그리드)을 단순하게 만든다.

**오류** — `EXHIBITION_NOT_FOUND`는 발생하지 않는다. 행이 없으면 빈 12슬롯과 `edit_mode`를 계산해 반환한다.

### 9.4 `PUT /admin/exhibitions/{date}` — 제목·테마 저장 (B-2-1)

드래프트 자동 임시저장의 대상이다. 행이 없으면 생성한다(upsert).

**요청 바디**

| 필드 | 타입 | 필수 | 제약 |
|---|---|:---:|---|
| `title` | string \| null | ● | 0–20자 |
| `theme` | string \| null | ● | 0–500자 |
| `version` | integer | ○ | 있으면 낙관적 잠금 검사 |

`title`·`theme`을 **항상 함께 보낸다**(PUT 의미론). 자동저장 주기마다 전체 상태를 덮어쓰는 편이 부분 병합보다 예측 가능하다.

**응답 `data`** — `{ "exhibition_date", "version", "draft_updated_at", "is_published", "published_at", "can_publish", "publish_blockers", "published_now": boolean }`

`published_now=true`는 **이 요청으로 발행 조건이 처음 충족되었음**을 뜻한다. 프런트는 이때만 발행 완료 안내를 띄운다.

**오류** — `EXHIBITION_BACKFILL_FORBIDDEN`(409, 과거 미발행일), `CONFLICT_VERSION`(409), `VALIDATION_FAILED`(422)

### 9.5 `PUT /admin/exhibitions/{date}/artworks/{position}` — 그림 저장 (B-2-2)

**경로 변수** — `position`: 1–12

**요청 바디**

| 필드 | 타입 | 필수 | 제약 |
|---|---|:---:|---|
| `title` | string \| null | ● | 0–20자 |
| `artist` | string \| null | ● | 0–40자 |
| `year_text` | string \| null | ● | 0–20자 |
| `description` | string \| null | ● | 0–300자 |
| `collection` | string \| null | ● | 0–60자 |
| `source_url` | string \| null | ● | `https://`로 시작, 0–500자 |
| `version` | integer | ○ | |

**응답 `data`** — `{ "slot": AdminArtworkSlot, "exhibition": {version, can_publish, publish_blockers, is_published, published_now} }`

그림 저장이 전시의 발행 조건을 바꿀 수 있으므로 **전시 상태를 함께 반환**한다. 프런트가 저장 후 전시를 다시 조회하지 않게 한다.

### 9.6 `DELETE /admin/exhibitions/{date}/artworks/{position}` — 슬롯 비우기

**응답 `data`** — 9.5와 동일 구조(`slot.artwork_id=null`)

이미지 오브젝트는 즉시 삭제하지 않고 7일 뒤 정리 배치가 회수한다(DB 문서 §8.3). 발행된 전시에서 슬롯을 비워도 `is_published`는 유지된다(PRD §6.10).

### 9.7 `POST /admin/exhibitions/{date}/artworks/reorder` — 순서 변경

**요청 바디** — `{ "order": [{"artwork_id": uuid, "position": 1..12}, ...] }`

전체 슬롯의 목표 배치를 한 번에 보낸다. 부분 이동 지시가 아니라 **최종 상태 선언**이므로 재시도가 안전하다.

**검증** — `position`은 1–12 안에서 중복 없이 유일해야 하고, `artwork_id`는 모두 해당 전시 소속이어야 한다.

**응답 `data`** — `{ "slots": AdminArtworkSlot[] }` (12개)

### 9.8 `POST /admin/exhibitions/{date}/artworks/upload-urls` — presigned POST 자격 발급

20MB 파일은 API Gateway를 통과할 수 없으므로 클라이언트가 S3로 직접 올린다. **presigned POST** 방식을 쓴다 — 크기 상한·콘텐츠 타입·키 접두를 서버가 서명한 정책으로 못박을 수 있다.

**요청 바디**

| 필드 | 타입 | 필수 | 제약 | 설명 |
|---|---|:---:|---|---|
| `files` | array | ● | 1–12개 | |
| `files[].position` | integer | ● | 1–12, 중복 불가 | 채울 슬롯 |
| `files[].filename` | string | ● | 1–200자 | 확장자 추출용 |
| `files[].content_type` | string | ● | `image/jpeg`\|`image/png`\|`image/webp` | |
| `files[].size_bytes` | integer | ● | 1–20,971,520 | 사전 검증. S3 정책으로 재차 강제 |

**응답 `data`**

| 필드 | 타입 | 설명 |
|---|---|---|
| `uploads[].position` | integer | |
| `uploads[].artwork_id` | string(uuid) | 슬롯에 대응하는 그림 행. 없으면 이 시점에 생성된다 |
| `uploads[].upload_url` | string | S3 업로드 엔드포인트 |
| `uploads[].method` | string | `POST` |
| `uploads[].fields` | object | 서명 정책 필드 묶음. **순서대로 폼에 담고 파일을 마지막에 붙인다** |
| `uploads[].object_key` | string | |
| `uploads[].expires_at` | string(datetime) | 기본 15분 |

**부수효과** — 대상 슬롯의 `image_status`를 `uploading`으로 전환한다.

**오류** — `UPLOAD_FILE_TOO_LARGE`(413), `UPLOAD_MIME_NOT_ALLOWED`(422), `ARTWORK_SLOT_OCCUPIED`(409 — 이미 `ready`인 슬롯에 `overwrite=false`로 요청한 경우)

**요청 바디 추가 필드** — `overwrite`(boolean, 기본 `false`). `true`면 기존 이미지를 교체한다.

### 9.9 `POST /admin/artworks/{artwork_id}/image/complete` — 업로드 완료 통지

클라이언트가 업로드 성공 직후 호출한다. 서버가 **이 요청 안에서 동기로** 원본을 검증·변환하고 `ready`로 전환한 뒤 응답한다. 중복 호출은 무해하다(이미 `ready`면 현재 상태만 반환).

**요청 바디** — `{ "object_key": string }`

**응답 `data`** — `{ "artwork_id", "image_status", "images": ImageSet }`

**폴링하지 않는다.** 응답이 곧 처리 완료 통지다. 실패는 `image_status=failed`와 사유 코드로 돌아오며 재업로드로만 복구한다.

### 9.10 `POST /admin/exhibitions/{date}/hide` · `/unhide` — 전시 숨김

**요청 바디** — `hide`: `{ "reason": string | null }` (0–200자) / `unhide`: 없음

**응답 `data`** — `{ "exhibition_date", "is_hidden", "hidden_at", "current_exhibition_date": string }`

`current_exhibition_date`는 **숨김 처리 후 관람자에게 실제로 걸리게 되는 전시의 발행일**이다. 큐레이터가 조작 결과를 즉시 확인할 수 있어야 한다(PRD §6.9).

**오류** — `EXHIBITION_NOT_PUBLISHED`(409), `EXHIBITION_ALREADY_HIDDEN`(409)

### 9.11 `POST /admin/exhibitions/{date}/carry-draft` — 이어쓰기

과거 미발행일의 드래프트를 **오늘 날짜로 이동**한다(복사가 아니다, PRD 부록 B).

**경로 변수** — `date`: 원본 드래프트의 날짜(과거)

**요청 바디** — `{ "confirm": true }`

**응답 `data`** — `{ "from_date", "to_date", "moved_artwork_count", "exhibition": AdminExhibitionDetail }`

**동작** — 대상(오늘) 날짜에 작업물이 있으면 이동하지 않고 `DRAFT_TARGET_OCCUPIED`(409)를 반환한다. "작업물 있음"의 정의는 `title`·`theme` 중 하나라도 비어 있지 않거나 `artwork_count > 0`이다. 원본 날짜의 행은 이동 후 삭제된다.

**오류** — `DRAFT_NOT_FOUND`(404), `DRAFT_TARGET_OCCUPIED`(409), `EXHIBITION_NOT_PUBLISHED` 해당 없음(발행된 전시는 이어쓰기 대상이 아니며 `DRAFT_NOT_FOUND`로 처리)

### 9.12 `GET /admin/exhibitions/{date}/preview` — 미리보기

**응답 `data`** — `ExhibitionDetail`과 **동일한 스키마**. 단 미발행 상태여도 반환하며 `is_carried_over=false`, `viewing_date`는 해당 날짜로 채운다.

관람자 컴포넌트를 그대로 재사용하기 위해 스키마를 일치시킨다(프런트 문서 §7.4). 이미지가 아직 `ready`가 아닌 슬롯은 `image`를 `null`로 주고 프런트가 자리표시자를 그린다.

### 9.13 `GET /admin/members` — 회원 목록 (B-3)

**쿼리 파라미터**

| 이름 | 타입 | 기본 | 제약 | 설명 |
|---|---|---|---|---|
| `query` | string | — | 1–20자 | 이름 부분일치 또는 전화번호 완전일치 |
| `status` | string | `all` | `all`\|`active`\|`blocked` | |
| `notify` | string | `all` | `all`\|`on`\|`off` | 알림 미수신자 색출용 |
| `sort` | string | `-created_at` | `created_at`\|`-created_at`\|`name`\|`-name`\|`last_viewed_on`\|`-last_viewed_on` | |
| `page` | integer | 1 | | |
| `limit` | integer | 30 | 1–100 | |

**응답 `data`** — `{ "members": MemberItem[], "signup_open": boolean }` + `meta.pagination`(page 모드)

`signup_open`을 목록과 함께 반환한다 — B-3 화면 상단 스위치가 별도 요청 없이 렌더된다.

### 9.14 `POST /admin/members` — 대행 가입

**성공** `201`

**요청 바디** — `phone`(필수), `name`(필수, 1–20자), `initial_password`(필수, 8–64자)

**응답 `data`** — `{ "member": MemberItem }`

생성된 계정은 `created_via='curator'`, `must_change_password=true`다. **가입 잠금(`signup_open=false`) 상태에서도 생성 가능**하다 — 잠금은 외부 가입을 막는 장치이지 큐레이터를 막는 장치가 아니다.

**오류** — `SIGNUP_PHONE_TAKEN`(409), `PASSWORD_POLICY_VIOLATION`(422)

### 9.15 `POST /admin/members/{id}/block` · `/unblock`

**요청 바디** — `block`: `{ "reason": string | null }` / `unblock`: 없음

**응답 `data`** — `{ "member": MemberItem }`

차단은 **로그인 시점에만** 작동한다(PRD §6.4). 응답에 `details` 대신 `member.blocked_at`으로 결과를 확인한다. 이미 같은 상태면 그대로 `200`(멱등).

**오류** — `MEMBER_NOT_FOUND`(404), `MEMBER_CURATOR_IMMUTABLE`(403)

### 9.16 `POST /admin/members/{id}/reset-password`

**요청 바디** — `{ "new_password": string }` (8–64자)

**응답 `data`** — `{ "member": MemberItem }`

`must_change_password=true`, `token_version+1`로 해당 회원의 모든 세션을 무효화한다. 큐레이터가 전화로 새 비밀번호를 전달하는 운영 흐름을 전제한다(PRD §6.14).

### 9.17 `GET /admin/settings` · `PATCH /admin/settings`

**GET 응답 `data`** — `{ "settings": [{ "key", "value", "value_type", "description", "is_mutable", "updated_at" }] }`

**PATCH 요청 바디** — `{ "settings": { "<key>": <value>, ... } }` — 변경할 키만 담는다.

**PATCH 응답 `data`** — GET과 동일 구조(전체 반환)

가입 잠금은 `signup_open` 키로 조작한다. 별도 엔드포인트를 두지 않는 이유는 설정이 앞으로 늘어날 것이 확실하고(§4.9 시드 10종), 조작 화면이 하나이기 때문이다.

**오류** — `SETTING_UNKNOWN_KEY`(400), `SETTING_IMMUTABLE`(403), `VALIDATION_FAILED`(422 — 값 타입 불일치)

### 9.18 공지 API — `GET/POST /admin/notices`, `PATCH/DELETE /admin/notices/{id}`

| 메서드 | 요청 바디 | 응답 `data` |
|---|---|---|
| GET | 쿼리: `include_past`(bool, 기본 false), `page`, `limit` | `{ "notices": NoticeItem[] }` + pagination |
| POST | `starts_on`, `ends_on`, `body`(1–300자) | `{ "notice": NoticeItem }` (`201`) |
| PATCH | `starts_on`?, `ends_on`?, `body`? | `{ "notice": NoticeItem }` |
| DELETE | 없음 | `{}` — 실제로는 `is_active=false` 처리 |

**오류** — `NOTICE_PERIOD_INVALID`(422), `NOTICE_PERIOD_OVERLAP`(409, `details.conflict_notice_id`)

### 9.19 통계 API *(v1.1)*

**`GET /admin/stats/daily`** — 쿼리 `from`(기본 오늘-6일), `to`(기본 오늘). 최대 90일.

응답 `data.days[]`: `{ date, exhibition_date, exhibition_title, is_carried_over, entrant_count, artwork_view_count }` — 요청 범위의 모든 날짜를 포함한다.

**`GET /admin/stats/members`** — 쿼리 `query`(1–20자, 필수). 응답 `data.members[]`: `{ id, name, phone_masked, last_viewed_on }` (최대 20건). B-1의 이름/연락처 입력 후보 목록이다.

**`GET /admin/stats/members/{id}`** — 쿼리 `days`(기본 30, 최대 90).

응답 `data`: `{ member: {id, name, phone_masked}, days: [{ date, exhibition_date, exhibition_title, entered: boolean, viewed_artwork_count, total_artwork_count }] }`

`viewed_artwork_count / total_artwork_count`가 B-1-1의 `8 / 12` 표시 근거다. 미입장일도 행으로 포함한다(`entered=false`).

---

## 10. 시스템 API

### 10.1 `GET /system/health`

**권한** `PUBLIC` · **응답 `data`** — `{ "status": "ok"|"degraded", "checks": { "database": "ok"|"fail", "storage": "ok"|"fail" }, "version": string }`

`degraded`여도 HTTP `200`을 반환한다. 헬스 체크가 5xx를 내면 CloudFront 오리진 실패로 잡혀 A 첫 화면까지 죽는다(PRD §8.5).

---

## 11. 주요 흐름의 호출 순서

### 11.1 앱 부팅 → 갤러리 입장

1. `GET /auth/session` — 세션 확보
2. `GET /public/landing` — A 화면 렌더
3. (입장 버튼) → `GET /exhibitions/current` — C 화면 렌더
4. 렌더 완료 후 `POST /exhibitions/{date}/view` — 입장 기록 (실패해도 화면에 영향 없음, 재시도 1회)
5. (썸네일 탭) → `GET /artworks/{id}` → 1.5초 체류 후 `POST /artworks/{id}/view`

C 화면 진입까지 **네트워크 왕복 3회**이며, 2·3은 세션 확인 결과에 의존하므로 직렬이다. 프런트는 3을 세션 확인과 낙관적으로 병렬 실행한다(프런트 문서 §8.2).

### 11.2 그림 업로드

1. `POST /admin/exhibitions/{date}/artworks/upload-urls` — N개 슬롯 자격 발급, 상태 `uploading`
2. 클라이언트 → S3 직접 `POST` (동시 3개 제한)
3. `POST /admin/artworks/{id}/image/complete` — 각 파일 완료 즉시. 서버가 동기 변환 후 `ready`로 응답
4. `PUT /admin/exhibitions/{date}/artworks/{position}` — 메타데이터 입력·저장
5. 12슬롯 완성 + 제목·테마 충족 시 응답의 `published_now=true`

### 11.3 발행과 알림

1. 6.의 저장 요청 트랜잭션에서 `is_published=true`, `published_at` 기록
2. 같은 트랜잭션에서 대상 회원 전원의 `notification_log`를 `pending`으로 생성 (`dedupe_key = morning:{user_id}:{date}`)
3. 5분 주기 스케줄러가 `scheduled_for <= now()`인 `pending`을 집어 웹 푸시 발송
4. 이미 사용자의 `notify_at`이 지난 경우 `scheduled_for`를 즉시로 설정하되, `notify_cutoff_hour`(21시)를 넘겼으면 `skipped(cutoff_passed)`로 종료

---

## 12. PRD 대비 변경·보완 사항

| # | PRD §9.3 | 이 문서의 결정 | 사유 |
|---|---|---|---|
| **A-1** | `POST /admin/exhibitions/{date}` | `PUT /admin/exhibitions/{date}` | 자동 임시저장은 동일 리소스의 전체 상태 갱신이며 재시도가 안전해야 한다 |
| **A-2** | `POST /admin/artworks/upload-url` (단수) | `POST /admin/exhibitions/{date}/artworks/upload-urls` (복수, 전시 하위) | 다중 선택 업로드(PRD §6.10)가 1급 기능이므로 배치 발급이 기본이다. 전시 하위 경로가 권한·검증 문맥을 단순화한다 |
| **A-3** | (없음) | `GET /public/landing` 신설 | A 화면이 전시 제목·공지·가입 가능 여부·관리자 여부를 각각 요청하면 4회 왕복이 된다 |
| **A-4** | (없음) | 미디어 접근을 presigned URL 단일 수단으로 통일 | 서명 쿠키·키페어·전용 세션 API가 사라져 클라이언트가 관리할 미디어 자격 상태가 없어진다 |
| **A-5** | `GET /exhibitions/current`이 입장 기록도 겸함(암시) | `POST /exhibitions/{date}/view` 분리 | GET의 부수효과는 PWA 캐시·프리페치와 충돌한다 |
| **A-6** | `POST /admin/settings/signup` | `PATCH /admin/settings` 통합 | 조정 대상 설정이 10종이며 화면은 하나다 |
| **A-7** | `GET/POST /admin/notice` (단수) | `/admin/notices` 컬렉션 + `{id}` | 휴가 일정이 여러 건 예약될 수 있다 |
| **A-8** | (없음) | `POST /admin/exhibitions/{date}/unhide`, `/members/{id}/unblock` | 되돌릴 수 없는 조작만 있는 관리 화면은 운영 사고를 낳는다 |
| **A-9** | (없음) | `GET /admin/summary` 신설 | PRD 부록 B가 지정한 두 숫자의 전용 경로 |
| **A-10** | (없음) | `POST /admin/artworks/{id}/image/complete` | S3 이벤트만 의존하면 이벤트 지연 시 큐레이터가 무한정 기다린다 |
| **A-11** | 페이지네이션 미정의 | `meta.pagination` 단일 규약(§2.4) | PRD 유의사항 3 |
| **A-12** | 오류 처리 미정의 | 봉투 + 코드 카탈로그(§2.2, §5) | PRD 유의사항 3 |
| **A-13** | 교차 검토 | `GET /me/push-subscriptions` 추가 | 프런트의 구독 대조 로직에 조회 경로가 없었다 |
| **A-14** | 교차 검토 | 관리자 전시 편집 응답에 `AdminExhibitionDetail` 이름 부여 | 세 엔드포인트가 같은 구조를 이름 없이 참조하고 있었다 |
| **A-15** | 교차 검토 | 클라이언트 전용 오류 코드의 위치를 명시 | 프런트가 만든 코드가 서버 카탈로그에 있는 것처럼 보였다 |
