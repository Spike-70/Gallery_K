# 갤러리 K — 디자인 시스템

| | |
|---|---|
| **문서 버전** | v1.0 |
| **작성일** | 2026-08-27 |
| **상위 문서** | `docs/PRD.md` v1.1 |
| **구현 기술** | TailwindCSS v3 + CSS Custom Properties + React 19 |
| **상태** | 확정 (구현 기준선) |

---

## 1. 설계 원칙

제품 원칙 4 — **"UI는 액자다. 액자가 그림보다 눈에 띄면 실패다."** 이 문서의 모든 결정은 이 문장에서 파생된다.

| # | 원칙 | 구체적 규칙 |
|---|---|---|
| **DS-1** | **색을 쓰지 않는다** | 관람자 화면의 UI 색상은 무채색 6단계와 단 하나의 강조색뿐이다. 그림에서 나오는 색이 화면의 유일한 채도다 |
| **DS-2** | **면적을 비운다** | 여백은 장식이 아니라 구조다. 요소 사이 간격은 8px 배수 스케일 밖으로 나가지 않는다 |
| **DS-3** | **글자는 크게** | 본문 최소 17px, 큰 글씨 모드 20px(GAP-13). 12px 이하 폰트 크기를 토큰에 정의하지 않는다 — 정의되지 않으면 쓸 수 없다 |
| **DS-4** | **손가락이 닿는 곳은 48px** | 모든 상호작용 요소의 히트 영역은 최소 48×48px. 시각적 크기가 작아도 히트 영역을 확장한다 |
| **DS-5** | **색만으로 말하지 않는다** | 상태는 색 + 문자(또는 아이콘)로 이중 표기한다(§8.3 발행 상태 칩) |
| **DS-6** | **두 개의 표면, 하나의 시스템** | 관람자 화면(Gallery)과 관리자 화면(Studio)은 밀도와 폭이 다르지만 토큰·프리미티브를 공유한다. 컴포넌트를 두 벌 만들지 않는다 |
| **DS-7** | **토큰 없이 값을 쓰지 않는다** | 임의 값(`text-[13px]`, `#8a8a8a`)은 린트로 차단한다. 예외는 그림 이미지의 종횡비 계산뿐이다 |

---

## 2. 토큰 아키텍처

### 2.1 3계층 구조

| 계층 | 이름 | 형태 | 예 | 변경 빈도 |
|---|---|---|---|---|
| **1. 원시(Primitive)** | 값 그 자체 | CSS 변수 `--gk-<범주>-<단계>` | `--gk-neutral-700: #3d3a36` | 거의 없음 |
| **2. 의미(Semantic)** | 역할에 매핑 | CSS 변수 `--gk-<역할>` | `--gk-text-primary: var(--gk-neutral-800)` | 낮음 |
| **3. 컴포넌트** | 컴포넌트 전용 | Tailwind 유틸 조합 (`cva` variant) | `button--primary` | 보통 |

**Tailwind는 2계층만 소비한다.** `tailwind.config.js`의 `theme.extend`가 의미 토큰(CSS 변수)을 참조하고, 컴포넌트는 Tailwind 유틸리티만 쓴다. 원시 값을 컴포넌트가 직접 참조하는 것을 금지한다.

이 구조가 필요한 이유는 **큰 글씨 모드**와 **전체화면 뷰어(다크)** 때문이다. 둘 다 의미 토큰의 값만 교체해서 구현되며 컴포넌트 코드는 한 줄도 바뀌지 않는다.

### 2.2 토큰 적용 스코프

| 스코프 | 선택자 | 교체 대상 |
|---|---|---|
| 기본 | `:root` | 전체 의미 토큰 |
| 큰 글씨 | `html[data-font-scale="large"]` | 타이포 스케일, 그리드 열 수 |
| 몰입 뷰어 | `.gk-immersive` (전체화면 뷰어 컨테이너) | 표면·텍스트 색 |
| 관리자 | `html[data-surface="studio"]` | 밀도 토큰(간격·행 높이) |

---

## 3. 색

### 3.1 원시 팔레트

무채색은 **따뜻한 회색(warm gray)** 계열이다. 순수 회색은 그림의 색을 차갑게 보이게 한다.

