# 갤러리 K — 프런트엔드 아키텍처 설계서

| | |
|---|---|
| **문서 버전** | v1.0 |
| **작성일** | 2026-08-27 |
| **상위 문서** | `docs/PRD.md` v1.1, `02-API-SPEC.md`, `03-DESIGN-SYSTEM.md` |
| **런타임** | React 19 · Vite 8 · TypeScript 6 · TailwindCSS 3 |
| **배포 형태** | 정적 SPA(S3 + CloudFront) + PWA |
| **상태** | 확정 (구현 기준선) |

---

## 1. 설계 원칙

| # | 원칙 | 적용 |
|---|---|---|
| **FA-1** | **레이어 의존은 한 방향** | `app → features → entities → shared`. 역방향·수평 참조를 정적 검사로 금지한다 |
| **FA-2** | **기능은 폴더 하나로 완결** | 한 화면을 지우면 폴더 하나가 지워져야 한다. 화면 코드가 5개 디렉터리에 흩어지는 구조를 만들지 않는다 |
| **FA-3** | **서버 상태와 클라이언트 상태를 섞지 않는다** | 서버에서 온 것은 TanStack Query가, 화면 조작 상태는 컴포넌트 지역 상태 또는 소형 스토어가 소유한다 |
| **FA-4** | **API 계약은 한 곳에서만 안다** | `shared/api`가 봉투·오류·페이지네이션을 흡수하고, 그 바깥은 도메인 타입만 다룬다 |
| **FA-5** | **디자인 토큰 밖으로 나가지 않는다** | 임의 값·인라인 스타일을 린트로 차단한다(디자인 문서 DS-7) |
| **FA-6** | **첫 화면을 가장 빨리** | 라우트 단위 코드 스플리팅, 관리자 번들의 관람자 경로 유입 금지 |
| **FA-7** | **실패해도 화면은 뜬다** | 기록 API 실패, 이미지 실패, 네트워크 단절이 화면 전체를 무너뜨리지 않는다(PRD §6.1, §6.7) |

---

## 2. 기술 선택

| 영역 | 선택 | 근거 · 대안 기각 사유 |
|---|---|---|
| 라우팅 | **React Router 7** (`createBrowserRouter`) | 데이터 라우터의 `loader`로 라우트 진입 시 프리페치 가능. TanStack Router는 학습 비용 대비 이점이 적다 |
| 서버 상태 | **TanStack Query 5** | 캐시·재검증·오프라인 재시도를 직접 구현하지 않는다. `staleTime`으로 전시 데이터 특성(하루 단위 불변)을 그대로 표현할 수 있다 |
| 클라이언트 상태 | **Zustand 5** (스토어 3개 이하) | Context 남용은 리렌더 폭발을 부른다. Redux는 이 규모에 과하다 |
| 폼 | **React Hook Form 7 + Zod 4** | 비제어 기반이라 입력 지연이 없다. 서버 `field_errors`를 그대로 주입할 수 있다 |
| 스타일 | **TailwindCSS 3 + CVA + tailwind-merge** | 디자인 문서 §11 |
| 아이콘 | 자체 SVG 스프라이트 | 의존성 0, 트리셰이킹 고민 없음 |
| 날짜 | **`date-fns` (필요 함수만)** | 표시 문자열은 대부분 서버가 준다(API 문서 §6.1). 클라이언트 날짜 연산은 최소 |
| PWA | **`vite-plugin-pwa` (Workbox)** | 서비스워커 수기 작성 금지. 푸시 핸들러만 커스텀 주입 |
| 테스트 | **Vitest + Testing Library + Playwright + MSW** | |
| 린트 | **oxlint**(기존) + **dependency-cruiser**(레이어) + **prettier-plugin-tailwindcss** | 레이어 규칙은 oxlint로 표현되지 않으므로 별도 도구를 쓴다 |
| 이미지 | 네이티브 `<img>` + LQIP | 라이브러리 불필요 |
| 드래그 | **`@dnd-kit/core`** (관리자 번들 한정) | 순서 변경(B-2)에만 필요하며 관람자 번들에 들어가지 않는다 |

---

## 3. 디렉터리 구조

