# 갤러리 K — 프런트엔드

매일 아침 12점의 그림이 걸리는 작은 미술관. 이 디렉터리는 관람자(C 계열)와
큐레이터(B 계열) 화면 전부를 담은 정적 SPA다.

구현 기준선은 `docs/`의 설계 문서다.

| 문서 | 이 코드에서의 위치 |
|---|---|
| [03 디자인 시스템](../docs/03-DESIGN-SYSTEM.md) | `src/styles/tokens.css`, `tailwind.config.js`, `src/shared/ui/` |
| [05 프런트엔드 아키텍처](../docs/05-FRONTEND-ARCHITECTURE.md) | 디렉터리 구조 · 레이어 규칙 · 라우팅 · 상태 · API 계층 |
| [06 UX 설계](../docs/06-USER-EXPERIENCE.md) | 화면별 구성과 `src/shared/config/messages.ts`(문구 단일 원천) |
| [02 API 명세](../docs/02-API-SPEC.md) | `src/shared/api/`, 각 `entities/*/api/` |

---

## 시작하기

```bash
npm install
npm run dev            # http://localhost:5173
```

**백엔드가 함께 떠 있어야 한다.** `backend/README.md`의 `make serve`로 8000 포트에 띄우면
dev 서버가 `/api`를 그쪽으로 프록시한다(`vite.config.ts`). 접두 `/api`는 배포에서
CloudFront가 붙이는 경로이고 `chalice local`에는 없으므로 프록시가 떼어 준다. 이렇게
**동일 오리진 조건을 로컬에서 재현**해야 세션 쿠키와 CSRF 헤더가 개발에서 먼저 검증된다.

로그인 계정은 백엔드 마이그레이션 시드의 큐레이터(`CURATOR_SEED_PHONE`)로 시작해서,
B-3 회원 관리의 대행 가입으로 관람자를 만든다. 큐레이터로 들어가면 A 첫 화면 우상단에
`Curator K` 링크가 생기고, 관리자 화면(B 계열)으로 갈 수 있다.

### 환경 변수

`.env`(공통) → `.env.development` / `.env.production`(모드별) → `.env.local`(개인, 커밋 안 함)
순으로 덮인다. 형식과 의미는 `.env.example`에 있다. **비밀값은 어느 파일에도 두지 않는다** —
`VITE_` 변수는 전부 번들에 그대로 실린다.

### 명령

| 명령 | 하는 일 |
|---|---|
| `npm run dev` | 개발 서버 |
| `npm run build` | 타입 검사 + 프로덕션 빌드 + **번들 예산·격리 검사** |
| `npm run typecheck` | 타입 검사만 |
| `npm run lint` | oxlint |
| `npm run lint:layers` | **레이어 의존 규칙 검사**(`.dependency-cruiser.cjs`) |
| `npm run lint:design` | **디자인 토큰·문구 규약 검사**(`scripts/check-design-tokens.mjs`) |
| `npm test` | 통합·단위 테스트 |
| `npm run verify` | 위 전부를 순서대로 |

---

## 구조

```
src/
├── app/         애플리케이션 셸 — 라우터 · 프로바이더 · 레이아웃 · 기록 전송
├── features/    화면 단위. 한 화면을 지우면 폴더 하나가 지워진다
├── entities/    도메인 모델 + 도메인 표현 컴포넌트 (기능 간 공유)
├── shared/      도메인 무지식 공용 — api · ui · hooks · lib · config
└── test/        테스트 지원 — 프로바이더 렌더러 · API 스텁 · 서버 원형 픽스처
```

### 레이어 규칙

의존은 **한 방향**이다: `app → features → entities → shared`.

| 금지 | 이유 |
|---|---|
| 기능 간 상호 참조 | 공통이 필요하면 `entities`/`shared`로 올린다 |
| `entities → features` | 도메인이 화면을 알면 재사용이 끝난다 |
| `shared → 상위` | 디자인 시스템이 제품에 종속된다 |
| 다른 기능의 내부 파일 깊게 참조 | `index.ts`(공개 표면)만 본다 |
| 순환 의존 | |