| 토큰 | 값 | 용도 |
|---|---|---|
| `--gk-neutral-0` | `#ffffff` | 카드·시트 표면 |
| `--gk-neutral-50` | `#faf9f7` | 페이지 배경(기본) |
| `--gk-neutral-100` | `#f2f0ec` | 구분 표면, 스켈레톤 |
| `--gk-neutral-200` | `#e4e1db` | 경계선 |
| `--gk-neutral-300` | `#cbc7bf` | 비활성 경계 |
| `--gk-neutral-400` | `#a8a39a` | 플레이스홀더 |
| `--gk-neutral-500` | `#807a70` | 보조 텍스트(대비 4.6:1) |
| `--gk-neutral-600` | `#5f5a52` | 강한 보조 텍스트 |
| `--gk-neutral-700` | `#403c36` | 본문 |
| `--gk-neutral-800` | `#2a2724` | 제목 |
| `--gk-neutral-900` | `#1a1816` | 최고 대비 |
| `--gk-ink-black` | `#0b0a09` | 몰입 뷰어 배경 |
| `--gk-accent-500` | `#8c6a3f` | **유일한 강조색.** 액자 금박에서 온 톤 |
| `--gk-accent-600` | `#6f5330` | 강조 hover·활성 |
| `--gk-accent-050` | `#f5efe4` | 강조 배경(선택 상태) |
| `--gk-success-500` | `#3f7a4f` | 발행됨(Y) |
| `--gk-warning-500` | `#b0762a` | 준비 안 됨(N) |
| `--gk-danger-500` | `#a83c34` | 파괴적 동작·오류 |
| `--gk-info-500` | `#3a6079` | 정보 안내 |

**상태색 4종은 관리자 화면(Studio)과 오류 표시 전용**이다. 관람자 화면의 정상 상태에는 등장하지 않는다(DS-1).

### 3.2 의미 토큰

| 토큰 | 기본값 | 몰입 뷰어 | 용도 |
|---|---|---|---|
| `--gk-bg-canvas` | `neutral-50` | `ink-black` | 페이지 배경 |
| `--gk-bg-surface` | `neutral-0` | `ink-black` | 카드·시트 |
| `--gk-bg-subtle` | `neutral-100` | `#151311` | 구분 영역·스켈레톤 |
| `--gk-bg-overlay` | `rgba(26,24,22,.55)` | `rgba(0,0,0,.85)` | 모달 backdrop |
| `--gk-text-primary` | `neutral-800` | `neutral-50` | 제목·본문 |
| `--gk-text-secondary` | `neutral-600` | `neutral-300` | 부가 정보 |
| `--gk-text-tertiary` | `neutral-500` | `neutral-400` | 캡션·메타 |
| `--gk-text-placeholder` | `neutral-400` | — | 입력 placeholder |
| `--gk-text-inverse` | `neutral-0` | `neutral-900` | 어두운 배경 위 텍스트 |
| `--gk-text-accent` | `accent-600` | `accent-500` | 링크·강조 |
| `--gk-border-default` | `neutral-200` | `rgba(255,255,255,.14)` | 기본 경계 |
| `--gk-border-strong` | `neutral-300` | `rgba(255,255,255,.28)` | 입력 필드 |
| `--gk-border-focus` | `accent-500` | `accent-500` | 포커스 링 |
| `--gk-action-primary-bg` | `neutral-800` | — | 기본 버튼 배경 |
| `--gk-action-primary-fg` | `neutral-0` | — | |
| `--gk-action-danger-fg` | `danger-500` | — | 탈퇴 등 |
| `--gk-status-published` | `success-500` | — | Y |
| `--gk-status-empty` | `warning-500` | — | N |
| `--gk-status-carried` | `neutral-500` | — | ↑ (회색, PRD §6.9) |

### 3.3 명도 대비 검증 기준

| 조합 | 대비 | 기준 |
|---|---|---|
| `text-primary` on `bg-canvas` | 12.8:1 | AAA |
| `text-secondary` on `bg-canvas` | 6.9:1 | AA+ |
| `text-tertiary` on `bg-canvas` | 4.6:1 | AA (본문 4.5:1) |
| `text-accent` on `bg-canvas` | 5.4:1 | AA |
| `action-primary-fg` on `action-primary-bg` | 13.9:1 | AAA |
| `status-*` on `bg-canvas` | ≥ 4.5:1 | AA |

`text-tertiary`는 **캡션 전용**이며 본문에 쓰지 않는다. 빌드 시 대비 검증 스크립트가 위 표를 자동 확인한다(§12.3).

---

## 4. 타이포그래피

### 4.1 서체

| 역할 | 서체 | 근거 |
|---|---|---|
| 기본 | `Pretendard Variable` → `Pretendard` → `-apple-system` → `system-ui` → `sans-serif` | 한글 가독성·숫자 폭·굵기 축이 안정적이며 무료 배포 가능 |
| 전시 제목 | 기본과 동일 (별도 세리프를 쓰지 않음) | 서체를 두 벌 쓰면 액자가 눈에 띈다(DS-1) |
| 숫자(통계·날짜) | `Pretendard` + `font-variant-numeric: tabular-nums` | 관리자 목록에서 숫자가 흔들리지 않아야 한다 |