```
frontend/
├── index.html
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
├── .dependency-cruiser.cjs          # 레이어 의존 규칙
├── public/
│   ├── icons.svg                    # SVG 스프라이트
│   ├── manifest.webmanifest
│   ├── robots.txt                   # 전체 차단(PRD §8.4)
│   └── fonts/                       # Pretendard 서브셋 woff2
└── src/
    ├── main.tsx                     # 부트스트랩. 프로바이더 조립 + 라우터 마운트
    ├── sw.ts                        # 서비스워커 커스텀 진입(푸시·오프라인)
    ├── app/                         # 애플리케이션 셸
    │   ├── App.tsx
    │   ├── router/
    │   │   ├── index.tsx            # 라우트 트리 정의
    │   │   ├── paths.ts             # 경로 상수 단일 정의
    │   │   ├── guards.tsx           # RequireAuth / RequireCurator / RedirectIfAuthed
    │   │   └── loaders.ts           # 라우트 진입 프리페치
    │   ├── providers/
    │   │   ├── QueryProvider.tsx
    │   │   ├── SessionProvider.tsx  # 세션 부트스트랩
    │   │   ├── FontScaleProvider.tsx# data-font-scale 속성 동기화
    │   │   ├── ToastProvider.tsx
    │   │   └── AppErrorBoundary.tsx
    │   ├── layouts/
    │   │   ├── GalleryLayout.tsx    # 관람자 공통(컨테이너·하단 링크 슬롯)
    │   │   ├── StudioLayout.tsx     # 관리자 공통(반응형 2단)
    │   │   └── PlainLayout.tsx      # A·A-1·D 등 단독 화면
    │   └── analytics/
    │       └── viewTracker.ts       # 입장·열람 기록 전송 규칙(§9.3)
    ├── features/                    # 화면 단위. 폴더 = 기능
    │   ├── landing/                 # A. 첫 화면
    │   │   ├── LandingPage.tsx
    │   │   ├── components/
    │   │   ├── hooks/useLanding.ts
    │   │   └── index.ts             # 공개 표면(라우터가 참조하는 유일한 경로)
    │   ├── auth/                    # A-1 로그인, D 가입, A-2 재설정, 비밀번호 변경
    │   │   ├── LoginPage.tsx
    │   │   ├── SignupPage.tsx
    │   │   ├── PasswordResetPage.tsx
    │   │   ├── PasswordChangePage.tsx
    │   │   ├── components/PhoneField.tsx · PasswordField.tsx · TermsAgreement.tsx
    │   │   ├── hooks/useLogin.ts · useSignup.ts
    │   │   ├── model/schemas.ts     # Zod 폼 스키마
    │   │   ├── content/terms.ts      # 이용·개인정보 처리 동의 전문(정적 텍스트)
    │   │   └── index.ts
    │   ├── gallery/                 # C. 갤러리
    │   │   ├── GalleryPage.tsx
    │   │   ├── components/ExhibitionHeader.tsx · ArtworkGrid.tsx · GalleryFooterNav.tsx
    │   │   ├── hooks/useCurrentExhibition.ts · useEnterLog.ts
    │   │   └── index.ts
    │   ├── exhibition-theme/        # C-1. 전시 테마
    │   ├── artwork/                 # C-2. 그림 + 전체화면 뷰어
    │   │   ├── ArtworkPage.tsx
    │   │   ├── components/ArtworkFrame.tsx · ImmersiveViewer.tsx · SwipePager.tsx
    │   │   ├── hooks/useArtworkNavigation.ts · useArtworkViewLog.ts · usePinchZoom.ts
    │   │   └── index.ts
    │   ├── archive/                 # C-3. 지난 전시
    │   ├── settings/                # C-4. 설정
    │   │   ├── SettingsPage.tsx
    │   │   ├── components/NotifySection.tsx · FontScaleSection.tsx · WithdrawSection.tsx
    │   │   └── hooks/useUpdateSettings.ts · useWithdraw.ts
    │   ├── notification/            # 웹푸시 권한·구독 (화면 없음, 기능 모듈)
    │   │   ├── hooks/usePushSubscription.ts
    │   │   ├── components/PushPermissionPrompt.tsx · IosInstallGuide.tsx
    │   │   └── lib/pushClient.ts
    │   └── admin/                   # B 계열
    │       ├── dashboard/           # B. 관리자 홈
    │       │   ├── AdminDashboardPage.tsx
    │       │   ├── components/SummaryStats.tsx · DayList.tsx · DayRow.tsx
    │       │   └── hooks/useCalendar.ts
    │       ├── exhibition-editor/   # B-2, B-2-1, B-2-2
    │       │   ├── ExhibitionEditorPage.tsx
    │       │   ├── ThemeEditorPage.tsx
    │       │   ├── ArtworkEditorPage.tsx
    │       │   ├── PreviewPage.tsx
    │       │   ├── components/SlotGrid.tsx · SlotButton.tsx · UploadDropzone.tsx · SaveIndicator.tsx
    │       │   ├── hooks/useAutoSave.ts · useUploadQueue.ts · useReorder.ts
    │       │   └── model/editorSchemas.ts
    │       ├── members/             # B-3. 회원 관리
    │       ├── stats/               # B-1, B-1-1 (v1.1)
    │       └── settings/            # 전역 설정·휴관 공지
    ├── entities/                    # 도메인 모델 + 도메인 표현 컴포넌트(기능 간 공유)
    │   ├── exhibition/
    │   │   ├── model/types.ts       # Exhibition, ExhibitionSummary
    │   │   ├── api/queries.ts       # useExhibitionQuery 등 쿼리 훅
    │   │   ├── api/keys.ts          # 쿼리 키 팩토리
    │   │   └── ui/ExhibitionTitle.tsx · DateLine.tsx
    │   ├── artwork/
    │   │   ├── model/types.ts
    │   │   ├── api/queries.ts
    │   │   └── ui/ArtworkThumb.tsx · ArtworkImage.tsx · PositionIndicator.tsx
    │   ├── member/
    │   ├── notice/
    │   └── session/
    │       ├── model/types.ts       # SessionUser
    │       ├── api/queries.ts
    │       └── model/sessionStore.ts
    ├── shared/                      # 도메인 무지식 공용
    │   ├── api/
    │   │   ├── httpClient.ts        # fetch 래퍼. 봉투 해석·오류 변환·재시도
    │   │   ├── envelope.ts          # ApiEnvelope 타입 + 판별 유니온
    │   │   ├── ApiError.ts          # 오류 객체 + code 상수
    │   │   ├── errorMessages.ts     # code → 한국어 문구 폴백 맵
    │   │   ├── endpoints.ts         # 경로 상수
    │   │   ├── queryClient.ts       # QueryClient 기본 옵션
    │   │   ├── pagination.ts        # meta.pagination → 무한 스크롤 어댑터
    │   │   └── types.ts             # 서버 필드(snake_case) 원형 타입
    │   ├── ui/                      # 디자인 시스템 프리미티브(디자인 문서 §8.1)
    │   │   ├── Button.tsx · IconButton.tsx · TextLink.tsx
    │   │   ├── TextField.tsx · TextArea.tsx · Switch.tsx · CharCounter.tsx · FieldGroup.tsx
    │   │   ├── Dialog.tsx · BottomSheet.tsx · Toast.tsx
    │   │   ├── Skeleton.tsx · Spinner.tsx · Badge.tsx · StatusChip.tsx · Divider.tsx
    │   │   ├── EmptyState.tsx · ErrorState.tsx · Icon.tsx
    │   │   └── index.ts
    │   ├── hooks/
    │   │   ├── useSwipe.ts · useIntersection.ts · useLockBodyScroll.ts
    │   │   ├── useOnlineStatus.ts · useDebouncedValue.ts · useInterval.ts
    │   │   ├── useMediaQuery.ts · useVisibilityChange.ts
    │   │   └── usePrevious.ts
    │   ├── lib/
    │   │   ├── phone.ts             # 포맷·마스킹
    │   │   ├── date.ts              # 보조 포맷(서버 문자열 우선)
    │   │   ├── storage.ts           # localStorage 안전 래퍼(용도 키 상수 포함)
    │   │   ├── platform.ts          # iOS·standalone 감지
    │   │   ├── logger.ts
    │   │   └── assert.ts
    │   ├── config/
    │   │   ├── env.ts               # import.meta.env 검증 후 단일 객체로 노출
    │   │   ├── constants.ts         # ARTWORK_COUNT=12, ARCHIVE_LIMIT=30 …
    │   │   └── messages.ts          # 마이크로카피 전량(UX 문서 §5). 문구의 단일 원천
    │   ├── types/
    │   │   ├── enums.ts             # 서버 열거형 미러(DB 문서 §5)
    │   │   └── utility.ts
    │   └── styles/
    │       ├── tokens.css
    │       ├── base.css
    │       └── index.css
    └── test/
        ├── setup.ts
        ├── msw/handlers/            # 도메인별 목 핸들러
        └── utils/renderWithProviders.tsx
```