`npm run lint:layers`가 이 5개를 검사한다. 명시적 예외는 두 곳뿐이며 설정 파일에 근거와 함께 적혀 있다.

### 무엇을 어디에 둘까

| 질문 | 위치 |
|---|---|
| 특정 화면에서만 쓰이는가 | `features/{기능}/` |
| 두 개 이상의 기능이 같은 도메인 개념을 다루는가 | `entities/{도메인}/` |
| 도메인을 전혀 모르는가 | `shared/` |
| 라우팅·프로바이더·레이아웃인가 | `app/` |

---

## 이 코드가 지키는 약속

설계 문서의 원칙 중 **코드로 강제되는 것**들이다. 고칠 때 함께 확인한다.

| 약속 | 어디서 지켜지나 |
|---|---|
| 토큰 밖으로 나가지 않는다 | `tailwind.config.js`가 `colors`·`fontSize`·`spacing`을 **덮어쓴다**. `text-xs`(12px)는 존재하지 않는다. `npm run lint:design`이 임의 값·스케일 밖 유틸·하드코딩 색을 빌드 실패로 막는다 |
| 명도 대비는 측정된다 | `lint:design`이 디자인 문서 §3.3의 조합을 **실제로 계산해** AA 미달이면 실패시킨다 |
| 큰 글씨 모드는 컴포넌트를 바꾸지 않는다 | `html[data-font-scale]` 하나로 타이포와 그리드 열 수(3→2)가 함께 바뀐다 |
| 되돌아갈 길이 항상 보인다 | 모든 화면 하단의 `BackLink`. 대상은 페이지가 명시적으로 지정한다 |
| 제스처에는 항상 대안이 있다 | 스와이프 ↔ 하단 링크·화살표 키, 핀치 ↔ `크게 보기` 버튼·더블탭 |
| 문구는 한 곳에만 있다 | `shared/config/messages.ts`. JSX에 한국어 문자열을 직접 쓰지 않으며 **`lint:design`이 검사한다**(문구 원천과 테스트만 예외) |
| 되돌아갈 길은 두 곳에 그려지지 않는다 | 페이지가 `BackLink` 하나만 두면 상단 `←`는 레이아웃 슬롯으로 **포털**된다. 대상이 어긋날 수 없다 |
| 서버 계약은 한 곳에서만 안다 | `shared/api`가 봉투·오류·페이지네이션을 흡수하고, 바깥은 도메인 타입만 다룬다 |
| 관리자 코드는 관람자 경로로 흘러들지 않는다 | `RequireCurator` 아래 `lazy()` + 청크 분리. **`scripts/check-bundle.mjs`가 산출물을 직접 보고 검사하며, 섞이면 빌드가 실패한다** |
| 실패해도 화면은 뜬다 | A 첫 화면은 데이터 무의존 렌더, 기록 API 실패는 조용히 포기 |
| 미리보기는 관람자 화면 그 자체다 | `GalleryView`(순수) / `GalleryPage`(컨테이너) 분리. 미리보기는 기록 경로를 타지 않는다 |

---

## 소셜 로그인

카카오·구글을 **리다이렉트 방식**으로 지원한다(팝업을 쓰지 않는다). 흐름·방어·계정 정책은
[`docs/08-SOCIAL-AUTH.md`](../docs/08-SOCIAL-AUTH.md)가 소유한다.

프런트에는 **제공자 설정이 없다.** `GET /auth/social/providers`가 켜진 목록을 주고, 버튼은
서버가 준 `start_url`을 그대로 쓰는 `<a href>`다. 자격 증명은 백엔드 `.env`에만 있다.

```
A-1 [카카오로 시작하기]  →  /api/auth/social/kakao/start  →  카카오 동의
                                                              │
                    연결됨 → 세션 쿠키 + /gallery  ←──────────┤
                    미연결 → 연결 티켓 + /auth/link  ←────────┘
```