**서브셋** — 한글 2,780자 + 라틴 + 숫자 + 문장부호로 서브셋한 `woff2`를 자체 호스팅한다. 가변 폰트 1개 파일(≈ 120KB)만 로드하고, `font-display: swap`, `preload`를 적용한다. 외부 CDN을 쓰지 않는다(폐쇄형 서비스의 외부 요청 최소화, PRD §8.4).

### 4.2 타입 스케일

기준값은 `normal` 모드이며, `large` 모드에서 의미 토큰 값만 교체된다.

| 토큰 | 용도 | normal (크기/행간/자간/굵기) | large |
|---|---|---|---|
| `display` | A 화면 로고 | 28 / 1.30 / -0.02em / 600 | 32 / 1.30 |
| `title-lg` | 전시 제목(C, C-1) | 24 / 1.35 / -0.015em / 600 | 28 / 1.35 |
| `title-md` | 그림 제목(C-2), 화면 제목 | 20 / 1.40 / -0.01em / 600 | 23 / 1.40 |
| `title-sm` | 섹션 제목, 관리자 카드 제목 | 18 / 1.45 / 0 / 600 | 20 / 1.45 |
| `body-lg` | 전시 테마 본문, 그림 설명 | **17** / 1.75 / 0 / 400 | **20** / 1.80 |
| `body-md` | 일반 본문, 버튼 라벨, 입력 값 | 16 / 1.60 / 0 / 400 | 18 / 1.65 |
| `body-sm` | 보조 설명, 목록 부가 정보 | 15 / 1.55 / 0 / 400 | 17 / 1.60 |
| `caption` | 날짜, 작가명, 메타 | 14 / 1.45 / 0.01em / 400 | 16 / 1.50 |
| `label` | 폼 라벨, 상태 칩 | 14 / 1.30 / 0.02em / 500 | 16 / 1.30 |
| `mono-num` | 통계 숫자 | 20 / 1.20 / 0 / 600 · tabular | 22 / 1.20 |

**12px·13px 토큰은 존재하지 않는다**(DS-3). 더 작게 필요해 보이는 자리는 정보 우선순위를 다시 판단해야 하는 자리다.

### 4.3 본문 조판 규칙

| 항목 | 규칙 |
|---|---|
| 최대 행 길이 | 한글 기준 **32em**(약 32자). 초과 시 컨테이너 폭을 줄인다 |
| 줄바꿈 | `word-break: keep-all`, `overflow-wrap: break-word` — 한글 단어 중간 절단 방지 |
| 문단 보존 | 전시 테마·그림 설명은 원문 줄바꿈을 유지한다(`white-space: pre-line`) |
| 문단 간격 | `body-lg` 기준 1em |
| 균형 잡힌 제목 | 제목류는 `text-wrap: balance` (미지원 브라우저는 무시) |

---

## 5. 간격 · 크기 · 레이아웃

### 5.1 간격 스케일

4px 기반, 8px 배수 우선. Tailwind 기본 스케일을 **축소해서 재정의**한다 — 선택지가 적을수록 일관성이 높다.

| 토큰 | 값 | 주 용도 |
|---|---|---|
| `space-1` | 4px | 아이콘-텍스트 간격 |
| `space-2` | 8px | 인접 요소 |
| `space-3` | 12px | 폼 요소 내부 |
| `space-4` | 16px | 기본 간격, 화면 좌우 여백(모바일) |
| `space-5` | 20px | |
| `space-6` | 24px | 섹션 내부 |
| `space-8` | 32px | 섹션 간 |
| `space-10` | 40px | |
| `space-12` | 48px | 화면 블록 간 |
| `space-16` | 64px | 화면 상하 여백 |

`space-7`, `space-9`, `space-11`은 정의하지 않는다.

### 5.2 컨테이너와 반응형

| 브레이크포인트 | 값 | 대상 |
|---|---|---|
| (기본) | 0–639px | 모바일 세로. **설계 기준 폭 390px** |
| `sm` | 640px | 모바일 가로·소형 태블릿 |
| `md` | 768px | 태블릿 |
| `lg` | 1024px | 데스크톱 (관리자 주 사용 환경) |
| `xl` | 1280px | 대형 데스크톱 |