### 3.1 배치 판단 기준

| 질문 | 위치 |
|---|---|
| 특정 화면에서만 쓰이는가? | `features/{기능}/` |
| 두 개 이상의 기능이 같은 도메인 개념을 다루는가? | `entities/{도메인}/` |
| 도메인을 전혀 모르는가? | `shared/` |
| 라우팅·프로바이더·레이아웃인가? | `app/` |

**`features/*/index.ts`만이 외부 공개 표면이다.** 다른 기능의 내부 파일을 직접 import 하는 것을 dependency-cruiser가 차단한다.

---

## 4. 레이어 규칙

### 4.1 의존 방향

| 레이어 | import 허용 대상 |
|---|---|
| `app` | `features`, `entities`, `shared` |
| `features` | 같은 feature 내부, `entities`, `shared` |
| `entities` | 같은 entity 내부, `shared` |
| `shared` | `shared`만 |

**금지 사항**

1. `features` 간 상호 참조 (공통이 필요하면 `entities` 또는 `shared`로 올린다)
2. `entities` → `features`
3. `shared` → 상위 레이어
4. `features/*/` 내부 파일을 다른 곳에서 깊게 참조 (`index.ts` 경유만)
5. 순환 의존

`.dependency-cruiser.cjs`가 이 5개를 규칙으로 갖고 CI에서 실패시킨다.

### 4.2 컴포넌트 소속 판정

디자인 시스템 카탈로그(디자인 문서 §8)와 이 문서의 디렉터리는 다음과 같이 대응한다.

| 카탈로그 구분 | 위치 | 예 |
|---|---|---|
| 프리미티브(§8.1) | `shared/ui/` | `Button`, `TextField`, `Dialog`, `Banner`, `StatusChip` |
| 도메인 표현(§8.2 일부) | `entities/{도메인}/ui/` | `ArtworkThumb`, `ExhibitionTitle`, `DateLine`, `PositionIndicator` |
| 화면 전용 조합 | `features/{기능}/components/` | `ExhibitionHeader`(= `DateLine` + `ExhibitionTitle` + 연장 라벨), `GalleryFooterNav`, `NotifySection` |

**같은 이름을 두 계층에 두지 않는다.** 화면 전용 조합은 이름에 문맥을 담아(`ExhibitionHeader`) 도메인 표현 컴포넌트(`ExhibitionTitle`)와 구분한다.

### 4.3 shared/ui의 계약

`shared/ui` 컴포넌트는 **도메인 타입을 프롭으로 받지 않는다.** `ArtworkThumb`이 `shared/ui`가 아니라 `entities/artwork/ui`에 있는 이유가 이것이다. 이 경계가 흐려지면 디자인 시스템이 제품에 종속되어 재사용이 불가능해진다.

---

## 5. 라우팅

### 5.1 경로 표

| 경로 | 화면 | 레이아웃 | 가드 | 번들 |
|---|---|---|---|---|
| `/` | A. 첫 화면 | Plain | — | 초기 |
| `/login` | A-1. 로그인 | Plain | 로그인 시 `/gallery`로 | 초기 |
| `/signup` | D. 회원가입 | Plain | 로그인 시 `/gallery`로 | 지연 |
| `/password/reset` | A-2. 재설정 (v1.1) | Plain | — | 지연 |
| `/password/change` | 비밀번호 변경 | Plain | 회원 | 지연 |
| `/auth/link` | A-4. 계정 연결 | Plain | 연결 티켓(서버 쿠키) | 지연 |
| `/gallery` | C. 갤러리(현재 전시) | Gallery | 회원 | 초기 |
| `/gallery/theme` | C-1. 전시 테마 | Gallery | 회원 | 지연 |
| `/gallery/artworks/:artworkId` | C-2. 그림 | Gallery | 회원 | 초기 |
| `/archive` | C-3. 지난 전시 | Gallery | 회원 | 지연 |
| `/archive/:date` | 지난 전시 상세(C 재사용) | Gallery | 회원 | 지연 |
| `/archive/:date/theme` | 지난 전시 테마 | Gallery | 회원 | 지연 |
| `/archive/:date/artworks/:artworkId` | 지난 전시의 그림(C-2 재사용) | Gallery | 회원 | 지연 |
| `/settings` | C-4. 설정 | Gallery | 회원 | 지연 |
| `/admin` | B. 관리자 홈 | Studio | 큐레이터 | 지연(admin 청크) |
| `/admin/exhibitions/:date` | B-2. 업로드 | Studio | 큐레이터 | admin |
| `/admin/exhibitions/:date/theme` | B-2-1 | Studio | 큐레이터 | admin |
| `/admin/exhibitions/:date/slots/:position` | B-2-2 | Studio | 큐레이터 | admin |
| `/admin/exhibitions/:date/preview` | 미리보기 | Plain | 큐레이터 | admin |
| `/admin/members` | B-3. 회원 관리 | Studio | 큐레이터 | admin |
| `/admin/settings` | 설정·휴관 공지 | Studio | 큐레이터 | admin |
| `/admin/stats` | B-1 (v1.1) | Studio | 큐레이터 | admin |
| `/admin/stats/members/:memberId` | B-1-1 (v1.1) | Studio | 큐레이터 | admin |
| `*` | 404 | Plain | — | 초기 |

