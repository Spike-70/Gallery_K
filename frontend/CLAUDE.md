# 프런트엔드 개발 Rule

기준: `docs/03-DESIGN-SYSTEM.md`(DS) · `docs/05-FRONTEND-ARCHITECTURE.md`(FA) · `docs/06-USER-EXPERIENCE.md`(UX) · `docs/02-API-SPEC.md`(API).
설계 문서와 실제 구현이 다르면 **구현이 기준**이며, 차이는 §13에 있다.

## 1. 스택 · 명령

React 19 / Vite / TS / Tailwind 3 + CVA / TanStack Query 5 / Zustand 5 / RHF 7 + Zod 4 / react-router-dom 7.
`npm run verify` = typecheck → lint(oxlint) → lint:layers → lint:design → test → build. **작업 종료 전 필수.**

## 2. 레이어

`app → features → entities → shared` 단방향. 임포트는 항상 `@/` 절대 경로.

금지: 기능 간 상호 참조 / `entities→features,app` / `shared→상위` / 타 기능 내부 파일 깊게 참조(`index.ts`만) / 순환.
예외는 `.dependency-cruiser.cjs`에만 존재한다. 규칙을 우회하지 말고 공통을 한 층 위로 올린다.

배치: 한 화면 전용 → `features/{기능}/` · 두 기능 이상이 쓰는 도메인 개념 → `entities/{도메인}/` · 도메인 무지식 → `shared/` · 라우터·프로바이더·레이아웃 → `app/`.

## 3. 새로 만들기 전에 확인

`shared/ui/index.ts`(컴포넌트) → `shared/hooks`·`shared/lib`(훅·유틸) → `shared/config/messages.ts`(문구) → `shared/config/constants.ts`(숫자) → `shared/config/paths.ts`·`shared/api/endpoints.ts`(경로) → `entities/*/api`(쿼리·매퍼).
문구·숫자·경로를 코드에 직접 쓰지 않는다. JSX 한국어 리터럴은 `lint:design`이 빌드 실패로 막는다.

## 4. shared/ui (프리미티브 · `@/shared/ui`에서만 임포트)

BackLink · BackLinkGroup · TopBackSlot · Badge · Banner · BottomSheet · Button(+buttonVariants) · LinkButton · CharCounter · Checkbox · DateField · Dialog · AlertDialog · Divider · EmptyState · ErrorState · FieldGroup(+fieldIds) · FilterChip · Icon(+ICON_NAMES) · IconButton · Menu · ProgressRing · PullToRefresh · Skeleton · ScreenSkeleton · Spinner · StatusChip · Switch · TextArea · TextField · TextLink · TextButton · TimeSelectSheet · ToastViewport · toast

**도메인 타입을 prop으로 받지 않는다.** 변형은 CVA로 추가하고 래퍼를 새로 만들지 않는다. 아이콘은 `ICON_NAMES`에서 고르고, 없으면 `public/icons.svg`에 심볼 추가 후 목록에 등록한다.

## 5. shared/hooks · lib · config · types

- hooks: useDebouncedValue · useFocusTrap · useIntersection · useInterval · useLockBodyScroll · useMediaQuery(useIsDesktop) · useOnlineStatus · usePrevious · usePullToRefresh · useScrollRestoration · useSwipe · useVisibilityChange
- lib: `cn`(clsx+tailwind-merge, 클래스 병합은 항상 이것) · `date`(formatFullDate/ShortDate/ArchiveDate/MonthDay, toIsoDate, dateSeries, timeOptions) · `phone`(normalize/format/mask/isValid) · `platform`(isIos, isStandalone, needsIosInstallGuide, supportsPush, detectPushPlatform, shouldPrefetch) · `storage`(localStore/sessionStore + STORAGE_KEYS/SESSION_KEYS — `localStorage` 직접 접근 금지) · `formErrors`(applyApiError) · `logger`(console 직접 호출 금지) · `assert`(assert/assertNever)
- config: `messages`(actions·landmarks·screenTitles·push·brand·status·templates·screens·validation) · `paths`(paths·routePatterns·loginPathWithNext) · `constants` · `env`
- types: `enums`(USER_ROLES·FONT_SCALES·CREATED_VIA·IMAGE_STATUSES·EXHIBITION_DAY_STATUSES·EDIT_MODES·PUSH_PLATFORMS·PUSH_STATUSES — 문자열 유니온은 여기에 `as const` 배열 + 파생 타입으로) · `utility`(IsoDate·IsoDateTime·TimeOfDay·Uuid·Nullable·AsyncState·GalleryMode)