| 컨테이너 | 최대 폭 | 좌우 패딩 | 적용 |
|---|---|---|---|
| `container-gallery` | 560px | 16px (`sm`↑ 24px) | 관람자 전 화면. **데스크톱에서도 넓히지 않는다** — 모바일 갤러리의 비례를 유지한다 |
| `container-reading` | 480px | 16px | C-1 테마 본문, 그림 설명 |
| `container-studio` | 1120px | 16px (`lg`↑ 32px) | 관리자 화면 |
| `container-form` | 400px | 16px | 로그인·가입 |

### 5.3 그리드

| 그리드 | normal | large | 간격 |
|---|---|---|---|
| C 갤러리 썸네일 | **3열 × 4행** | **2열 × 6행** | 8px (large 12px) |
| B-2 업로드 슬롯 | 3열 × 4행 | 3열 유지 | 12px |
| 관리자 목록 | 1열(모바일) / 표(≥`md`) | — | — |

썸네일 그리드는 정사각(`aspect-ratio: 1`)이며 `object-fit: cover`로 채운다. **열 수 전환은 `data-font-scale` 속성 하나로 일어난다**(§2.2).

### 5.4 모서리 반경 · 그림자 · 경계

| 토큰 | 값 | 용도 |
|---|---|---|
| `radius-none` | 0 | **그림 이미지.** 작품에는 어떤 반경도 적용하지 않는다 |
| `radius-sm` | 4px | 칩, 배지 |
| `radius-md` | 8px | 버튼, 입력 필드, 카드 |
| `radius-lg` | 12px | 시트, 다이얼로그 |
| `radius-full` | 9999px | 스위치, 아바타 |
| `shadow-none` | none | 기본. **관람자 화면은 그림자를 쓰지 않는다** |
| `shadow-sheet` | `0 -4px 24px rgba(26,24,22,.10)` | 바텀시트 |
| `shadow-dialog` | `0 8px 32px rgba(26,24,22,.16)` | 다이얼로그 |
| `border-hairline` | 1px `border-default` | 구분선 |

깊이 표현은 그림자가 아니라 **경계선과 배경 대비**로 한다. 그림자는 화면 위에 떠 있는 오버레이(시트·다이얼로그)에만 허용한다.

### 5.5 z-index 층위

| 토큰 | 값 | 층 |
|---|---|---|
| `z-base` | 0 | 문서 흐름 |
| `z-sticky` | 10 | 상단 고정 헤더 |
| `z-overlay` | 100 | backdrop |
| `z-sheet` | 110 | 바텀시트 |
| `z-dialog` | 120 | 다이얼로그 |
| `z-immersive` | 200 | 전체화면 뷰어 |
| `z-toast` | 300 | 토스트 |

숫자를 직접 쓰지 않는다. 새 층이 필요하면 이 표를 먼저 고친다.

---

## 6. 모션

| 토큰 | 값 | 용도 |
|---|---|---|
| `duration-instant` | 100ms | 눌림 피드백 |
| `duration-fast` | 180ms | 페이드, 색 전환 |
| `duration-base` | 260ms | 시트·다이얼로그 진입 |
| `duration-slow` | 400ms | 전체화면 뷰어 열기 |
| `ease-standard` | `cubic-bezier(.2,0,.2,1)` | 기본 |
| `ease-decelerate` | `cubic-bezier(0,0,.2,1)` | 진입 |
| `ease-accelerate` | `cubic-bezier(.4,0,1,1)` | 이탈 |

**모션 규칙**

1. 애니메이션은 `opacity`와 `transform`만 사용한다. 레이아웃 속성은 애니메이션하지 않는다.
2. 그림이 나타날 때 확대/축소 효과를 주지 않는다 — 작품을 왜곡하는 인상을 준다. **페이드만** 쓴다.
3. `prefers-reduced-motion: reduce`이면 모든 전환을 `duration-instant`로 축약하고 이동 애니메이션을 제거한다. 이는 **전역 CSS 한 곳에서 처리**하며 컴포넌트가 개별 대응하지 않는다.
4. 스와이프 전환은 손가락 이동을 그대로 따라가고(`transform: translateX`), 놓는 순간 `duration-base`로 정착한다.

---

## 7. 아이콘

| 항목 | 규격 |
|---|---|
| 소스 | 자체 SVG 스프라이트 (`/icons.svg`). 아이콘 라이브러리를 의존성으로 추가하지 않는다 |
| 크기 | 20px(기본), 24px(단독 버튼), 28px(전체화면 뷰어) |
| 선 굵기 | 1.5px, 라운드 캡 |
| 색 | `currentColor` 상속 |
| 접근성 | 장식용은 `aria-hidden`, 단독 사용 시 `aria-label` 필수 |
| 목록 | `back`, `close`, `chevron-left/right/up/down`, `plus`, `image`, `check`, `alert`, `info`, `settings`, `bell`, `bell-off`, `trash`, `eye`, `eye-off`, `zoom-in`, `drag`, `search`, `upload`, `spinner`, `more`(⋯), `arrow-up`(연장 표시), `calendar`, `refresh` (총 26종) |