경로 문자열은 `app/router/paths.ts`에만 존재하며 모든 링크는 이 상수를 참조한다.

### 5.2 아카이브 경로 설계

`/archive/:date`가 `/gallery`와 **동일한 컴포넌트를 재사용**한다. 차이는 데이터 소스(`GET /exhibitions/{date}` vs `/current`)와 상단 안내 배너(`지난 전시를 보고 있습니다` + 오늘로 돌아가기)뿐이다(PRD §6.8). 컴포넌트를 복제하지 않고 `mode: 'current' | 'archive'` 프롭으로 분기한다.

**그림 화면도 같은 원리로 두 경로를 갖는다.** `/gallery/artworks/:id`와 `/archive/:date/artworks/:id`는 같은 컴포넌트를 렌더하되 되돌아가기 대상이 다르다 — 전자는 오늘의 갤러리로, 후자는 그 날짜의 갤러리로 돌아간다. **경로에 문맥을 담지 않으면 아카이브에서 그림을 연 사람이 뒤로 갔을 때 오늘의 전시로 튕겨 나간다.** 되돌아가기 대상은 `useGalleryContext()` 훅이 현재 라우트에서 파생하며, 컴포넌트는 문맥을 직접 판단하지 않는다.

### 5.3 가드

| 가드 | 동작 |
|---|---|
| `RequireAuth` | 세션 확인 전에는 스플래시 유지. 미인증이면 `/login?next={경로}`로 치환 이동 |
| `RequireCurator` | 미인증 → `/login`, 회원이지만 비큐레이터 → `/gallery`로 조용히 이동(관리자 존재를 노출하지 않음) |
| `RedirectIfAuthed` | 로그인·가입 화면에서 이미 세션이 있으면 `/gallery` |
| `RequirePasswordChange` | `must_change_password`이면 `/password/change`로 강제. 예외는 로그아웃 경로뿐 |

가드는 **세션 부트스트랩 완료 후에만** 판정한다. 미완료 상태에서 리다이렉트하면 새로고침마다 로그인 화면이 번쩍인다.

### 5.4 코드 스플리팅

| 청크 | 포함 | 목표 크기(gzip) |
|---|---|---|
| `main` | 셸·라우터·프로바이더·shared/ui 핵심·세션·A·A-1 | ≤ 60KB |
| `gallery` | C·C-2 | ≤ 35KB |
| `gallery-extra` | C-1·C-3·C-4 | ≤ 20KB |
| `admin` | B 계열 전부 + `@dnd-kit` | ≤ 120KB |
| `vendor-react` | react·react-dom·router | ≤ 60KB |
| `vendor-query` | TanStack Query | ≤ 15KB |

**관리자 청크는 관람자 경로에서 절대 로드되지 않는다.** `RequireCurator` 라우트 아래에서만 `lazy()`로 참조하며, 번들 분석 스크립트가 관람자 청크에 admin 모듈이 섞이면 빌드를 실패시킨다.

---

## 6. 상태 관리

### 6.1 상태의 4분류

| 종류 | 소유자 | 예 |
|---|---|---|
| **서버 상태** | TanStack Query | 전시, 그림, 회원 목록, 설정 |
| **URL 상태** | React Router | 현재 그림 ID, 아카이브 날짜, 목록 필터·페이지 |
| **전역 클라이언트 상태** | Zustand (3개 스토어) | 세션, 토스트, 뷰어 |
| **지역 상태** | `useState`/`useReducer` | 폼 입력, 열림/닫힘, 스와이프 진행 |

**목록의 필터·검색어·페이지는 URL에 둔다.** 관리자가 특정 필터 상태를 새 탭으로 열거나 새로고침해도 유지되어야 한다.

### 6.2 Zustand 스토어

| 스토어 | 상태 | 비고 |
|---|---|---|
| `sessionStore` | `user`, `status`(`booting`/`authenticated`/`anonymous`), `mediaExpiresAt` | 서버 상태이기도 하지만 라우팅 가드가 동기적으로 읽어야 하므로 스토어에 미러링한다. **원천은 Query이고 스토어는 구독 결과를 반영**한다 |
| `toastStore` | 현재 토스트 1개 | 동시 1개(디자인 문서 §8.1) |
| `viewerStore` | 전체화면 뷰어 열림 여부·대상 그림·줌 상태 | 라우팅과 무관한 오버레이 |

**스토어를 4개째 만들고 싶어지면 그 상태가 서버 상태거나 URL 상태다.** 재검토한다.

### 6.3 Query 정책

| 대상 | staleTime | gcTime | refetchOnFocus | 비고 |
|---|---|---|---|---|
| `/public/landing` | 60초 | 10분 | O | |
| `/exhibitions/current` | 5분 | 24시간 | O | 포커스 복귀 시 새 전시 확인 |
| `/exhibitions/{date}` | 무한 | 24시간 | X | 과거 전시는 불변 |
| `/exhibitions` (아카이브) | 5분 | 1시간 | X | 무한 스크롤 |
| `/artworks/{id}` | 무한 | 24시간 | X | |
| `/me` | 5분 | 1시간 | O | |
| 관리자 달력·편집 | 0 | 5분 | O | 운영 데이터는 항상 최신 |
| 통계 | 60초 | 10분 | O | |

**전역 기본값** — `retry`: 네트워크·5xx만 2회(지수 백오프 300ms→1.2s), 4xx는 재시도 없음. `throwOnError`: 라우트 경계에서만 true.

### 6.4 낙관적 업데이트

| 대상 | 처리 |
|---|---|
| C-4 알림 on/off, 큰 글씨 | **낙관적 반영.** 실패 시 롤백 + 토스트 |
| 관리자 자동 저장 | 낙관적이지 않다. `SaveIndicator`로 진행 상태를 명시 |
| 차단·숨김 | 낙관적이지 않다. 되돌리기 어려운 조작은 서버 응답을 기다린다 |
| 열람 표식 | 낙관적 반영(즉시 표식 표시). 기록 API 실패해도 롤백하지 않는다 |