## 6. shared/api (서버 계약의 유일한 소유자)

| 파일 | 역할 |
|---|---|
| `httpClient` | get/post/put/patch/delete(=`data`만 반환) · `requestWithMeta`(페이지네이션) · `beacon`(기록 전용, 실패 무시). `fetch` 직접 호출 금지 |
| `ApiError` | `isApiError` · `ERROR_CODES` · `CLIENT_ERROR_CODES`. 코드 비교는 리터럴이 아닌 상수로 |
| `errorMessages` | `resolveErrorMessage`(서버 문구 우선). 프런트가 코드별 문구를 새로 정의하지 않는다 |
| `endpoints` | URL 경로 상수 |
| `queryClient` | `CACHE_POLICY`(landing·currentExhibition·pastExhibition·archive·artwork·me·admin·stats). staleTime/gcTime 숫자를 쿼리에 직접 쓰지 않는다 |
| `pagination` | `toCursorPage`/`toNumberedPage` |
| `envelope` | 봉투 타입 · `isSuccessEnvelope` · `createMeta` |
| `types` | 서버 원형 `Raw*` 타입(snake_case). **바깥으로 새어 나가지 않는다** |

## 7. entities (도메인)

도메인: `exhibition`(+admin) · `artwork` · `member` · `notice` · `session` · `appSetting`.

`api/` 4분할 고정: `keys.ts`(쿼리 키 팩토리, `all`+파생 · 무효화는 접두 매칭) · `*Api.ts`(Raw 호출 + 매퍼 적용) · `mappers.ts`(`Raw* → 도메인`, camelCase 변환은 여기서만) · `queries.ts`(`use*Query`/`use*Mutation` 훅). `model/types.ts`에 도메인 타입과 순수 헬퍼.

기존 도메인 헬퍼(중복 작성 금지): `artworkAltText` · `isCurator` · `slotVisualState` · `summarizeBlockers` · `settingValue` · `needsIosGuide` · `useGalleryContext`(현재/아카이브/미리보기 문맥과 되돌아갈 경로 파생 — 컴포넌트가 문맥을 직접 판단하지 않는다) · `useSessionStore`/`sessionSnapshot` · `registerMediaRecovery`.

주의: 사용자 개인 설정은 `session/api/meApi.updateSettings`, 전역 운영 설정은 `appSetting/api/settingApi.updateSettings`. 동명이지만 다른 것이다.

## 8. features (화면)

landing · auth · gallery · exhibition-theme · artwork · archive · settings · notification · errors · admin/{dashboard, exhibition-editor, members, settings, stats}.

- 폴더 하나로 완결: `XxxPage.tsx` + `components/` + `hooks/` + `model/` + `index.ts`(공개 표면, 라우터가 보는 유일한 경로).
- 페이지 골격 3단: **데이터 훅 → 상태 분기(pending/error/empty) → 표현 컴포넌트 조합.** 상태 분기를 하위 컴포넌트에 위임하지 않는다.
- 데이터 접근·폼 제출은 `hooks/`로 뺀다. 페이지 파일에 `useMutation`을 직접 쓰지 않는다.
- 재사용 대상이 생기면 순수 표현 컴포넌트를 분리하고 `index.ts`로 공개한다(예: `GalleryView` ↔ `GalleryPage`).
- 한 기능 전용 데이터는 feature-local `api/`를 허용한다(`landing`, `admin/stats`). 두 번째 사용처가 생기면 `entities`로 올린다.
- 기존 기능 훅(중복 금지): useLanding · useLogin · useSignup · useGalleryExhibition · useArtworkNavigation · useArtworkViewLog · usePinchZoom · useCalendar · useAutoSave · useUploadQueue · useSlotPolling · usePushSubscription · useUpdateSettings · useWithdraw.

