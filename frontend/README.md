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
cp .env.example .env   # 선택. 없어도 기본값으로 동작한다
npm run dev            # http://localhost:5173
```

백엔드 없이 **전 화면이 동작한다**. 로그인은 아래 데모 계정을 쓴다(로그인 화면에도 안내가 있다).

| 역할 | 전화번호 | 비밀번호 |
|---|---|---|
| 관람자 | `010-1234-5671` | `gallery1234` |
| 큐레이터 | `010-0000-0001` | `curator1234` |

큐레이터로 들어가면 A 첫 화면 우상단에 `Curator K` 링크가 생기고, 관리자 화면(B 계열)으로 갈 수 있다.

### 명령

| 명령 | 하는 일 |
|---|---|
| `npm run dev` | 개발 서버 |
| `npm run build` | 타입 검사 + 프로덕션 빌드 |
| `npm run typecheck` | 타입 검사만 |
| `npm run lint` | oxlint |
| `npm run lint:layers` | **레이어 의존 규칙 검사**(`.dependency-cruiser.cjs`) |
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
└── mocks/       ⚠ 데모 전용. 백엔드 연동 시 통째로 지운다
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
| 토큰 밖으로 나가지 않는다 | `tailwind.config.js`가 `colors`·`fontSize`·`spacing`을 **덮어쓴다**. `text-xs`(12px)는 존재하지 않는다 |
| 큰 글씨 모드는 컴포넌트를 바꾸지 않는다 | `html[data-font-scale]` 하나로 타이포와 그리드 열 수(3→2)가 함께 바뀐다 |
| 되돌아갈 길이 항상 보인다 | 모든 화면 하단의 `BackLink`. 대상은 페이지가 명시적으로 지정한다 |
| 제스처에는 항상 대안이 있다 | 스와이프 ↔ 하단 링크·화살표 키, 핀치 ↔ `크게 보기` 버튼·더블탭 |
| 문구는 한 곳에만 있다 | `shared/config/messages.ts`. JSX에 한국어 문자열을 직접 쓰지 않는다 |
| 서버 계약은 한 곳에서만 안다 | `shared/api`가 봉투·오류·페이지네이션을 흡수하고, 바깥은 도메인 타입만 다룬다 |
| 관리자 코드는 관람자 경로로 흘러들지 않는다 | `RequireCurator` 아래 `lazy()` + 빌드 청크 분리(`admin`) |
| 실패해도 화면은 뜬다 | A 첫 화면은 데이터 무의존 렌더, 기록 API 실패는 조용히 포기 |
| 미리보기는 관람자 화면 그 자체다 | `GalleryView`(순수) / `GalleryPage`(컨테이너) 분리. 미리보기는 기록 경로를 타지 않는다 |

---

## 데모(Mock) 계층

현재 모든 데이터는 `src/mocks`의 인메모리 목에서 온다. **제품 코드는 이 폴더를 알지 못한다** —
API 함수 안에서만 참조되며, 그 자리에는 실제 호출이 주석으로 나란히 놓여 있다.

```ts
export async function fetchCurrentExhibition(): Promise<Exhibition> {
  // [API]
  // const raw = await httpClient.get<RawExhibitionDetail>(endpoints.exhibitions.current())
  // return toExhibition(raw)

  // [MOCK]
  const raw = await exhibitionMock.getCurrentExhibition()
  return toExhibition(raw)
}
```

교체 지점 전수는 한 줄로 찾는다.

```bash
grep -rn "\[MOCK\]" src/
```

제거 절차와 규칙은 [`src/mocks/README.md`](src/mocks/README.md)에 있다.

목은 **화면 로직을 대신하지 않는다.** 발행 조건 판정, `edit_mode` 결정, 연장 라벨 생성처럼
서버가 소유해야 할 규칙은 `src/mocks/db.ts`가 서버 흉내를 내어 계산한다. 그래야 실제 API로
바꿀 때 화면 코드가 그대로 남는다.

---

## 알아 둘 것

- **번들 예산** — 설계 문서 §5.4의 청크 예산 중 `vendor-react`만 목표(gzip 60KB)를 넘는다.
  React 19 + React Router 7의 실제 크기이며, 코드로 줄일 수 있는 여지가 없다.
  나머지(셸 7.8KB, `admin` 35.8KB 등)는 모두 예산 안이다.
- **순서 변경(드래그)** — 설계 문서는 `@dnd-kit`을 지정하지만, 현재는 의존성 없이
  네이티브 드래그 + 방향키 대체 조작으로 구현되어 있다. 접근성 요구(UX-7)는 충족한다.
- **PWA·서비스워커** — 서비스워커와 매니페스트는 아직 없다. 푸시 구독 흐름은 화면까지
  완결되어 있고, VAPID 키가 없는 환경에서는 합성 구독으로 대체된다.
- **v1.1 화면** — A-2 비밀번호 재설정과 B-1/B-1-1 관람 현황은 스키마가 확정되어 있어
  화면까지 함께 구현했다. 데모 인증번호는 `000000`이다.