---

## 7. API 계층

### 7.1 `httpClient`의 책임

1. 기본 URL·`credentials: 'include'`·`X-Requested-With` 헤더 부착
2. 응답 봉투 해석 → 성공이면 `data`만 반환, 실패면 `ApiError`를 throw
3. `304` 처리(Query 캐시 유지)
4. 네트워크 오류를 `ApiError(code: 'NETWORK_OFFLINE')`으로 정규화
5. `401 AUTH_SESSION_EXPIRED`/`AUTH_SESSION_REVOKED` 수신 시 **세션 초기화 + `/login` 이동**을 1회만 트리거
6. `meta.request_id`를 오류 객체에 보존(사용자 문의 대응)
7. 요청 타임아웃 10초(`AbortController`)

**httpClient 바깥에서 `fetch`를 직접 호출하는 것을 린트로 금지한다.** 예외는 서비스워커와 S3 직접 업로드 두 곳뿐이며 각각 별도 모듈(`features/notification/lib`, `features/admin/exhibition-editor/hooks/useUploadQueue`)에 격리한다.

### 7.2 오류 표시 규칙

| 조건 | 표시 |
|---|---|
| `field_errors`가 있다 | 각 필드 옆에 인라인 표시 (RHF `setError`로 주입) |
| 폼 맥락이고 `field_errors`가 없다 | 폼 상단 배너 |
| 조회 실패(초기 로드) | `ErrorState` + 재시도 |
| 조회 실패(갱신) | 기존 내용 유지 + 토스트 |
| 액션 실패 | 토스트 |
| 오프라인 | 상단 고정 안내 바 |

문구는 **서버의 `error.message`를 우선 사용**하고, 없거나 네트워크 오류인 경우에만 `errorMessages.ts`의 폴백을 쓴다. 프런트가 코드별 문구를 자체 정의해 서버와 어긋나는 상황을 만들지 않는다(FA-4).

### 7.3 쿼리 키 팩토리

각 entity의 `api/keys.ts`가 키를 소유한다. 문자열 배열을 사용처에서 직접 조립하지 않는다.

| 도메인 | 키 형태 |
|---|---|
| exhibition | `['exhibition','current']` / `['exhibition','date',date]` / `['exhibition','archive',{limit}]` |
| artwork | `['artwork','detail',id]` |
| session | `['session']` / `['me']` |
| admin | `['admin','calendar',{from,to}]` / `['admin','exhibition',date]` / `['admin','members',params]` |

무효화는 접두 매칭으로 한다 — 전시 저장 후 `['admin']`과 `['exhibition']`을 무효화하면 관련 화면이 모두 갱신된다.

### 7.4 타입 경계

`shared/api/types.ts`가 **서버 원형(snake_case)** 타입을 갖고, entity의 `model/types.ts`가 **도메인 타입(camelCase)** 을 갖는다. 변환은 entity의 `api/` 안에서만 일어난다.

이 변환을 두는 이유는 명명 통일이 아니라 **API 변경의 파급 차단**이다. 서버가 필드를 바꾸면 수정 지점이 entity 한 곳이다.

---

## 8. 화면 조립 규칙

### 8.1 페이지 컴포넌트의 구조

모든 `*Page.tsx`는 동일한 골격을 갖는다: **(1) 데이터 훅 호출 → (2) 상태 분기(로딩/오류/빈) → (3) 프레젠테이션 컴포넌트 조합**. 페이지에 비즈니스 계산이나 fetch 호출을 직접 두지 않는다.

| 규칙 | 내용 |
|---|---|
| 데이터 접근 | 반드시 훅 경유(`useCurrentExhibition` 등) |
| 상태 분기 | 로딩·오류·빈 상태를 페이지가 명시적으로 렌더한다. 하위 컴포넌트에 위임하지 않는다 |
| 부수효과 | `useEffect`는 기록 전송·포커스 이동·스크롤 복원에만 |
| 프롭 드릴링 | 2단계까지 허용. 그 이상이면 컴포넌트 분해가 잘못된 것이다 |
| 되돌아가기 | 페이지가 `BackLink`의 대상을 명시적으로 지정한다. 하위 컴포넌트가 `history.back()`을 호출하지 않는다 |

### 8.2 부팅 시퀀스

1. `main.tsx` — 프로바이더 마운트, 스플래시(정적 HTML) 유지
2. `SessionProvider` — `GET /auth/session` 1회. 완료 전까지 라우터 렌더 보류
3. 세션 결과에 따라 라우터 진입
4. `/` 진입 시 `GET /public/landing`, `/gallery` 진입 시 `GET /exhibitions/current`

**이미지 URL 복구** — 이미지 URL은 응답에 담겨 오는 만료 있는 presigned URL이다(API 문서 §6.10). 만료되면 전 이미지가 한꺼번에 깨지므로, 이미지 로드 실패가 **연속 3회** 발생하면 그림을 담은 쿼리를 1회 무효화해 새 URL을 받는다. 복구 수단은 `QueryProvider`가 주입하고, 이미지 컴포넌트는 실패 사실만 알린다.

**낙관적 병렬화** — 로컬 스토리지에 "이전 방문에서 인증됨" 마커가 있으면 세션 확인과 `/exhibitions/current`를 **동시에** 시작한다. 세션이 무효로 판명되면 진행 중 요청을 취소하고 로그인으로 보낸다. 이 최적화가 C 화면 도달을 1회 왕복만큼 단축한다(API 문서 §11.1).

### 8.3 스크롤 복원

C(갤러리 그리드) → C-2(그림) → 뒤로가기에서 **그리드 스크롤 위치를 복원**한다. React Router의 기본 복원에 더해 그리드 컨테이너의 스크롤 오프셋을 `sessionStorage`에 라우트 키별로 저장한다. 이미지 지연 로딩 때문에 높이가 나중에 확정되므로, 그리드는 **종횡비 예약으로 초기 높이를 확정**해 복원이 어긋나지 않게 한다.

### 8.4 관리자 미리보기의 컴포넌트 재사용