## 9. 라우팅 (app/)

- 주소는 `paths`, 라우트 정의는 `app/router/index.tsx`(파라미터는 `routePatterns`). 가드: `RequireAuth`(+`loginPathWithNext`) · `RequireCurator` · `RedirectIfAuthed`.
- 레이아웃 `GalleryLayout`(관람자) · `StudioLayout`(관리자) · `PlainLayout`(단독)이 컨테이너 클래스를 소유한다.
- 지연 로드는 `lazyRoute()`로만 감싼다(청크 실패 시 1회 자동 새로고침). `default export`는 lazy 대상에서만.
- **관리자 화면은 `RequireCurator` 아래 lazy 참조만.** 관람자 경로 유입은 `check-bundle.mjs`가 빌드 실패로 막는다.
- 페이지가 `BackLink`/`BackLinkGroup`을 하나만 두면 상단 `←`는 `TopBackSlot`으로 포털된다. 상단 뒤로가기를 따로 그리지 않는다.
- 열람·입장 기록은 `app/analytics/viewTracker.ts`(컨테이너에서만 호출, 실패 무시).

## 10. 스타일

- 의미 토큰만 사용. 값의 실체는 `src/styles/tokens.css`, 노출은 `tailwind.config.js`.
- `colors`·`fontSize`·`spacing`은 **덮어썼다.** 스케일 밖 클래스(`text-xs`, `h-7`, `w-32`)는 **CSS가 생성되지 않고 조용히 사라진다.**
- spacing: `0 px 1 2 3 4 5 6 8 10 12 16` + 이름 토큰 `touch · control-sm/md/lg · switch-track · row · row-lg · block · image-preview · icon-lg · full`.
- fontSize: `display · title-lg/md/sm · body-lg/md/sm · caption · label · mono-num`.
- zIndex: `base · sticky · overlay · sheet · dialog · immersive · toast` (`z-[숫자]` 금지).
- 그 외: maxWidth `gallery/reading/studio/form/preview` · radius `sm/md/lg/full` · shadow `sheet/dialog` · duration `instant/fast/base/slow` · ease `standard/decelerate/accelerate` · animation `fade-in/sheet-in/dialog-in/shimmer/spin`.
- 공용 클래스(`base.css`): `gk-container-gallery|reading|studio|form` · `gk-prose` · `gk-artwork-grid` · `gk-sr-only` · `gk-hit-expand` · `gk-shimmer` · `tabular`.
- 금지(빌드 실패): 임의값 `[...]`(`aspect-`·`grid-cols-`·`grid-rows-` 제외) · 원시 색 변수 직접 참조 · 하드코딩 색 · 인라인 `style` · JSX 한국어 문구.
- 큰 글씨 모드는 `html[data-font-scale]` 변수 교체로 처리한다. 컴포넌트에 분기를 만들지 않는다.

## 11. 폼 · 상태 표시

- RHF + Zod. 스키마는 `features/*/model/*Schemas.ts`, 타입은 `z.infer`.
- 필드는 `FieldGroup` + `TextField`/`TextArea`/`DateField`/`Checkbox`/`Switch` 조합. 라벨·힌트·오류 연결은 `fieldIds`가 한다.
- 서버 오류는 `applyApiError(error, setError, fieldMap?)` 한 경로만: `field_errors` → 인라인, 없으면 반환된 문구를 폼 상단 `Banner`로. **다른 오류 표시 경로를 만들지 않는다.**
- 화면 상태: 로딩 `Skeleton`/`ScreenSkeleton`(전체 화면 스피너 금지) · 빈 상태 `EmptyState` · 오류 `ErrorState`(재시도 + requestId) · 공지 `Banner` · 일시 알림 `toast`. 오류 화면에도 되돌아갈 링크를 남긴다.
- 서버 상태는 Query, 화면 조작 상태는 지역 상태 또는 소형 Zustand 스토어(`sessionStore`·`viewerStore`·`toastStore`). 서버 데이터를 스토어에 복사하지 않는다.