**아이콘만으로 동작을 설명하지 않는다.** 시니어 사용자(P2)를 위해 주요 동작에는 텍스트 라벨을 병기한다.

---

## 8. 컴포넌트 카탈로그

모든 컴포넌트는 `shared/ui/`에 위치하며 도메인 지식을 갖지 않는다(프런트 문서 §4.3). 변형은 `class-variance-authority`로 선언한다.

### 8.1 프리미티브

#### `Button`

| 속성 | 값 |
|---|---|
| `variant` | `primary`(짙은 배경) · `secondary`(경계선) · `ghost`(배경 없음) · `danger`(텍스트만 danger) |
| `size` | `lg`(높이 56px, 화면 폭 채움) · `md`(48px) · `sm`(40px, 히트영역 48px 확장) |
| `state` | `default` · `hover` · `active` · `disabled` · `loading` |
| 기본값 | 관람자 화면의 주요 동작은 항상 `primary` + `lg` + 전체 폭 |

- `loading` 상태에서 라벨을 유지하고 좌측에 스피너를 넣는다. **라벨이 사라지면 시니어 사용자가 무엇을 눌렀는지 잃는다.**
- `disabled`는 `aria-disabled`로 표기하고 포커스를 유지한다(이유를 읽을 수 있어야 한다).
- 최소 히트 영역 48px는 `size=sm`에서 의사요소 확장으로 보장한다.

#### `TextField` / `TextArea`

| 속성 | 값 |
|---|---|
| `size` | `md`(48px) · `lg`(56px, 기본) |
| `state` | `default` · `focus` · `error` · `disabled` |
| 부속 | `label`(항상 필수, placeholder로 대체 금지) · `hint` · `errorMessage` · `counter` |

- 라벨은 필드 위에 배치한다. 플로팅 라벨을 쓰지 않는다 — 축소된 라벨이 12px 이하가 되어 DS-3과 충돌한다.
- `error` 상태는 경계선 색 + 아이콘 + 하단 메시지의 3중 표기(DS-5).
- `counter`는 `현재/최대` 형식이며 초과 시 숫자만 `danger` 색으로 바꾸고 **입력은 막지 않는다**(PRD §6.10).
- 전화번호 입력은 `inputmode="numeric"`, `autocomplete="tel"`, 자동 하이픈 포맷팅. 비밀번호는 `autocomplete="current-password"`/`new-password`.

#### `Switch`

48×28px 트랙, `radius-full`. `role="switch"` + `aria-checked`. 라벨을 좌측에 두고 **라벨 전체가 히트 영역**이다.

#### `Dialog` / `BottomSheet`

| 항목 | 규칙 |
|---|---|
| 용도 | `Dialog`: 확인이 필요한 결정(탈퇴, 숨김) / `BottomSheet`: 선택·입력(알림 시각 선택) |
| 포커스 | 열릴 때 첫 포커스 가능 요소로 이동, 트랩, 닫힐 때 트리거로 복귀 |
| 닫기 | backdrop 클릭 · `Esc` · 명시적 닫기 버튼. 시트는 아래로 스와이프 |
| 스크롤 | 열려 있는 동안 body 스크롤 잠금 |
| 파괴적 동작 | 확인 버튼을 `danger`로, **취소를 좌측·기본 포커스**로 둔다 |

#### `Toast`

화면 하단(모바일)·우상단(데스크톱). 4초 자동 소멸, 오류는 6초. 동시 최대 1개이며 새 토스트가 이전을 대체한다. `role="status"`(정보) / `role="alert"`(오류).

#### `Skeleton`

`bg-subtle` + 1.4초 shimmer. **썸네일 스켈레톤은 LQIP가 있으면 쓰지 않는다** — 블러 이미지가 더 나은 플레이스홀더다.

#### 기타 프리미티브