`PreviewPage`는 `GET /admin/exhibitions/{date}/preview`가 관람자와 **동일한 스키마**를 주므로(API 문서 §9.12), `features/gallery`의 프레젠테이션 컴포넌트를 그대로 렌더한다. 이를 위해 갤러리 컴포넌트는 **데이터를 프롭으로 받는 순수 컴포넌트**와 **데이터를 가져오는 컨테이너**로 분리한다. 미리보기는 전자만 사용한다.

이 분리는 미리보기 하나를 위한 것이 아니라 **관람자 화면을 데이터 없이 테스트·스토리북에 올릴 수 있게** 한다.

**미리보기에서는 기록을 전송하지 않는다.** `viewTracker`는 컨테이너 계층에만 붙어 있으므로 순수 컴포넌트를 렌더하는 미리보기는 자연히 기록 경로를 타지 않는다. 별도 플래그로 억제하지 않는 것이 이 분리의 이점이다.

---

## 9. 성능

### 9.1 목표 (PRD §8.1)

| 지표 | 목표 | 대상 화면 |
|---|---|---|
| LCP | ≤ 2.5초 (4G) | C 갤러리 |
| 그림 표시 | ≤ 1.5초 | C-2 |
| INP | ≤ 200ms | 전 화면 |
| CLS | ≈ 0 | 전 화면 |
| 하루치 전송량 | ≤ 3MB | 12점 열람 |

### 9.2 이미지 전략

| 항목 | 규칙 |
|---|---|
| 그리드 | 상위 6개 `eager` + `fetchpriority="high"`, 나머지 `lazy` (`IntersectionObserver` rootMargin 200px) |
| 플레이스홀더 | LQIP data URL(응답에 포함, 추가 요청 0) |
| 종횡비 | 서버가 준 `aspect_ratio`로 컨테이너 예약 |
| C-2 | 진입 시 `display` 로드, **인접 그림(이전·다음) `display`를 유휴 시간에 프리페치** |
| 원본 | 전체화면 뷰어에서 확대 제스처 시작 시에만 로드. 로드 전까지 display 표시 |
| 포맷 | WebP 단일(대상 브라우저 전부 지원, PRD 부록 B) |

**전송량 산정** — 썸네일 12 × 약 35KB = 420KB, display 12 × 약 180KB = 2.2MB. 합계 약 2.6MB로 목표 이내다. 원본은 명시적 요청 시에만 나가므로 산정에서 제외한다.

### 9.3 기록 전송 규칙

| 기록 | 시점 | 조건 |
|---|---|---|
| 입장(`/exhibitions/{date}/view`) | C 화면 첫 렌더 후 | 세션당 날짜별 1회. `sessionStorage` 마커로 중복 억제 |
| 열람(`/artworks/{id}/view`) | C-2 진입 후 **1.5초 체류** | 스와이프로 스쳐 지나간 그림은 세지 않는다 |

두 요청 모두 **실패해도 재시도 1회 후 조용히 포기**한다. 사용자에게 오류를 보여주지 않는다(FA-7). 화면 이탈 중 전송이 필요하면 `navigator.sendBeacon`을 우선 사용한다.

### 9.4 프리페치

| 계기 | 대상 |
|---|---|
| C 화면 렌더 완료 | 첫 번째 그림의 `GET /artworks/{id}` |
| 썸네일 `pointerdown` | 해당 그림 상세 |
| C-2 진입 | 인접 그림 상세 + display 이미지 |
| `/admin` 진입 | 오늘 날짜 편집 데이터 |

프리페치는 `navigator.connection.saveData`가 켜져 있거나 `effectiveType`이 `2g`면 **모두 비활성화**한다.

### 9.5 렌더 성능

- 12개 썸네일 그리드는 가상화하지 않는다(항목이 12개다). 대신 `React.memo`로 개별 썸네일의 리렌더를 차단한다.
- 스와이프 중 `transform`은 `requestAnimationFrame` 기반으로 갱신하고 React 상태를 매 프레임 업데이트하지 않는다.
- 관리자 회원 목록은 100행을 넘으면 페이지네이션으로 처리하며 가상화하지 않는다.

---

## 10. PWA · 오프라인 · 푸시

### 10.1 캐시 전략 (Workbox)

| 자원 | 전략 | 만료 |
|---|---|---|
| 앱 셸(JS/CSS/HTML) | Precache + `CacheFirst` | 배포마다 갱신 |
| 폰트 | `CacheFirst` | 1년 |
| `/media/artworks/*` | `CacheFirst` | 30일 / 최대 200개 |
| `GET /api/exhibitions/current` | `NetworkFirst` (타임아웃 3초) | 7일 |
| `GET /api/exhibitions/{date}` | `NetworkFirst` | 7일 |
| `GET /api/public/landing` | `NetworkFirst` (타임아웃 2초) | 1일 |
| 그 외 API | `NetworkOnly` | — |

**오프라인 동작** — 네트워크가 없으면 마지막으로 본 전시를 캐시에서 렌더하고 상단에 안내 바를 띄운다(PRD §6.5). 관리자 화면은 오프라인을 지원하지 않으며 명시적 안내를 보여준다.

### 10.2 업데이트 처리

새 서비스워커가 감지되면 **즉시 갱신하지 않는다.** 하단에 `새 버전이 있습니다 · 새로고침` 안내를 띄우고 사용자가 누를 때 적용한다. 그림을 보는 도중 화면이 리로드되는 일이 없어야 한다.

### 10.3 푸시 구독 흐름

| 단계 | 동작 |
|---|---|
| 1 | 가입 완료 직후(PRD §6.4) 또는 C-4 설정에서 시작 |
| 2 | iOS이고 standalone이 아니면 **`IosInstallGuide`를 먼저** 표시(홈 화면 추가 안내). 권한 요청을 하지 않는다 |
| 3 | `Notification.requestPermission()` |
| 4 | 허용 시 `pushManager.subscribe(VAPID public key)` |
| 5 | `POST /me/push-subscriptions` |
| 6 | 거부 시 재요청하지 않는다. C-4에 "알림이 차단되어 있습니다 · 브라우저 설정에서 허용" 안내만 |