## 12. 백엔드 연동

실제 API에 붙어 있다. 목 계층은 없다 — `fetch`는 `httpClient` 안에서만 부르고, 예외는 서비스워커(`src/sw.ts`)와 S3 직접 업로드(`useUploadQueue`)뿐이다.

- 개발: 백엔드 `make serve`(8000) + `npm run dev`(5173). dev 서버가 `/api`를 프록시하며 접두를 뗀다 — `/api`는 배포에서 CloudFront가 붙이는 경로다. 동일 오리진 조건을 로컬에서 재현하는 것이 목적이다.
- 서버 스키마는 **모르는 필드를 거부한다**(`extra="forbid"`). 요청 바디에 화면 편의용 필드를 얹지 않는다.
- 날짜의 "오늘"은 서버가 정한다(`meta.server_date`). 단말 시계로 조회 범위를 역산하지 않는다.
- 새 API 함수: `endpoints.ts`에 경로 추가 → `*Api.ts`에서 `httpClient` 호출 + 매퍼 적용 → `queries.ts`에 훅. `Raw*`는 매퍼 밖으로 나가지 않는다.

### 12.1 소셜 로그인 (카카오·구글)

OAuth 2.0 Authorization Code + PKCE, **리다이렉트 방식**. 기준 문서는 `docs/08-SOCIAL-AUTH.md`.

- 인가 시작(`/api/auth/social/{p}/start`)은 **`httpClient`를 타지 않는다.** `<a href>`의 목적지이며 브라우저가 직접 이동한다 — `fetch`로 부르면 302를 따라가 제공자 HTML을 받게 되고 리다이렉트 방식이 성립하지 않는다. `onClick`도 쓰지 않는다(JS 로드 전 클릭이 무반응이면 대상 사용자는 반복해서 누른다).
- 콜백은 302로 끝나므로 **오류 봉투가 오지 않는다.** 코드만 `?social_error=`로 오고 A-1이 `fallbackMessageFor`로 한국어를 만든다 — `errorMessages`가 유일한 원천인 몇 안 되는 경우다.
- 소셜 버튼은 `entities/session/ui/SocialButtons`. A-1과 D가 함께 쓰므로 `features`가 아니라 `entities`에 있다.
- `SessionUser.hasPassword=false`면 소셜 전용 계정이다. D 설정이 비밀번호 변경 항목을 **감춘다**(비활성이 아니라).
- 연결 티켓·`state`는 전부 HttpOnly 쿠키다. 화면은 읽지 못하며 만료는 `SOCIAL_LINK_EXPIRED`로만 안다.

## 13. 설계 문서와 다른 실제 구현

FA §2가 지정한 `date-fns`·`@dnd-kit`·`vite-plugin-pwa`·MSW·Playwright·Storybook은 **쓰지 않는다.** 날짜는 `shared/lib/date`, 드래그·아이콘은 자체 구현, 서비스워커는 `src/sw.ts` 수기 작성, 테스트는 Vitest + Testing Library다. 의존성 추가 전 기존 무의존 구현을 먼저 확인한다.

## 14. 테스트

`__tests__/`에 두고 `test/utils/renderWithProviders`(route 옵션 지원)로 렌더한다. 프로바이더 조립을 테스트마다 반복하지 않는다.

서버는 `test/utils/apiStub`의 `stubApi({ 'GET /exhibitions/current': () => ... })`로 대체한다. `fetch` 한 지점만 가로채므로 화면·훅·매퍼는 실제 코드 그대로 돈다. 응답은 도메인 타입이 아니라 **서버 원형**(`test/fixtures/server.ts`의 `Raw*` 빌더)으로 만든다 — 그래야 매퍼도 함께 검증된다. 목록은 `paged()`, 오류 봉투는 `apiError()`. 스텁하지 않은 경로는 404가 되며 조용히 통과하지 않는다.