| 컴포넌트 | 요점 |
|---|---|
| `IconButton` | 48×48px 고정. `aria-label` 필수 |
| `TextLink` | 밑줄 상시 표시(색만으로 구분하지 않음, DS-5). 하단 되돌아가기 링크의 기본형 |
| `Badge` | 정보성 표식. `neutral`/`accent` 2종 |
| `StatusChip` | §8.3 |
| `Divider` | 1px hairline. 여백으로 충분하면 쓰지 않는다 |
| `Spinner` | 20/24/32px. 1.1초 회전 |
| `EmptyState` | 아이콘 + 한 줄 문구 + 선택적 동작 버튼 |
| `ErrorState` | 문구 + 재시도 버튼. **부분 실패에는 화면 전체를 대체하지 않는다** |
| `CharCounter` | `TextField`/`TextArea` 부속 |
| `FieldGroup` | 라벨·필드·힌트·오류의 수직 조합. 폼의 최소 단위 |
| `Banner` | 화면 상단 고정 안내. `info`(지난 전시 보는 중) / `offline`(연결 없음) / `update`(새 버전). **경고색을 쓰지 않는다** — 사용자의 잘못이 아니다 |
| `FilterChip` | 목록 필터 토글(B-3). 선택 시 `accent-050` 배경 + 체크. 히트 영역 48px |
| `Menu` | `⋯` 버튼이 여는 액션 목록(B-3 회원 행). 항목 높이 48px, 파괴적 항목은 `danger` + 최하단 |
| `ProgressRing` | 업로드 진행률(0–100). 24px·40px 2종. 값이 없으면 무한 회전 |
| `TimeSelectSheet` | 시각 선택 바텀시트(C-4 알림 시각). 30분 단위, 범위 제한 가능. 드럼이 아닌 **목록 선택**으로 구현 — 드럼은 시니어에게 조작이 어렵다 |
| `DateField` | 날짜 입력(휴관 공지). 네이티브 `input[type=date]`을 토큰으로 감싼다 |

### 8.2 관람자 복합 컴포넌트

| 컴포넌트 | 구성 | 규칙 |
|---|---|---|
| `DateLine` | `2026. 08. 27. 목` | `caption`, `text-tertiary`. 서버가 준 문자열을 그대로 출력한다 |
| `ExhibitionTitle` | 제목 + 연장 라벨 | 제목은 `title-lg`, 연장 라벨(`8월 30일의 전시`)은 `caption`/`text-tertiary`로 제목 아래 |
| `ArtworkThumb` | 정사각 이미지 + 작가명 + 열람 표식 | 열람 표식은 우상단 4px 점, `neutral-400` 40% 투명도. **아주 옅게**(PRD §6.5) |
| `ArtworkGrid` | `ArtworkThumb` × 12 | 3열/2열 자동 전환. 첫 6개는 즉시 로드, 나머지는 지연 로드 |
| `ArtworkFrame` | 원본 비율 이미지 + 확대 버튼 | 종횡비를 예약해 레이아웃 시프트 0. 우하단에 `크게 보기` 버튼(§5.2 P2 대응) |
| `ImmersiveViewer` | 전체화면 뷰어 | 검은 배경, UI 제거, 핀치 줌·더블탭, 아래로 스와이프하여 닫기 |
| `SwipePager` | 그림 좌우 전환 | 임계값 화면폭 20% 또는 속도 0.4px/ms. 양 끝에서는 고무줄 저항 |
| `PositionIndicator` | `3 / 12` | `caption`, tabular-nums |
| `BackLink` | `갤러리 화면으로` 등 | **모든 화면 하단에 존재**(PRD §5.2). 상단 back 아이콘과 병존 |
| `ArchiveRow` | 날짜 + 제목 + 썸네일 + 감상 표식 | 행 높이 최소 72px |
| `NoticeBanner` | 휴관 공지 + `지난 전시 보기` | 경계선만, 배경색 없음. 경고처럼 보이지 않게 한다 |

### 8.3 관리자 복합 컴포넌트

| 컴포넌트 | 구성 | 규칙 |
|---|---|---|
| `StatusChip` | 발행 상태 | `Y` = success + 체크아이콘 / `N` = warning + 점 / `↑ 08.30` = neutral + 위화살표. **문자·색·아이콘 3중**(DS-5) |
| `DayRow` | 날짜 · `UP` 버튼 · 상태칩 | 3열 고정. 오늘 행은 좌측 2px accent 바로 표시 |
| `SlotButton` | 12칸 업로드 버튼 | **시각 상태 6종** — `empty`(점선+번호) / `uploading`(`ProgressRing`) / `processing`(흐린 썸네일+스피너) / `ready·미완성`(썸네일+주황 점) / `ready·완성`(썸네일+초록 체크) / `failed`(붉은 테두리+`!`). 서버 `image_status` 5종에 **메타데이터 완성 여부**가 곱해져 6종이 된다 |
| `UploadDropzone` | 다중 파일 선택 | 드래그&드롭 + 파일 선택. 진행률 개별 표시 |
| `DraggableSlotGrid` | 순서 변경 | 드래그 핸들 표시, 키보드(방향키+Space) 대체 조작 제공 |
| `PreviewFrame` | 관람자 화면 미리보기 | 390px 폭 프레임 안에 관람자 컴포넌트를 그대로 렌더(프런트 문서 §7.4) |
| `SummaryStat` | 요약 숫자 | `mono-num` + `label`. 2개 나란히 |
| `MemberRow` | 회원 목록 행 | 이름·번호·가입일·알림상태·차단 스위치 |
| `SaveIndicator` | 자동 저장 상태 | `저장 중…` / `저장됨 · 방금` / `저장 실패 · 다시 시도`. 3상태 외에 없다 |