**구독 재검증** — 앱 부팅 시 `GET /me/push-subscriptions`로 서버 등록 목록을 받아 브라우저의 현재 구독(`endpoint`)과 대조한다. 서버에 없거나 endpoint가 바뀌었으면 재등록하고, 브라우저 구독이 사라졌는데 서버에 남아 있으면 해당 구독을 해제한다. 이 대조는 **부팅당 1회**만 수행한다.

### 10.4 서비스워커 커스텀 핸들러

| 이벤트 | 동작 |
|---|---|
| `push` | 페이로드의 `title`·`body`·`url`·`tag`로 알림 표시. 파싱 실패 시 기본 문구 |
| `notificationclick` | 이미 열린 탭이 있으면 포커스 후 `/`로 이동, 없으면 새로 연다 (PRD §6.12 — 모든 진입은 A를 거친다) |
| `pushsubscriptionchange` | 재구독 후 서버 갱신 |

### 10.5 매니페스트

`display: standalone`, `orientation: portrait`, `theme_color`·`background_color`는 `--gk-bg-canvas`와 동일. 아이콘 192/512/maskable. `start_url: "/"`.

---

## 11. 접근성

| 항목 | 구현 |
|---|---|
| 큰 글씨 모드 | `FontScaleProvider`가 `html[data-font-scale]`을 동기화. 서버 값(`user.font_scale`)이 원천, 로컬 캐시로 초기 깜빡임 방지 |
| 포커스 관리 | 라우트 전환 시 메인 랜드마크로 포커스 이동 + 화면 제목을 `aria-live="polite"`로 알림 |
| 랜드마크 | 각 페이지 `main`, 하단 네비 `nav[aria-label]` |
| 이미지 대체 텍스트 | `{제목} – {작가}` (디자인 문서 §9) |
| 그리드 시맨틱 | `ul`/`li` + 링크. `div` 나열 금지 |
| 전체화면 뷰어 | `role="dialog"` + `aria-modal` + 포커스 트랩 + `Esc` 닫기 |
| 스와이프 대체 | 좌우 화살표 키, 화면 하단 이전/다음 텍스트 링크 |
| 확대 대체 | `크게 보기` 버튼(핀치 제스처를 모르는 사용자용, PRD §5.2) |
| 축소 애니메이션 | `prefers-reduced-motion` 전역 대응 |
| 폼 | 라벨 연결, `aria-invalid`, `aria-describedby`로 오류·힌트 연결 |
| 검증 | `axe-core`를 컴포넌트 테스트와 E2E에 통합 |

---

## 12. 보안

| 항목 | 조치 |
|---|---|
| 토큰 | JS가 접근하지 않는다(HttpOnly 쿠키). `localStorage`에 자격 정보 저장 금지 |
| CSRF | 모든 변경 요청에 `X-Requested-With: gallery-k` (httpClient가 자동 부착) |
| XSS | `dangerouslySetInnerHTML` 전면 금지(린트). 전시 테마·설명의 줄바꿈은 CSS `white-space: pre-line`으로 처리 |
| CSP | `default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'` — CloudFront 응답 헤더로 주입 |
| 검색 노출 | `robots.txt` 전체 차단 + `<meta name="robots" content="noindex,nofollow">` (PRD §8.4) |
| OG | 제목·설명 텍스트 + `media/public/entrance.jpg`. **작품 이미지는 OG에 절대 넣지 않는다** |
| 로그 | 콘솔 로그에 전화번호·이름을 남기지 않는다. 프로덕션 빌드에서 `logger`가 no-op |
| 소스맵 | 프로덕션 소스맵을 공개 경로에 배포하지 않는다 |
| 의존성 | `npm audit` CI + 주 1회 갱신 PR |

### 12.1 관리자 UI 은닉의 의미

`Curator K` 링크를 숨기고 `/admin` 접근 시 조용히 리다이렉트하는 것은 **UI 편의일 뿐 보안이 아니다**(PRD §8.4). 실제 통제는 서버가 한다. 프런트는 이를 전제로 하며, 관리자 API 응답을 회원 화면에서 다루는 코드를 두지 않는다.

---

## 13. 오류 경계와 복원력

| 계층 | 처리 |
|---|---|
| 루트 `AppErrorBoundary` | 렌더 예외 → 전체 화면 `ErrorState` + 새로고침 유도. `request_id`가 있으면 함께 표시 |
| 라우트 경계 | 라우트별 `errorElement`. 다른 화면으로 이동은 가능한 상태 유지 |
| 위젯 경계 | 그리드·이미지·통계 카드 등 부분 실패 격리 |
| 청크 로드 실패 | 배포 직후 흔한 문제. 자동 1회 새로고침 후 실패하면 안내 |
| 오프라인 | 상단 안내 바 + 캐시 렌더 |

**A 첫 화면은 예외다.** 어떤 API가 실패해도 정문 이미지와 버튼이 보이도록, `LandingPage`는 데이터 없이도 완전한 레이아웃을 렌더한다(PRD §6.1).

---

## 14. 테스트 전략

| 종류 | 대상 | 도구 | 기준 |
|---|---|---|---|
| 단위 | 훅·유틸·폼 스키마 | Vitest | 로직 분기 100% |
| 컴포넌트 | `shared/ui` 전 상태, entity UI | Testing Library + axe | 상태 전수 |
| 통합 | 페이지 + MSW 목 API | Vitest + MSW | 화면별 로딩/성공/오류/빈 상태 |
| E2E | 핵심 여정 | Playwright | §14.1 |
| 시각 회귀 | 관람자 4화면 × 2모드 | Playwright 스냅샷 | 디자인 문서 §12.2 |

### 14.1 반드시 있어야 하는 E2E

| # | 시나리오 |
|---|---|
| E-1 | 가입 → 자동 로그인 → C 진입 → 그림 열람 → 스와이프 → 갤러리 복귀 |
| E-2 | 로그인 → 연장 중인 전시에서 `8월 30일의 전시` 표시 확인 |
| E-3 | 아카이브에서 지난 전시 열기 → 오늘로 돌아가기 |
| E-4 | 설정에서 알림 끄기 → 재진입 시 유지 |
| E-5 | 큰 글씨 모드 전환 → 그리드 2열 확인 |
| E-6 | 관리자: 제목·테마 입력 → 12장 업로드 → 발행 상태 Y 전환 |
| E-7 | 관리자: 과거 미발행일의 이어쓰기 |
| E-8 | 오프라인 상태에서 C 화면 캐시 렌더 |
| E-9 | 비큐레이터가 `/admin` 직접 접근 시 갤러리로 이동 |