로컬에서 확인하려면 백엔드 `.env`에 `KAKAO_CLIENT_ID`(또는 `GOOGLE_CLIENT_ID`)와
`SOCIAL_REDIRECT_BASE_URL=http://localhost:5173`을 넣는다. 키가 없으면 목록이 비고
A-1에 소셜 영역이 그려지지 않는다 — 전화번호 로그인은 그대로 동작한다.

---

## 서버와 닿는 지점

화면은 서버에 **`shared/api/httpClient` 하나로만** 닿는다. 그 바깥에서 `fetch`를 부르는
곳은 둘뿐이며 각각 격리되어 있다 — 서비스워커(`src/sw.ts`)와 S3 직접 업로드
(`useUploadQueue`의 `XMLHttpRequest`, 20MB 파일은 API Gateway를 통과할 수 없다).

경로는 `shared/api/endpoints.ts`에만 있고, snake_case 응답은 각 `entities/*/api/mappers.ts`가
도메인 타입으로 바꾼다. `Raw*` 타입이 매퍼 밖으로 새어 나가지 않는 것이 이 분리의 목적이다 —
API가 바뀌어도 화면이 흔들리지 않는다.

그래서 테스트가 가로챌 지점도 하나다. `src/test/utils/apiStub.ts`가 `fetch`를 라우트 표로
바꾸고 **서버 원형 응답**(`src/test/fixtures/server.ts`)을 넣는다. 화면·훅·매퍼는 실제 코드
그대로 돌아가므로 매퍼도 함께 검증된다.

```ts
const api = stubApi({
  'GET /exhibitions/current': () => currentExhibition(),
  'POST /exhibitions/{date}/view': () => ({ recorded: true }),
})
expect(api.callsFor('POST /exhibitions/{date}/view')).toHaveLength(1)
```

스텁하지 않은 경로를 부르면 404 봉투가 돌아온다. **화면이 무엇을 부르는지가 곧 계약이므로**
조용히 통과시키지 않는다.

---

## 알아 둘 것

- **번들 예산** — `npm run build`가 §5.4의 표를 매번 검사해 출력한다. 현재 `vendor-react`만
  목표(gzip 60KB)를 넘으며(86.8KB), React 19 + React Router 7의 실제 크기라 코드로 줄일
  여지가 없다. 검사 스크립트는 이 초과를 **면제로 명시해 기록**한다 — 예산을 조용히 올리면
  표가 의미를 잃는다. 나머지(셸 40.3KB, `admin` 12.1KB 등)는 모두 예산 안이다.
- **폰트 용량** — 디자인 문서 §4.1은 서브셋 가변 폰트를 `≈120KB`로 잡았지만 실제는
  **603KB**다(한글 2,780자 + 굵기 축). 굵기별 정적 서브셋은 하나가 261KB이므로
  400·500·600 셋을 합치면 가변 1개보다 무겁다 — 가변 1개가 여전히 최선이다.
  `font-display: swap`이라 렌더를 막지 않고, 프리캐시 대신 워커의 1년 캐시가 받는다.
- **VAPID 키** — `VITE_VAPID_PUBLIC_KEY`가 비어 있으면 **구독을 만들지 않는다.** 서버에
  등록할 수 없는 구독을 만들어 봐야 알림이 오지 않으므로 없는 편이 정직하다. 백엔드
  `.env`의 `VAPID_PUBLIC_KEY`와 **같은 값**이어야 하고, 발송에는 백엔드의 개인키가 함께 필요하다.
- **v1.1 화면** — A-2 비밀번호 재설정과 B-1/B-1-1 관람 현황은 스키마가 확정되어 있어
  화면까지 함께 구현했다.
- **팔레트 미세 조정** — 디자인 문서 §3.1의 `neutral-500`·`warning-500`은 실측 대비가
  §3.3의 AA 기준(4.5:1)에 못 미쳤다(각 4.04·3.65). 색상을 유지한 채 최소한으로 낮춰
  4.6:1을 맞췄고, `lint:design`이 이 값을 매번 다시 계산한다.