### 8.4 컴포넌트 작성 규약

| 규약 | 내용 |
|---|---|
| 변형 선언 | `cva`로 variant·size·state를 선언하고 `VariantProps`로 타입을 유도한다 |
| 클래스 병합 | `tailwind-merge`로 외부 `className`을 병합한다. 외부 오버라이드는 허용하되 **레이아웃 속성만** 권장 |
| ref 전달 | 모든 프리미티브는 ref를 전달한다 |
| 다형성 | `asChild` 패턴(Radix Slot)으로 링크/버튼 전환을 지원한다 |
| 상태 소유 | 프리미티브는 **제어(controlled)를 기본**으로 하고 비제어를 옵션으로 둔다 |
| 접근성 | 각 컴포넌트의 필수 ARIA는 컴포넌트 내부에서 보장한다. 사용처가 잊을 수 있는 것을 프롭으로 두지 않는다 |
| 스토리 | 각 컴포넌트는 상태 전수를 보여주는 스토리 파일을 갖는다(§12.2) |

---

## 9. 이미지 표현 규격

| 항목 | 규격 |
|---|---|
| 종횡비 예약 | 모든 `img`에 `width`/`height` 또는 `aspect-ratio`를 지정한다. CLS 목표 0 |
| 로딩 | 그리드 상위 6개 `loading="eager"` + `fetchpriority="high"`, 나머지 `loading="lazy"` |
| 디코딩 | `decoding="async"` |
| 플레이스홀더 | LQIP data URL을 `background-image`로 깔고 이미지 로드 완료 시 `duration-fast` 페이드 |
| 실패 | 이미지 영역만 `ErrorState`로 대체하고 **텍스트는 유지**(PRD §6.7) |
| 대체 텍스트 | `{그림 제목} – {작가}` (PRD §8.3) |
| 원본 | 전체화면 뷰어에서 확대 제스처가 시작될 때만 로드. 로드 중에는 display 이미지를 보여준다 |
| 저장 방지 | **하지 않는다.** `user-select`·컨텍스트 메뉴를 막지 않는다(PRD §6.7) |

---

## 10. 상태 표현 규칙

| 상태 | 표현 | 금지 |
|---|---|---|
| 로딩(최초) | 스켈레톤 또는 LQIP | 전체 화면 스피너 |
| 로딩(갱신) | 기존 내용 유지 + 상단 얇은 진행 표시 | 내용 비우기 |
| 비어 있음 | `EmptyState` 한 줄 문구 | 일러스트레이션 남용 |
| 오류(전체) | `ErrorState` + 재시도 | 스택·코드 노출 |
| 오류(부분) | 해당 영역만 대체 | 화면 전체 대체 |
| 오프라인 | 캐시 내용 + 상단 안내 바 | 빈 화면 |
| 성공 | `Toast` 1회 | 모달 확인창 |

---

## 11. Tailwind v3 구성

### 11.1 설정 구조

| 파일 | 역할 |
|---|---|
| `src/styles/tokens.css` | 원시·의미 토큰의 CSS 변수 선언. 스코프별 오버라이드 포함 |
| `src/styles/base.css` | `@tailwind base` + 전역 리셋 + 폰트 페이스 + `prefers-reduced-motion` |
| `src/styles/index.css` | 위 두 개와 `@tailwind components/utilities`를 조립 |
| `tailwind.config.js` | `theme.extend`가 CSS 변수를 참조. `content`는 `src/**/*.{ts,tsx}` |

### 11.2 config 매핑 원칙

| Tailwind 키 | 매핑 |
|---|---|
| `colors` | 의미 토큰만 등록 (`bg-canvas`, `text-primary`, `border-default` …). 원시 팔레트는 등록하지 않는다 |
| `fontSize` | §4.2 스케일을 `[크기, {lineHeight, letterSpacing, fontWeight}]` 형태로 등록. **기본 스케일은 제거** |
| `spacing` | §5.1 값만 유지. Tailwind 기본 스케일 덮어쓰기 |
| `borderRadius`·`boxShadow`·`zIndex`·`screens`·`maxWidth` | §5.4·§5.5·§5.2 표 그대로 |
| `transitionDuration`·`transitionTimingFunction` | §6 그대로 |
| 플러그인 | `@tailwindcss/forms`(base 전략), `@tailwindcss/typography` 미사용(전시 본문은 자체 조판) |