**MSW 핸들러는 API 문서의 응답 스키마를 그대로 구현**하며, 백엔드 계약 변경 시 핸들러 갱신이 함께 이뤄지지 않으면 통합 테스트가 실패하도록 스키마 검증을 포함한다.

---

## 15. 빌드 · 환경 · 배포

### 15.1 환경 변수

| 변수 | 예 | 용도 |
|---|---|---|
| `VITE_API_BASE_URL` | `/api` | 동일 오리진이므로 상대 경로 |
| `VITE_VAPID_PUBLIC_KEY` | | 푸시 구독 |
| `VITE_APP_ENV` | `dev`/`staging`/`prod` | |
| `VITE_SENTRY_DSN` | (선택) | 오류 수집 |

`shared/config/env.ts`가 부팅 시 **필수 변수 존재를 검증하고 실패 시 명시적으로 죽는다.** 누락된 변수로 런타임 중간에 실패하는 것보다 낫다.

### 15.2 빌드 산출물

| 항목 | 설정 |
|---|---|
| 타깃 | `es2022` (iOS Safari 16.4+, PRD 부록 B) |
| 청크 | §5.4 수동 분할(`manualChunks`) |
| 해시 | 컨텐츠 해시 파일명 + `index.html` 무캐시 |
| 압축 | brotli(CloudFront) |
| 분석 | `rollup-plugin-visualizer`. 예산 초과 시 빌드 실패 |

### 15.3 배포

S3 동기화 → CloudFront 무효화(`/index.html`, `/manifest.webmanifest`, `/sw.js`만). 해시 자산은 무효화 대상이 아니다. 배포 금지 시간대는 백엔드와 동일(07:00–09:00 KST).

---

## 16. 코딩 규약

| 항목 | 규칙 |
|---|---|
| 파일명 | 컴포넌트 `PascalCase.tsx`, 훅 `useCamelCase.ts`, 그 외 `camelCase.ts` |
| 컴포넌트 | 함수 선언 + named export. default export는 라우트 lazy 대상만 |
| 타입 | `interface`는 확장 대상에만, 나머지는 `type`. `any` 금지, `unknown` 후 좁히기 |
| 프롭 | 5개 초과 시 객체로 묶거나 컴포넌트를 분해한다 |
| 훅 | 한 훅은 한 관심사. 반환값이 5개를 넘으면 분해 신호 |
| 조건부 렌더 | 삼항 중첩 금지. 2단계 이상이면 早期 return 또는 서브컴포넌트 |
| 주석 | "무엇"이 아니라 "왜". 도메인 규칙 참조는 PRD 절 번호를 적는다 |
| import | 절대 경로 별칭(`@/app`, `@/features`, `@/entities`, `@/shared`) |
| 매직 값 | `shared/config/constants.ts`. 12·30 같은 숫자를 화면에 직접 쓰지 않는다 |
| 사용자 문구 | `shared/config/messages.ts`. JSX에 한국어 문자열을 직접 쓰지 않는다(예외: 스토리북 데모) |

---

## 17. PRD 대비 보완 사항

| # | 근거 | 이 문서의 결정 |
|---|---|---|
| **F-1** | PRD §6.7 (스와이프로 12점) | `SwipePager` + 인접 그림 프리페치. 탭 23회 → 12회를 실제로 달성하려면 전환이 즉시여야 한다 |
| **F-2** | PRD §5.2 (시니어) | 스와이프·핀치의 **명시적 대체 조작**(버튼·링크·키보드)을 전 제스처에 의무화 |
| **F-3** | GAP-13 (큰 글씨) | 서버 값을 원천으로, 로컬 캐시로 초기 깜빡임 방지. 그리드 열 수까지 토큰으로 전환 |
| **F-4** | PRD §6.1 (화면은 항상 뜬다) | `LandingPage`를 데이터 무의존 렌더로 설계 |
| **F-5** | PRD §6.5 (오프라인 캐시) | `NetworkFirst` + 마지막 전시 캐시 + 안내 바 |
| **F-6** | PRD §6.10 (미리보기) | 관람자 컴포넌트를 순수/컨테이너로 분리해 재사용. 미리보기용 화면을 별도로 만들지 않는다 |
| **F-7** | PRD §3.2 (일 감상 그림 수) | 열람 기록에 1.5초 체류 조건. 스쳐 지나간 그림을 세면 지표가 무의미해진다 |
| **F-8** | (없음) | 관리자 청크 격리를 빌드 검증으로 강제. 관람자 첫 화면 예산을 지키는 유일한 방법 |
| **F-9** | (없음) | 세션·전시 병렬 부팅. C 도달 왕복을 1회 줄인다 |
| **F-10** | (없음) | 서비스워커 업데이트를 사용자 확인 후 적용. 감상 중 리로드 방지 |
| **F-11** | 교차 검토 | 마이크로카피를 `shared/config/messages.ts` 단일 원천으로 규정(UX 문서 §5와 1:1) |
| **F-12** | 교차 검토 | presigned 이미지 URL 만료 복구 규칙 명문화. 만료 시 전 이미지가 한꺼번에 깨지는 단일 실패 지점이다 |
| **F-13** | 교차 검토 | 푸시 구독 대조에 `GET /me/push-subscriptions` 사용을 명시(해당 엔드포인트를 API 문서에 추가) |
| **F-14** | 교차 검토 | `/archive/:date/artworks/:id` 경로 추가 | 아카이브에서 연 그림의 되돌아가기 대상이 오늘의 갤러리로 튕기는 문제 |
| **F-15** | 교차 검토 | 컴포넌트 소속 판정표(§4.2) 추가 | 디자인 카탈로그와 디렉터리의 대응이 불명확했다 |