- **순서 변경(드래그)** — 설계 문서는 `@dnd-kit`을 지정하지만 의존성 없이 구현되어 있다.
  모바일은 롱프레스(400ms) 후 드래그, PC는 즉시 드래그, 키보드는 `Space`로 집고
  방향키로 옮긴 뒤 `Space`로 놓는다(UX §3.12 그대로).
- **아직 없는 것** — Playwright E2E 9종(프런트 §14.1)과 Storybook 시각 회귀(DS §12.2).
  둘 다 브라우저 바이너리를 받는 별도 인프라가 필요하다. 현재 회귀 방어는
  통합·단위 테스트 30개와 위의 검사 스크립트 셋이다.

---

## PWA

설계 문서 §10을 그대로 구현한다. 앱 셸·전시 데이터·작품 이미지를 캐시하고,
홈 화면에 추가할 수 있으며, 웹푸시를 받는다.

| 조각 | 파일 |
|---|---|
| 서비스워커 (캐시 전략 · 푸시 핸들러) | [`src/sw.ts`](src/sw.ts) |
| 등록 · 새 버전 감지 | [`src/app/pwa/serviceWorkerRegistry.ts`](src/app/pwa/serviceWorkerRegistry.ts) |
| 안내 바 · 구독 재검증 | [`src/app/providers/PwaProvider.tsx`](src/app/providers/PwaProvider.tsx) |
| 매니페스트 · 아이콘 | `public/manifest.webmanifest`, `public/icons/` |

지키는 규칙 셋:

- **새 버전을 몰래 적용하지 않는다.** 대기 중인 워커가 생기면 하단에 `새 버전이 있습니다 ·
  새로고침`만 띄운다. 그림을 보는 도중에 화면이 리로드되면 그것으로 약속이 깨진다(§10.2).
- **관리자 청크는 프리캐시하지 않는다.** 프리캐시는 지연 로드보다 앞서 받으므로,
  여기서 빼지 않으면 §5.4의 청크 분리가 무의미해진다.
- **오프라인이어도 마지막 전시가 뜬다.** `/exhibitions/*`는 NetworkFirst(3초),
  작품 이미지는 CacheFirst(30일 · 200개). 관리자 화면은 오프라인을 지원하지 않는다.

### 생성물 되살리기

아이콘과 폰트는 저장소에 커밋되어 있다. 원본이 바뀌면 아래로 다시 만든다.

```bash
node scripts/generate-icons.mjs      # public/favicon.svg 와 같은 도형을 PNG로
bash scripts/build-font-subset.sh    # Pretendard 가변 폰트 서브셋 (python3 + fonttools 필요)
```

---

## 검사 스크립트

문서가 "린트로 차단한다"고 적어 둔 규칙에는 **실제로 차단하는 코드**가 있다.

| 스크립트 | 막는 것 | 근거 |
|---|---|---|
| `scripts/check-design-tokens.mjs` | 임의 값 · 원시 색 직접 참조 · 하드코딩 색 · `z-[숫자]` · 인라인 `style` · **스케일 밖 간격 유틸** · JSX 한국어 문구 · **명도 대비 미달** · 미사용 토큰 | DS §11.4·§12.3, 프런트 §16 |
| `scripts/check-bundle.mjs` | 관리자 모듈의 첫 화면 유입 · 청크 예산 초과 · 순환 청크 · 관리자 청크의 프리캐시 | 프런트 §5.4·§15.2 |
| `.dependency-cruiser.cjs` | 레이어 역방향·수평 참조 · 깊은 참조 · 순환 | 프런트 §4 |

`스케일 밖 간격 유틸`이 특히 중요하다. `theme.spacing`을 덮어썼기 때문에 `h-7`·`w-32` 같은
클래스는 **CSS를 만들지 않는다** — 오류 없이 조용히 크기가 사라진다.