**`theme.extend`가 아니라 `theme`으로 덮어쓰는 항목**은 `fontSize`·`spacing`·`colors`다. 기본 스케일이 남아 있으면 `text-xs`(12px) 같은 금지 값이 쓰인다(DS-3, DS-7).

### 11.3 큰 글씨 모드 구현

`html[data-font-scale="large"]`에서 §4.2의 `large` 값으로 CSS 변수를 교체한다. Tailwind `fontSize` 토큰이 `var(--gk-font-size-body-lg)`를 참조하므로 **클래스는 그대로 두고 값만 바뀐다.** 그리드 열 수는 동일 선택자에서 `--gk-grid-columns`를 3→2로 바꿔 처리한다.

### 11.4 린트 규칙

| 규칙 | 목적 |
|---|---|
| 임의 값 금지 (`text-[..]`, `bg-[#..]`, `p-[..]`) | DS-7 |
| 원시 색 변수 직접 참조 금지 | 2계층 우회 방지 |
| `z-[숫자]` 금지 | §5.5 |
| 인라인 `style` 금지 (예외: 종횡비·LQIP·스와이프 transform) | |
| 클래스 정렬 | `prettier-plugin-tailwindcss` |

---

## 12. 품질 보증

### 12.1 접근성 체크리스트 (모든 컴포넌트 공통)

- [ ] 키보드만으로 조작·탈출 가능
- [ ] 포커스 링이 항상 보임 (`outline: 2px solid var(--gk-border-focus); outline-offset: 2px`)
- [ ] 히트 영역 ≥ 48×48px
- [ ] 색 외 단서 존재
- [ ] 대비 ≥ 4.5:1 (큰 텍스트 3:1)
- [ ] 스크린리더 라벨·역할·상태 제공
- [ ] `prefers-reduced-motion` 대응
- [ ] 큰 글씨 모드에서 잘림·겹침 없음

### 12.2 시각 회귀

Storybook 8 + 각 컴포넌트의 상태 전수 스토리. Chromatic 또는 Playwright 스냅샷으로 PR마다 비교한다. **관람자 화면 4종(A/C/C-1/C-2)은 `normal`·`large` 두 모드 모두 스냅샷 대상**이다.

### 12.3 토큰 검증

빌드 파이프라인에서 (a) §3.3 대비 조합 자동 검증, (b) 미사용 토큰 검출, (c) 하드코딩 색상값 스캔을 수행한다. 실패 시 빌드를 중단한다.

---

## 13. PRD 대비 보완 사항

| # | 근거 | 이 문서의 결정 |
|---|---|---|
| **S-1** | GAP-13 (큰 글씨 모드) | 별도 컴포넌트가 아니라 **토큰 스코프 교체**로 구현. 3열→2열 전환도 동일 메커니즘 |
| **S-2** | 제품 원칙 4 | 관람자 화면 강조색 1종·그림자 0. 상태색은 관리자·오류 전용 |
| **S-3** | PRD §8.3 (본문 17px) | 12·13px 토큰 자체를 제거. 정의되지 않은 값은 쓸 수 없다 |
| **S-4** | PRD §5.2 (시니어 되돌아가기) | `BackLink`를 모든 화면 하단의 필수 컴포넌트로 규정 |
| **S-5** | PRD §6.9 (스캔 속도가 전부) | `StatusChip` 3중 표기 + `DayRow` 고정 3열 |
| **S-6** | PRD §8.1 (LCP 2.5초) | 상위 6개 즉시 로드 + LQIP + 종횡비 예약을 시스템 규격으로 고정 |
| **S-7** | (없음) | 폰트 자체 호스팅·서브셋. 외부 CDN 요청은 폐쇄형 원칙과 충돌 |
| **S-8** | 교차 검토 | `Banner`·`FilterChip`·`Menu`·`ProgressRing`·`TimeSelectSheet`·`DateField` 추가. UX 문서가 요구하지만 카탈로그에 없던 프리미티브 |
| **S-9** | 교차 검토 | `SlotButton`을 시각 상태 6종으로 정정. 서버 상태 5종과 1:1이 아니다 |
| **S-10** | 교차 검토 | `TimeSelectSheet`를 드럼이 아닌 목록 선택으로 규정(P2 조작성) |
