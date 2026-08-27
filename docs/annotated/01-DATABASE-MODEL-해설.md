# 갤러리 K — 데이터베이스 설계서

| | |
|---|---|
| **문서 버전** | v1.0 |
| **작성일** | 2026-08-27 |
| **상위 문서** | `docs/PRD.md` v1.1 |
| **대상 DBMS** | AWS RDS for PostgreSQL 16 |
| **ORM** | SQLModel 0.0.x (SQLAlchemy 2.x 코어 위) + Alembic |
| **상태** | 확정 (구현 기준선) |

## 📘 초보자를 위한 안내

**이 문서는 무엇인가요?**

서비스가 다루는 모든 정보를 **어떤 표에, 어떤 칸으로 나눠 저장할지** 정해놓은 문서입니다. 엑셀 파일을 만들기 전에 "시트를 몇 개 만들고, 각 시트에 어떤 열을 둘지" 먼저 종이에 그려보는 것과 같습니다.

**왜 이걸 먼저 정하나요?**

한번 정하면 **가장 바꾸기 어려운 것**이기 때문입니다. 화면 색깔은 하루면 바꾸지만, 이미 1년치 정보가 쌓인 표의 구조를 바꾸는 일은 위험하고 오래 걸립니다. 그래서 설계 문서 중 이것을 가장 먼저, 가장 신중하게 씁니다.

**이 문서를 읽는 요령**

- **§4 테이블 상세**가 이 문서의 본론입니다. 나머지는 그 앞뒤를 설명하는 부분입니다.
- 표의 `Null` 칸은 "값이 비어 있어도 되는가"입니다. `N`이면 반드시 채워야 하고, `Y`면 비어 있어도 됩니다.
- 모르는 단어는 [용어 사전](00-용어사전.md)에서 찾아보세요. 원문은 `../01-DATABASE-MODEL.md`이며, 이 파일은 원문에 설명 상자만 끼워 넣은 것입니다.

**이 서비스에서 다루는 정보는 크게 5가지입니다**

1. **회원** — 누가 들어올 수 있는가
2. **전시** — 어느 날 어떤 제목으로 걸렸는가
3. **그림** — 전시마다 12점
4. **기록** — 누가 언제 들어와서 무엇을 봤는가
5. **살림살이** — 알림 발송 내역, 관리자 조작 이력, 설정값

---

## 1. 설계 원칙

> **📘 쉬운 설명**
>
> 아래 6가지는 "이 문서를 쓰면서 판단이 어려울 때마다 무엇을 기준으로 골랐는가"입니다. 설계에서는 정답이 하나가 아니라 **여러 선택지 중 하나를 고르는 일**이 계속 생기는데, 기준이 없으면 사람마다 다르게 고르고 결과가 뒤죽박죽이 됩니다.
>
> 특히 **DP-1(시간 축을 분리한다)** 이 이 서비스의 핵심입니다. "그림이 걸린 날"과 "사람이 보러 온 날"이 다를 수 있다는 것 — 이걸 처음부터 분리해두지 않으면 나중에 통계가 전부 틀어집니다.

| # | 원칙 | 구체적 적용 |
|---|---|---|
| **DP-1** | **시간 축을 분리한다** | PRD §4.3의 발행일/관람일 분리를 스키마에 그대로 반영한다. `exhibition.exhibition_date`(발행일)와 `view_log.viewed_on`(관람일)은 서로 다른 축이며 절대 혼용하지 않는다 |
| **DP-2** | **상태는 저장하고, 파생은 계산한다** | `is_published`는 파생 계산이 아닌 상태 플래그다(PRD 부록 B). 반대로 `is_complete`처럼 같은 행 안에서 순수 결정되는 값은 생성 컬럼으로 둔다 |
| **DP-3** | **무결성은 DB에서 지킨다** | 애플리케이션 검증은 UX용이고, 최종 방어선은 제약조건이다. UNIQUE·CHECK·FK·EXCLUDE를 적극 사용한다 |
| **DP-4** | **관측 가능성을 스키마에 포함한다** | 알림 발송, 관리자 조작, 이미지 파이프라인은 모두 결과 이력을 남긴다. 서버리스 환경에서 로그 이외의 사후 추적 수단이 필요하다 |
| **DP-5** | **개인정보는 최소로 담고 빠르게 지운다** | 수집 3항목(전화번호·비밀번호·이름) 외 어떤 개인 식별 정보도 컬럼으로 두지 않는다. 로그는 180일 자동 파기한다 |
| **DP-6** | **확장 지점을 열되 미리 만들지 않는다** | v1.1·v1.2 기능(SMS 재설정, 카카오 연동, 예약 발행)은 스키마 훅만 §13에 정의하고 MVP 테이블에는 포함하지 않는다 |

---

## 2. 공통 규약

> **📘 쉬운 설명**
>
> 여기서 정하는 건 **이름 짓는 방식과 형식**입니다. 사소해 보이지만 중요합니다.
>
> 회사에서 파일 이름을 어떤 사람은 `보고서_최종.docx`, 다른 사람은 `2026-08-27 보고서 v3.docx`로 저장하면 나중에 아무도 못 찾습니다. 코드도 똑같습니다. 미리 "우리는 이렇게 짓는다"를 정해두면 처음 보는 이름도 뜻을 짐작할 수 있습니다.

### 2.1 명명 규칙

> **📘 쉬운 설명**
>
> `snake_case`는 `단어_사이를_밑줄로` 잇는 방식입니다. `camelCase`(낙타등처럼 중간을 대문자로)와 대비되는 표기법이고, 데이터베이스에서는 관례적으로 밑줄 방식을 씁니다.
>
> 규칙 중 실용적인 것 하나 — **불리언(예/아니오 값)은 `is_`로 시작한다.** `hidden`이라고만 쓰면 "숨긴 상태"인지 "숨긴 사람"인지 헷갈리지만, `is_hidden`이면 예/아니오 값임이 이름만으로 분명해집니다.

| 대상 | 규칙 | 예 |
|---|---|---|
| 테이블 | 단수형 `snake_case`. SQL 예약어 충돌 회피 접두 허용 | `app_user`, `exhibition`, `artwork_view_log` |
| 컬럼 | `snake_case`. 불리언은 `is_`/`has_`, 시각은 `_at`, 날짜는 `_on`/`_date`, 개수는 `_count` | `is_hidden`, `published_at`, `viewed_on` |
| PK | 항상 `id` | |
| FK | `{참조테이블단수}_id` | `exhibition_id` |
| 인덱스 | `ix_{table}_{목적}` | `ix_exhibition_live` |
| 유니크 | `uq_{table}_{컬럼들}` | `uq_view_log_user_day` |
| 체크 | `ck_{table}_{컬럼}` | `ck_artwork_position` |
| 외래키 | `fk_{table}_{컬럼}` | `fk_artwork_exhibition_id` |

### 2.2 타입 규약

> **📘 쉬운 설명**
>
> **타입**은 그 칸에 어떤 종류의 값이 들어가는지입니다. 숫자 칸, 글자 칸, 날짜 칸이 각각 다릅니다.
>
> 여기서 눈여겨볼 결정은 **열거형을 `text + CHECK`로 한 것**입니다. "회원 등급은 `viewer` 아니면 `curator` 둘 중 하나"를 데이터베이스에 알려주는 방법이 두 가지 있는데, 하나(네이티브 ENUM)는 나중에 값을 추가할 때 손이 많이 갑니다. 그래서 유연한 쪽을 골랐습니다. **지금 편한 것보다 나중에 바꾸기 쉬운 것을 고른 사례**입니다.

| 용도 | 타입 | 결정 근거 |
|---|---|---|
| 기본키 | `uuid` (UUID v7, 애플리케이션 생성) | 시간 정렬성이 있어 B-tree 삽입 지역성이 확보되고, 서버리스 다중 실행 환경에서 시퀀스 경합이 없다 |
| 열거형 | `text` + `CHECK IN (...)` | PostgreSQL 네이티브 ENUM은 값 추가·삭제 시 마이그레이션 비용이 크다. Python 측 `str, Enum`과 1:1 매핑하고 §5 카탈로그를 단일 진실 원천으로 둔다 |
| 시각 | `timestamptz` | 항상 UTC로 저장하고 표현 시 KST로 변환한다 |
| 날짜(업무일) | `date` | KST 캘린더 날짜. 타임존 변환 대상이 아니다 |
| 짧은 문자열 | `varchar(n)` — n은 PRD 글자수 제한과 동일 | 길이 제약을 DB에서 강제한다 |
| 긴 텍스트 | `varchar(n)` (무제한 `text` 금지) | 모든 사용자 입력에는 상한이 있다 |
| 금액·비율 | 사용하지 않음 | 비영리·비상업 서비스 |
| 구조화 설정 | `jsonb` | `app_setting.value`, 감사 로그 스냅샷 한정 |

### 2.3 공통 컬럼(믹스인)

> **📘 쉬운 설명**
>
> 거의 모든 표에 공통으로 들어가는 칸들입니다. `created_at`(만들어진 시각)과 `updated_at`(마지막으로 고친 시각)은 문제가 생겼을 때 "언제부터 이랬지?"를 추적하는 유일한 단서라서 예외 없이 넣습니다.
>
> **믹스인**은 "이 세트를 여기에도 넣어줘"라고 재사용하는 방식입니다. 표마다 똑같은 칸을 손으로 복사해 넣으면 하나를 빠뜨리게 되므로, 세트로 묶어둡니다.

| 믹스인 | 컬럼 | 적용 대상 |
|---|---|---|
| `UUIDPKMixin` | `id uuid PK DEFAULT (애플리케이션 생성 UUIDv7)` | 전 테이블 (`app_setting` 제외) |
| `TimestampMixin` | `created_at timestamptz NOT NULL DEFAULT now()`, `updated_at timestamptz NOT NULL DEFAULT now()` | 전 테이블 |
| `VersionMixin` | `version integer NOT NULL DEFAULT 1` | 동시 수정 가능성이 있는 `exhibition`, `artwork` |

- `updated_at`은 DB 트리거가 아니라 SQLAlchemy `onupdate`로 갱신한다. 배치성 UPDATE 경로에서는 서비스가 명시적으로 세팅한다.
- `version`은 SQLAlchemy `version_id_col`로 낙관적 잠금에 사용한다. 충돌 시 `409 CONFLICT_VERSION`(API 문서 §5) 으로 매핑된다.

### 2.4 시간대 규약

> **📘 쉬운 설명**
>
> **이 절은 이 문서에서 가장 사고가 잘 나는 부분입니다.**
>
> 서버는 보통 세계 표준시(UTC)로 돌아가고 한국은 그보다 9시간 빠릅니다. 그래서 한국에서 8월 28일 오전 2시일 때, 서버는 아직 8월 27일입니다.
>
> 만약 "오늘 전시"를 서버 날짜로 계산하면, **매일 새벽 0시~9시 사이에 들어온 사람은 어제 전시를 보게 됩니다.** 이런 버그는 낮에 테스트하면 절대 안 잡히고, 새벽에 쓰는 사용자가 생기고 나서야 발견됩니다.
>
> 그래서 "날짜 계산은 무조건 한국 시간으로, 그것도 정해진 함수 한 곳에서만 한다"를 규칙으로 못박았습니다.

- **DB 세션 타임존은 UTC로 고정**한다. 커넥션 파라미터에 `-c TimeZone=UTC`를 지정한다.
- **업무 날짜(발행일·관람일·공지 기간)는 예외 없이 KST(Asia/Seoul) 캘린더 기준**이다. 애플리케이션이 `today_kst()`로 계산해 파라미터로 넘기며, SQL 안에서 `CURRENT_DATE`를 쓰지 않는다. (Lambda 런타임 TZ가 UTC이므로 `CURRENT_DATE`는 KST 09:00 이전에 하루 어긋난다.)
- 한국은 서머타임을 쓰지 않으므로 KST 오프셋은 항상 +09:00이다. 그럼에도 상수 `+09:00` 하드코딩 대신 `zoneinfo("Asia/Seoul")`를 사용한다.

### 2.5 삭제 정책

> **📘 쉬운 설명**
>
> 정보를 지우는 방식이 세 가지입니다.
>
> - **하드 삭제** — 진짜로 지운다. 복구 불가
> - **숨김 플래그** — 지우지 않고 "안 보임" 표시만 한다 (휴지통 같은 것)
> - **익명화** — 누구인지만 지우고 기록은 남긴다
>
> 탈퇴한 회원의 방문 기록을 예로 들면, 기록을 통째로 지우면 "지난달 방문자 수"가 소급해서 바뀌어버립니다. 그렇다고 이름을 남겨두면 개인정보 약속을 어깁니다. 그래서 **누구인지만 떼어내고 "누군가 왔었다"는 사실만 남기는** 방식을 씁니다.

| 유형 | 정책 | 적용 |
|---|---|---|
| **하드 삭제** | 행을 제거한다 | `app_user`(탈퇴), 보존기간 만료 로그, `push_subscription`(구독 만료) |
| **숨김 플래그** | 행은 남기고 조회에서 제외한다 | `exhibition.is_hidden` |
| **익명화** | 참조를 끊고 통계 대상에서 제외한다 | `view_log`, `artwork_view_log` (탈퇴 시 `user_id`→NULL, `is_anonymized`→true) |

소프트 삭제(`deleted_at`) 패턴은 **채택하지 않는다.** 회원 수 100명 규모에서 모든 질의에 `WHERE deleted_at IS NULL`을 강제하는 비용이 이득보다 크고, 개인정보 즉시 파기 원칙(PRD §7.3)과도 충돌한다.

---

## 3. 개체 관계도

> **📘 쉬운 설명**
>
> 아래 그림은 **표와 표 사이의 연결 관계**를 보여줍니다. 선 끝의 기호가 개수를 뜻합니다.
>
> - `||` = 정확히 1개
> - `o{` = 0개 이상 여러 개
> - `|{` = 1개 이상 여러 개
>
> 예를 들어 `EXHIBITION ||--|{ ARTWORK`는 "전시 하나에 그림이 여러 개 딸려 있다"는 뜻입니다.
>
> 그 아래 표의 **삭제 동작**은 "부모를 지우면 자식은 어떻게 되는가"입니다. `CASCADE`(함께 지움), `SET NULL`(연결만 끊음) 두 가지가 쓰였는데, **회원을 지울 때 방문 기록까지 통째로 지우지 않는 이유**가 §2.5에서 설명한 그것입니다.

```mermaid
erDiagram
    APP_USER ||--o{ VIEW_LOG : "입장한다"
    APP_USER ||--o{ ARTWORK_VIEW_LOG : "감상한다"
    APP_USER ||--o{ PUSH_SUBSCRIPTION : "구독한다"
    APP_USER ||--o{ NOTIFICATION_LOG : "수신한다"
    APP_USER ||--o{ AUDIT_LOG : "조작한다"
    APP_USER ||--o{ EXHIBITION : "작성한다"
    APP_USER ||--o{ NOTICE : "작성한다"

    EXHIBITION ||--|{ ARTWORK : "12점을 건다"
    EXHIBITION ||--o{ VIEW_LOG : "그날 걸려 있었다"
    EXHIBITION ||--o{ ARTWORK_VIEW_LOG : "집계 기준"
    EXHIBITION ||--o{ NOTIFICATION_LOG : "알림 대상"
    ARTWORK ||--o{ ARTWORK_VIEW_LOG : "열람된다"

    APP_SETTING {
        varchar key PK
        jsonb value
    }
    AUTH_THROTTLE {
        varchar key UK
        int fail_count
        timestamptz locked_until
    }
    NOTICE {
        date starts_on
        date ends_on
        varchar body
    }
```

**관계 요약**

| 관계 | 카디널리티 | 삭제 동작 | 근거 |
|---|---|---|---|
| `exhibition` → `artwork` | 1 : 0..12 | `CASCADE` | 전시를 지우면 그림도 의미가 없다. 단 발행된 전시는 삭제하지 않는다(§8.3) |
| `app_user` → `view_log` | 1 : N | `SET NULL` + 익명화 | 탈퇴해도 집계 이력의 형태는 남기되 개인 식별은 끊는다 |
| `app_user` → `push_subscription` | 1 : N | `CASCADE` | 개인정보성 자원이므로 즉시 파기 |
| `exhibition` → `view_log` | 1 : N | `SET NULL` | 전시 삭제는 원칙상 발생하지 않으나 방어적으로 둔다 |
| `artwork` → `artwork_view_log` | 1 : N | `CASCADE` | 그림 교체 시 그 그림의 열람 기록은 의미를 잃는다 |

---

## 4. 테이블 상세

> **📘 쉬운 설명 — 여기가 본론입니다**
>
> 이제부터 표를 하나씩 정의합니다. 각 표마다 **어떤 칸이 있고, 그 칸에 어떤 규칙이 걸려 있는지**를 적습니다.
>
> 칸 설명 표의 머리글은 이렇게 읽으세요.
>
> | 머리글 | 뜻 |
> |---|---|
> | 컬럼 | 칸 이름 |
> | 타입 | 들어갈 값의 종류 (`uuid`=고유번호, `varchar(20)`=최대 20글자, `bool`=예/아니오, `date`=날짜) |
> | Null | 비어 있어도 되는가 (`N`=반드시 채움) |
> | 기본값 | 아무것도 안 넣으면 자동으로 들어가는 값 |
> | 제약·인덱스 | 이 칸에 걸린 규칙과 빨리 찾기 장치 |

### 4.1 `app_user` — 회원

> **📘 쉬운 설명**
>
> 회원 명부입니다. **관람자와 큐레이터를 한 표에 함께 두고 `role`(역할) 칸으로 구분**합니다. 표를 두 개로 나누지 않은 이유는, 큐레이터도 결국 로그인하고 전시를 보는 사람이라 겹치는 정보가 대부분이기 때문입니다.
>
> 눈여겨볼 칸 몇 개:
>
> - `password_hash` — 비밀번호를 **되돌릴 수 없게 뭉갠 값**만 저장합니다. 그래서 관리자도 회원의 비밀번호를 알 수 없고, 잊어버리면 새로 정하는 수밖에 없습니다. 이게 정상입니다.
> - `token_version` — 숫자 하나입니다. 이 숫자를 1 올리면 그 회원이 로그인해둔 모든 기기가 한꺼번에 로그아웃됩니다. 비밀번호를 바꿨을 때 쓰는 장치입니다.
> - `must_change_password` — 큐레이터가 대신 계정을 만들어주고 초기 비밀번호를 전화로 알려준 경우, 다음 로그인에서 새 비밀번호를 정하게 만드는 표시입니다.
> - `notify_enabled` / `notify_at` — 알림을 끄더라도 **선택했던 시각은 지우지 않습니다.** 다시 켰을 때 "몇 시로 하시겠어요?"를 또 묻지 않기 위해서입니다.

PRD §7.2 User. 관람자와 큐레이터를 하나의 테이블로 관리하고 `role`로 구분한다. 큐레이터는 시드로 1개만 생성되며 화면에서 생성 불가하다(PRD 부록 B).

| 컬럼 | 타입 | Null | 기본값 | 제약·인덱스 | 설명 |
|---|---|:---:|---|---|---|
| `id` | uuid | N | UUIDv7 | PK | |
| `phone` | varchar(11) | N | | `uq_app_user_phone` | **로그인 ID.** 하이픈 없는 숫자만(`01012345678`). 정규화는 애플리케이션 책임 |
| `password_hash` | varchar(100) | N | | | bcrypt(cost 12) 해시. 평문·복호 가능 형식 저장 금지 |
| `name` | varchar(20) | N | | | 표시 이름 |
| `role` | text | N | `'viewer'` | `ck_app_user_role` | `viewer` \| `curator` |
| `notify_enabled` | bool | N | `false` | | 아침 알림 수신 여부 |
| `notify_at` | time | N | `'07:30'` | | 알림 희망 시각(KST). **끄더라도 값은 보존**한다 |
| `font_scale` | text | N | `'normal'` | `ck_app_user_font_scale` | `normal` \| `large` (v1.1 UI, 컬럼은 MVP부터) |
| `is_blocked` | bool | N | `false` | | 차단 회원. 로그인 시점에만 작동(PRD §6.4) |
| `blocked_at` | timestamptz | Y | | | |
| `blocked_reason` | varchar(200) | Y | | | 큐레이터 메모. 회원에게 노출하지 않는다 |
| `created_via` | text | N | `'self'` | `ck_app_user_created_via` | `self` \| `curator`(대행 가입, PRD §6.14) |
| `must_change_password` | bool | N | `false` | | 대행 가입·비밀번호 초기화 시 true. 다음 로그인에서 변경 유도 |
| `token_version` | integer | N | `1` | | JWT 무효화 카운터. 비밀번호 변경·초기화 시 +1 |
| `last_login_at` | timestamptz | Y | | | |
| `created_at` / `updated_at` | timestamptz | N | `now()` | | |

**인덱스**

| 이름 | 정의 | 용도 |
|---|---|---|
| `uq_app_user_phone` | `UNIQUE (phone)` | 로그인·가입 중복 검사 |
| `ix_app_user_notify` | `(notify_at) WHERE notify_enabled AND NOT is_blocked` | 아침 알림 대상 조회(§7 Q5) |
| `ix_app_user_created_at` | `(created_at DESC)` | B-3 회원 목록 기본 정렬 |
| `ix_app_user_name_trgm` | `gin (name gin_trgm_ops)` | B-1 사용자 검색(부분 일치). `pg_trgm` 확장 필요 |

**제약**

- `ck_app_user_role`: `role IN ('viewer','curator')`
- `ck_app_user_font_scale`: `font_scale IN ('normal','large')`
- `ck_app_user_created_via`: `created_via IN ('self','curator')`
- `ck_app_user_phone_digits`: `phone ~ '^01[0-9]{8,9}$'`

**규칙**

- `role='curator'` 행은 **최대 1개**를 전제로 운영한다. DB 제약(`UNIQUE`+부분 인덱스)으로 강제한다: `uq_app_user_single_curator UNIQUE (role) WHERE role = 'curator'`.
- 차단(`is_blocked`)은 기존 세션을 끊지 않는다(PRD §6.4). 즉시 차단이 필요하면 `token_version`을 함께 증가시키는 별도 조작(§13 확장 훅)이 필요하며 MVP에서는 제공하지 않는다.

### 4.2 `auth_throttle` — 인증 시도 제한

> **📘 쉬운 설명**
>
> "비밀번호를 5번 틀리면 10분 잠금"을 기록해두는 표입니다.
>
> **왜 이걸 표로 만들어야 하나요?** 보통 프로그램은 이런 걸 메모리(잠깐 기억하는 공간)에 담아둡니다. 그런데 이 서비스는 요청이 올 때마다 서버가 새로 깨어나는 방식(서버리스)이라, **메모리에 적어두면 다음 요청 때 사라져 있습니다.** 그래서 데이터베이스에 적어둡니다.

PRD §6.2 "5회 연속 실패 시 10분 차단"을 서버리스 환경에서 구현하기 위한 테이블. Lambda는 인스턴스 메모리를 신뢰할 수 없으므로 상태를 DB에 둔다.

| 컬럼 | 타입 | Null | 기본값 | 제약·인덱스 | 설명 |
|---|---|:---:|---|---|---|
| `id` | uuid | N | UUIDv7 | PK | |
| `throttle_key` | varchar(120) | N | | `uq_auth_throttle_key` | `{scope}:{식별자}` 형식. 예 `login:01012345678` |
| `scope` | text | N | | `ck_auth_throttle_scope` | `login` \| `signup` \| `password_reset` \| `media_session` |
| `fail_count` | smallint | N | `0` | | 연속 실패 횟수 |
| `first_failed_at` | timestamptz | Y | | | 윈도 시작점 |
| `last_failed_at` | timestamptz | Y | | | |
| `locked_until` | timestamptz | Y | | | 이 시각까지 차단 |
| `created_at` / `updated_at` | timestamptz | N | `now()` | | |

**인덱스** — `uq_auth_throttle_key UNIQUE (throttle_key)`, `ix_auth_throttle_locked (locked_until) WHERE locked_until IS NOT NULL`(정리 배치용).

**규칙** — 성공 인증 시 해당 키 행을 삭제한다. 실패 시 `INSERT ... ON CONFLICT (throttle_key) DO UPDATE`로 원자적 증가시킨다. `fail_count >= 5`이면 `locked_until = now() + 10분`, `fail_count`는 0으로 리셋한다. 윈도(첫 실패로부터 10분)를 벗어난 시도는 카운트를 1로 재시작한다.

### 4.3 `push_subscription` — 웹 푸시 구독

> **📘 쉬운 설명**
>
> 알림을 보내려면 "이 사람의 이 기기로 보내주세요"라는 주소가 필요합니다. 그 주소를 보관하는 표입니다.
>
> 한 사람이 휴대폰과 PC 두 곳에서 알림을 받을 수 있으므로 **회원 1명 : 구독 여러 개** 관계입니다.
>
> `endpoint_hash`가 따로 있는 이유 — 원래 주소가 너무 길어서 "겹치는지 확인하는 장치(인덱스)"에 그대로 넣을 수 없기 때문에, 길이를 고정한 요약값을 만들어 그걸로 비교합니다.

PRD §6.12. 한 회원이 폰·PC 등 여러 단말에서 구독할 수 있으므로 1:N으로 분리한다.

| 컬럼 | 타입 | Null | 기본값 | 제약·인덱스 | 설명 |
|---|---|:---:|---|---|---|
| `id` | uuid | N | UUIDv7 | PK | |
| `user_id` | uuid | N | | FK→`app_user` `CASCADE` | |
| `endpoint` | varchar(1000) | N | | | 푸시 서비스 엔드포인트 URL |
| `endpoint_hash` | char(64) | N | | `uq_push_subscription_endpoint` | `sha256(endpoint)`. 엔드포인트가 B-tree 인덱스 상한을 넘길 수 있어 해시로 유니크를 건다 |
| `p256dh` | varchar(200) | N | | | 구독 공개키 |
| `auth` | varchar(100) | N | | | 인증 시크릿 |
| `platform` | text | N | `'unknown'` | `ck_push_subscription_platform` | `ios` \| `android` \| `desktop` \| `unknown`. B-3 알림 상태 표시와 iOS 안내에 쓴다 |
| `user_agent` | varchar(300) | Y | | | 진단용 |
| `is_active` | bool | N | `true` | | |
| `failure_count` | smallint | N | `0` | | 연속 실패. 404/410 응답 시 즉시 비활성 |
| `last_success_at` / `last_failure_at` | timestamptz | Y | | | |
| `created_at` / `updated_at` | timestamptz | N | `now()` | | |

**인덱스** — `uq_push_subscription_endpoint UNIQUE (endpoint_hash)`, `ix_push_subscription_user (user_id) WHERE is_active`.

**규칙** — 동일 `endpoint_hash`가 다른 회원으로 재등록되면 `user_id`를 갱신한다(단말 공유·재로그인 시나리오). 푸시 응답이 404/410이면 `is_active=false`로 내리고, 500류 실패는 `failure_count`를 올려 3회 연속이면 비활성화한다.

### 4.4 `exhibition` — 전시(하루 단위)

> **📘 쉬운 설명 — 이 서비스의 심장**
>
> 하루에 하나씩 걸리는 전시입니다. 여기서 가장 중요한 결정이 두 가지 있습니다.
>
> **① 작성 중인 전시와 공개된 전시가 같은 행이다.**
> 초안용 표를 따로 만들지 않았습니다. 큐레이터가 글을 쓰다 만 상태도, 완성해서 걸린 상태도 같은 줄에 있고 `is_published`(발행됨) 칸의 예/아니오만 다릅니다. 옮겨 담는 과정이 없으니 정보가 새어나갈 틈이 없습니다.
>
> **② `is_published`는 한번 켜지면 절대 꺼지지 않는다.**
> 이게 왜 중요하냐면 — 큐레이터가 이미 걸린 전시에서 그림 한 점을 바꾸려고 잠깐 지우는 순간, 조건이 깨져서 **관람자 화면에서 오늘의 전시가 통째로 사라지는** 일이 생길 수 있습니다. 그래서 "한번 걸린 전시는 어떤 수정을 해도 내려가지 않는다"를 규칙으로 못박았습니다. 내리는 방법은 `is_hidden`(숨김) 하나뿐입니다.
>
> `artwork_count`와 `complete_artwork_count`는 **그림 개수를 미리 세어서 적어둔 칸**입니다. 매번 세지 않고 적어둔 숫자를 읽으면 관리자 화면이 훨씬 빨라집니다.

PRD §7.2 Exhibition. **드래프트와 발행본이 같은 행**이다. 별도 draft 테이블을 두지 않는 이유는 B-2 화면이 편집 중 상태를 그대로 미리보기해야 하고(§6.10), 발행이 별도 액션이 아니라 조건 충족 시 자동 전환이기 때문이다.

| 컬럼 | 타입 | Null | 기본값 | 제약·인덱스 | 설명 |
|---|---|:---:|---|---|---|
| `id` | uuid | N | UUIDv7 | PK | |
| `exhibition_date` | date | N | | `uq_exhibition_date` | **발행일(KST).** 하루에 하나(제품 원칙 1) |
| `title` | varchar(20) | Y | | | 전시 제목. 드래프트 단계에서는 NULL 허용 |
| `theme` | varchar(500) | Y | | | 전시 테마 본문. 줄바꿈 보존 |
| `is_published` | bool | N | `false` | | **단방향 상태 플래그.** true로 전환된 뒤 어떤 수정으로도 false로 돌아가지 않는다(PRD 부록 B) |
| `published_at` | timestamptz | Y | | | 발행 조건이 처음 충족된 시각 |
| `is_hidden` | bool | N | `false` | | 관람자에게서 감추는 유일한 수단(PRD §6.9) |
| `hidden_at` | timestamptz | Y | | | |
| `hidden_reason` | varchar(200) | Y | | | 큐레이터 메모 |
| `artwork_count` | smallint | N | `0` | `ck_exhibition_artwork_count` | 연결된 `artwork` 행 수(0–12). 비정규화 카운터 |
| `complete_artwork_count` | smallint | N | `0` | `ck_exhibition_complete_count` | `artwork.is_complete = true`인 행 수(0–12) |
| `created_by` | uuid | Y | | FK→`app_user` `SET NULL` | |
| `draft_updated_at` | timestamptz | Y | | | 마지막 자동 임시저장 시각. B-2 화면의 "저장됨" 표시 근거 |
| `version` | integer | N | `1` | | 낙관적 잠금 |
| `created_at` / `updated_at` | timestamptz | N | `now()` | | |

**인덱스**

| 이름 | 정의 | 용도 |
|---|---|---|
| `uq_exhibition_date` | `UNIQUE (exhibition_date)` | 하루 1전시 강제, 날짜 단건 조회 |
| `ix_exhibition_live` | `(exhibition_date DESC) WHERE is_published AND NOT is_hidden` | **현재 전시 질의(Q1)와 아카이브(Q3)의 전용 인덱스.** 모든 관람자의 모든 접속이 이 인덱스를 탄다 |
| `ix_exhibition_published_at` | `(published_at DESC) WHERE is_published` | 백필 허용으로 정책이 바뀔 경우의 대체 정렬(PRD §4.3 주석). 예비 |

**제약**

- `ck_exhibition_artwork_count`: `artwork_count BETWEEN 0 AND 12`
- `ck_exhibition_complete_count`: `complete_artwork_count BETWEEN 0 AND artwork_count`
- `ck_exhibition_published_at`: `(is_published = false AND published_at IS NULL) OR (is_published = true AND published_at IS NOT NULL)`
- `ck_exhibition_hidden_at`: `(is_hidden = false) OR (is_hidden = true AND hidden_at IS NOT NULL)`

**발행 조건** — `title IS NOT NULL AND btrim(title) <> '' AND theme IS NOT NULL AND btrim(theme) <> '' AND complete_artwork_count = 12`. 이 조건이 처음 충족되는 순간 서비스가 `is_published=true`, `published_at=now()`를 기록한다. 조건은 서비스 계층에서만 판정하며 DB 트리거를 쓰지 않는다 — 발행은 알림 발송(§4.10)을 유발하는 도메인 이벤트이므로 트랜잭션 스크립트로 관리되어야 한다.

**비정규화 카운터 관리** — `artwork_count`·`complete_artwork_count`는 그림 생성·삭제·수정과 **같은 트랜잭션 안에서** 재계산 UPDATE로 갱신한다(증감이 아닌 `SELECT count(*)` 기반 재설정). 12행 이하의 소규모 집합이므로 비용이 무시할 만하고, 증감 방식이 갖는 드리프트 위험이 없다. 야간 정합성 배치(§11.3)가 불일치를 검출한다.

### 4.5 `artwork` — 그림

> **📘 쉬운 설명**
>
> 그림 한 점의 정보입니다. `position`(1~12)이 전시 안에서의 순서입니다.
>
> **이미지가 곧바로 준비되지 않는다는 점**이 이 표를 복잡하게 만듭니다. 큐레이터가 사진을 올리면 서버가 그것을 세 가지 크기로 다시 만드는 데 몇 초가 걸립니다. 그동안의 상태를 `image_status` 칸이 표현합니다 — `업로드 중 → 처리 중 → 준비됨` 또는 `실패`.
>
> `is_complete`는 **자동으로 계산되는 칸**입니다. 제목·작가·연도·설명이 다 있고 이미지도 준비됐으면 자동으로 "완성"이 됩니다. 사람이 손으로 켜는 값이 아닙니다. 이렇게 해두면 "완성이란 무엇인가"의 판단 기준이 코드 여러 곳에 흩어지지 않습니다.
>
> `image_lqip`는 **아주 작고 흐릿한 미리보기 이미지**입니다. 진짜 이미지가 도착하기 전에 이걸 뿌옇게 깔아두면 화면이 텅 빈 채로 기다리지 않아도 됩니다.

PRD §7.2 Artwork. 이미지 업로드가 비동기 파이프라인(백엔드 문서 §8)이므로 이미지 상태 기계를 컬럼으로 갖는다.

| 컬럼 | 타입 | Null | 기본값 | 제약·인덱스 | 설명 |
|---|---|:---:|---|---|---|
| `id` | uuid | N | UUIDv7 | PK | |
| `exhibition_id` | uuid | N | | FK→`exhibition` `CASCADE` | |
| `position` | smallint | N | | `ck_artwork_position`, `uq_artwork_slot` | 전시 내 순서 1–12 |
| `title` | varchar(20) | Y | | | |
| `artist` | varchar(40) | Y | | | |
| `year_text` | varchar(20) | Y | | | `1665년경` 등 자유 텍스트 |
| `description` | varchar(300) | Y | | | 40자 이상 권장(경고만), 300자 초과 저장 차단 |
| `collection` | varchar(60) | Y | | | 소장처 |
| `source_url` | varchar(500) | Y | | `ck_artwork_source_url` | `https://`로 시작하는 URL만 |
| `image_status` | text | N | `'empty'` | `ck_artwork_image_status` | `empty`\|`uploading`\|`processing`\|`ready`\|`failed` |
| `image_original_key` | varchar(300) | Y | | | S3 오브젝트 키(원본) |
| `image_display_key` | varchar(300) | Y | | | 긴 변 1600px WebP |
| `image_thumb_key` | varchar(300) | Y | | | 400×400 정사각 WebP |
| `image_lqip` | varchar(2048) | Y | | | 16px 폭 WebP의 data URL. 블러 플레이스홀더용(PRD §6.5) |
| `image_width` / `image_height` | integer | Y | | | 원본 픽셀 크기. 레이아웃 시프트 방지용 |
| `image_bytes` | integer | Y | | | 원본 바이트 수 |
| `image_mime` | varchar(40) | Y | | | |
| `image_error_code` | varchar(40) | Y | | | 처리 실패 사유 코드 |
| `image_uploaded_at` / `image_ready_at` | timestamptz | Y | | | |
| `is_complete` | bool | N | 생성 컬럼 | | 아래 정의. `STORED GENERATED` |
| `version` | integer | N | `1` | | 낙관적 잠금 |
| `created_at` / `updated_at` | timestamptz | N | `now()` | | |

**생성 컬럼 정의**

```
is_complete = (title IS NOT NULL AND btrim(title) <> ''
            AND artist IS NOT NULL AND btrim(artist) <> ''
            AND year_text IS NOT NULL AND btrim(year_text) <> ''
            AND description IS NOT NULL AND btrim(description) <> ''
            AND image_status = 'ready')
```

한 행 안에서만 결정되므로 `GENERATED ALWAYS AS (...) STORED`로 둔다(DP-2). 완성 판정 로직이 코드 여러 곳에 흩어지는 것을 원천 차단한다.

**인덱스**

| 이름 | 정의 | 용도 |
|---|---|---|
| `uq_artwork_slot` | `UNIQUE (exhibition_id, position)` | 슬롯 중복 방지 |
| `ix_artwork_exhibition` | `(exhibition_id, position)` | 전시 상세 조회(12행 정렬) |
| `ix_artwork_pending_image` | `(image_status, image_uploaded_at) WHERE image_status IN ('uploading','processing')` | 처리 지연 감시 배치 |

**제약**

- `ck_artwork_position`: `position BETWEEN 1 AND 12`
- `ck_artwork_image_status`: `image_status IN ('empty','uploading','processing','ready','failed')`
- `ck_artwork_image_keys`: `image_status <> 'ready' OR (image_display_key IS NOT NULL AND image_thumb_key IS NOT NULL)`
- `ck_artwork_source_url`: `source_url IS NULL OR source_url ~ '^https://'`

**순서 변경** — 드래그 재정렬은 `position`을 재할당한다. `UNIQUE (exhibition_id, position)`이 걸려 있으므로 단일 트랜잭션 안에서 **`DEFERRABLE INITIALLY IMMEDIATE`로 선언하고 `SET CONSTRAINTS ... DEFERRED` 후 일괄 UPDATE**한다. 임시 오프셋(+100) 트릭을 쓰지 않는다.

### 4.6 `view_log` — 갤러리 입장 기록

> **📘 쉬운 설명**
>
> "누가 며칠에 갤러리에 들어왔는가"를 하루 한 줄씩만 남기는 표입니다.
>
> **핵심은 `(회원, 관람일)` 조합이 겹칠 수 없다는 규칙 하나입니다.** 같은 사람이 하루에 열 번 들어와도 줄은 하나입니다. 이 서비스가 알고 싶은 건 "몇 번 열었나"가 아니라 **"며칠이나 왔나"**이기 때문입니다.
>
> 아래쪽 "의도적으로 두지 않는 컬럼" 부분도 눈여겨보세요. 넣을 수 있었지만 **일부러 넣지 않기로 한 것들**입니다. 개인정보는 "필요할지도 모르니 일단 모아두자"가 가장 위험한 태도입니다.

PRD §7.2 ViewLog + GAP-11. **관람일 기준 하루 1행**이 이 테이블의 전부다.

| 컬럼 | 타입 | Null | 기본값 | 제약·인덱스 | 설명 |
|---|---|:---:|---|---|---|
| `id` | uuid | N | UUIDv7 | PK | |
| `user_id` | uuid | Y | | FK→`app_user` `SET NULL` | 탈퇴 시 NULL |
| `viewed_on` | date | N | | `uq_view_log_user_day` | **관람일(KST).** 지표의 기준 축 |
| `exhibition_id` | uuid | Y | | FK→`exhibition` `SET NULL` | 그날 실제로 열린 전시. 연장 중이면 과거 전시를 가리킨다 |
| `first_entered_at` | timestamptz | N | `now()` | | |
| `last_entered_at` | timestamptz | N | `now()` | | |
| `entry_count` | smallint | N | `1` | | 진단용. **지표 계산에는 쓰지 않는다** |
| `is_anonymized` | bool | N | `false` | | 탈퇴 회원의 잔여 로그 |
| `created_at` / `updated_at` | timestamptz | N | `now()` | | |

**인덱스** — `uq_view_log_user_day UNIQUE (user_id, viewed_on)`, `ix_view_log_day (viewed_on DESC)`, `ix_view_log_exhibition (exhibition_id)`, `ix_view_log_user_recent (user_id, viewed_on DESC)`.

**기록 규칙**

- C 갤러리 화면 진입 시 `INSERT ... ON CONFLICT (user_id, viewed_on) DO UPDATE SET entry_count = view_log.entry_count + 1, last_entered_at = EXCLUDED.last_entered_at`.
- 충돌 시 `exhibition_id`는 **갱신하지 않는다.** 그날 처음 연 전시를 그날의 대표값으로 삼는다. 하루 안에 오늘치와 아카이브를 모두 본 경우 첫 진입 전시가 남는다.
- 아카이브(C-3) 진입도 동일하게 그날의 입장으로 센다(PRD §6.5). 구분 컬럼을 두지 않는 것은 의도된 결정이다(부록 B).
- `user_id IS NULL`인 행은 유니크 제약에서 자동 제외된다(PostgreSQL NULL 비교 규칙). 익명화 후 중복이 생길 수 있으나 통계에서 배제되므로 무해하다.

**의도적으로 두지 않는 컬럼** — `source`(오늘/아카이브 구분), `session_id`, `ip`, `user_agent`. PRD 부록 B가 명시적으로 구분하지 않기로 했고, 개인정보 최소화 원칙(DP-5)에 따른다.

### 4.7 `artwork_view_log` — 그림 열람 기록

> **📘 쉬운 설명**
>
> "이 사람이 이 그림을 열어봤다"를 남기는 표입니다. 여기서도 **(회원, 그림) 조합당 한 줄**입니다. 같은 그림을 어제도 오늘도 봤다고 두 줄로 세지 않습니다.
>
> 이 기록의 실제 쓰임은 두 가지입니다.
> 1. 갤러리 화면에서 **이미 본 그림에 옅은 점을 찍는 것**
> 2. 관리자 화면에서 **"이분은 12점 중 8점을 보셨습니다"**를 보여주는 것

PRD §7.2 ArtworkViewLog. "같은 그림을 이틀에 걸쳐 보면 중복 제거해서 센다" → **(회원, 그림) 조합당 1행**이며 첫 열람일을 함께 보관한다.

| 컬럼 | 타입 | Null | 기본값 | 제약·인덱스 | 설명 |
|---|---|:---:|---|---|---|
| `id` | uuid | N | UUIDv7 | PK | |
| `user_id` | uuid | Y | | FK→`app_user` `SET NULL` | |
| `artwork_id` | uuid | N | | FK→`artwork` `CASCADE`, `uq_artwork_view_log_user_artwork` | |
| `exhibition_id` | uuid | N | | FK→`exhibition` `CASCADE` | 비정규화. 조인 없이 전시별 집계 |
| `first_viewed_on` | date | N | | | 첫 열람 **관람일**(KST). B-1-1의 `8 / 12` 산출 기준 |
| `first_viewed_at` | timestamptz | N | `now()` | | |
| `last_viewed_at` | timestamptz | N | `now()` | | |
| `view_count` | smallint | N | `1` | | 진단용 |
| `is_anonymized` | bool | N | `false` | | |
| `created_at` / `updated_at` | timestamptz | N | `now()` | | |

**인덱스** — `uq_artwork_view_log_user_artwork UNIQUE (user_id, artwork_id)`, `ix_artwork_view_log_user_day (user_id, first_viewed_on DESC)`, `ix_artwork_view_log_exhibition (exhibition_id, user_id)`, `ix_artwork_view_log_artwork (artwork_id)`.

**활용** — C 갤러리 그리드의 "이미 열어본 표식"은 **전시 기준**이다(PRD §6.5). `WHERE user_id = ? AND exhibition_id = ?`로 조회하며 `ix_artwork_view_log_exhibition`이 이를 커버한다.

### 4.8 `notice` — 휴관 공지

> **📘 쉬운 설명**
>
> "9월 5일까지 쉽니다" 같은 안내를 **기간을 정해서 미리 걸어두는** 기능입니다. 시작일이 되면 저절로 뜨고 종료일이 지나면 저절로 사라져서, 여행 가기 전에 예약해두고 돌아와서 끄는 걸 잊어버릴 걱정이 없습니다.
>
> `EXCLUDE` 제약이 낯설 텐데, **"활성 공지의 기간끼리 겹칠 수 없다"를 데이터베이스가 직접 막는 장치**입니다. 겹치는 공지가 두 개 있으면 "오늘의 공지"가 어느 쪽인지 정할 수 없게 되기 때문입니다.

PRD §6.1 GAP-18.

| 컬럼 | 타입 | Null | 기본값 | 제약·인덱스 | 설명 |
|---|---|:---:|---|---|---|
| `id` | uuid | N | UUIDv7 | PK | |
| `starts_on` | date | N | | | 공지 시작일(KST, 포함) |
| `ends_on` | date | N | | `ck_notice_period` | 공지 종료일(KST, 포함) |
| `body` | varchar(300) | N | | | 안내 문구 |
| `is_active` | bool | N | `true` | | 취소 시 false |
| `created_by` | uuid | Y | | FK→`app_user` `SET NULL` | |
| `created_at` / `updated_at` | timestamptz | N | `now()` | | |

**제약·인덱스**

- `ck_notice_period`: `ends_on >= starts_on`
- `ex_notice_no_overlap`: `EXCLUDE USING gist (daterange(starts_on, ends_on, '[]') WITH &&) WHERE (is_active)` — 활성 공지 기간이 겹치지 않게 DB가 보장한다. `btree_gist` 확장 필요. 겹침을 허용하면 "오늘의 공지"가 비결정적이 된다.
- `ix_notice_period (starts_on, ends_on) WHERE is_active`

**활용** — 공지 기간은 §3.2 발행 빈도 지표의 분모에서 제외된다. 큐레이터 연장 알림(§4.10)도 이 기간에는 발송하지 않는다.

### 4.9 `app_setting` — 전역 설정

> **📘 쉬운 설명**
>
> 나중에 조정하고 싶어질 값들을 모아둔 표입니다. "가입을 받을까 말까", "알림 기본 시각은 몇 시", "지난 전시를 몇 개까지 보여줄까" 같은 것들입니다.
>
> **왜 코드에 적지 않고 표에 두나요?** 코드에 적어두면 값을 바꿀 때마다 개발자가 다시 배포해야 합니다. 표에 두면 관리자 화면에서 스위치 하나로 바꿉니다.
>
> 반대로 **아무거나 다 여기 넣지도 않습니다.** 비밀 열쇠처럼 바뀌면 안 되는 값은 여기가 아니라 별도의 금고에 둡니다.

키-값 단일 테이블. 설정 하나마다 컬럼을 늘리는 대신 확장 가능한 형태로 둔다(DP-6).

| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|:---:|---|---|
| `key` | varchar(50) | N | | PK |
| `value` | jsonb | N | | 스칼라도 JSON 스칼라로 저장 |
| `value_type` | text | N | | `bool`\|`int`\|`string`\|`time`\|`json` |
| `description` | varchar(200) | N | | 운영자용 설명 |
| `is_mutable` | bool | N | `true` | false면 API로 변경 불가(배포로만 변경) |
| `updated_by` | uuid | Y | | FK→`app_user` `SET NULL` |
| `updated_at` | timestamptz | N | `now()` | |

**시드 값**

| key | type | 기본값 | 근거 |
|---|---|---|---|
| `signup_open` | bool | `true` | PRD §6.14 가입 잠금 |
| `notify_default_time` | time | `"07:30"` | §6.12 |
| `notify_cutoff_hour` | int | `21` | §6.12 · 부록 B. 조정 가능해야 한다 |
| `carryover_alert_days` | int | `2` | 연장 2일 연속 시 큐레이터 알림 |
| `archive_size` | int | `30` | §6.8 최근 30개 전시 |
| `admin_calendar_days` | int | `7` | §6.9 기본 7일치 |
| `log_retention_days` | int | `180` | PRD §7.3 |
| `media_signed_ttl_seconds` | int | `21600` | 미디어 서명 유효기간 6시간 |
| `media_signing_mode` | string | `"cookie"` | `cookie`(기본) \| `url`. 쿠키가 차단되는 환경을 위한 대체 경로(API 문서 §6.10) |
| `maintenance_mode` | bool | `false` | 점검 모드. A 첫 화면만 살린다(§8.5) |
| `session_ttl_days` | int | `90` | GAP-14 |

설정은 애플리케이션에서 **요청 단위 캐시 + 60초 TTL 프로세스 캐시**로 읽는다(백엔드 문서 §6.4).

### 4.10 `notification_log` — 알림 발송 이력

> **📘 쉬운 설명**
>
> 알림을 **보냈는지, 안 보냈는지, 왜 안 보냈는지**를 전부 남기는 표입니다.
>
> 보내지 않기로 한 경우에도 줄을 남기는 게 포인트입니다. 나중에 "저는 왜 알림을 못 받았죠?"라는 질문이 오면, 이 표를 보고 "그날은 새 전시가 없어서 안 보내드린 겁니다" 또는 "알림이 꺼져 있었습니다"라고 답할 수 있습니다. 기록이 없으면 아무 답도 못 합니다.
>
> `dedupe_key`(중복 방지 열쇠)는 **같은 알림이 두 번 나가는 사고를 데이터베이스 차원에서 막는 장치**입니다. 알림 보내는 프로그램이 실수로 두 번 실행돼도, 두 번째는 "이미 있는 값"이라며 거부됩니다.

PRD §6.12. 중복 발송 방지와 사후 추적을 동시에 담당한다.

| 컬럼 | 타입 | Null | 기본값 | 제약·인덱스 | 설명 |
|---|---|:---:|---|---|---|
| `id` | uuid | N | UUIDv7 | PK | |
| `user_id` | uuid | Y | | FK→`app_user` `SET NULL` | 수신자(큐레이터 알림 포함) |
| `kind` | text | N | | `ck_notification_log_kind` | `morning_exhibition`(예약 발송) \| `late_publish`(사용자 알림 시각이 지난 뒤 발행되어 즉시 발송) \| `curator_carryover` \| `curator_signup` |
| `dedupe_key` | varchar(160) | N | | `uq_notification_log_dedupe` | 예 `morning:{user_id}:{exhibition_date}` |
| `exhibition_id` | uuid | Y | | FK→`exhibition` `SET NULL` | |
| `status` | text | N | `'pending'` | `ck_notification_log_status` | `pending`\|`sent`\|`skipped`\|`failed` |
| `skip_reason` | varchar(40) | Y | | | `carryover`\|`cutoff_passed`\|`notify_disabled`\|`no_subscription`\|`blocked`\|`notice_period` |
| `scheduled_for` | timestamptz | N | | | 발송 예정 시각 |
| `sent_at` | timestamptz | Y | | | |
| `attempt_count` | smallint | N | `0` | | |
| `last_error` | varchar(300) | Y | | | |
| `payload` | jsonb | Y | | | 발송 시점 제목·본문·링크 스냅샷 |
| `created_at` / `updated_at` | timestamptz | N | `now()` | | |

**인덱스** — `uq_notification_log_dedupe UNIQUE (dedupe_key)`, `ix_notification_log_pending (scheduled_for) WHERE status = 'pending'`, `ix_notification_log_user (user_id, created_at DESC)`.

**규칙** — `dedupe_key`의 UNIQUE 제약이 "하루 1회"와 "연장 2일차 1회만"을 DB 수준에서 보장한다. 스케줄러가 중복 기동해도 두 번째는 제약 위반으로 무시된다. 발송하지 않기로 한 경우에도 `status='skipped'` 행을 남긴다 — **보내지 않은 이유가 남아야 운영 중 문의에 답할 수 있다.**

### 4.11 `audit_log` — 관리자 조작 이력

> **📘 쉬운 설명**
>
> "누가 언제 무엇을 바꿨는가"를 남기는 표입니다. 회원 차단, 전시 숨김, 비밀번호 초기화처럼 **되돌리기 어려운 조작**이 대상입니다.
>
> 관리자가 한 명뿐인 서비스에 이게 왜 필요할까요? 남을 감시하기 위해서가 아니라, **몇 달 뒤에 "이 전시가 왜 숨겨져 있지?"라고 스스로 궁금해질 때 답을 찾기 위해서**입니다.

PRD 본문에는 없으나 DP-4에 따라 추가한다. 차단·숨김·비밀번호 초기화 같은 되돌리기 어려운 조작의 근거를 남긴다.

| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|:---:|---|---|
| `id` | uuid | N | UUIDv7 | PK |
| `actor_id` | uuid | Y | | FK→`app_user` `SET NULL` |
| `actor_role` | text | N | | 조작 시점의 역할 스냅샷 |
| `action` | varchar(60) | N | | 예 `member.block`, `exhibition.hide`, `exhibition.carry_draft` |
| `target_type` | varchar(40) | Y | | `exhibition`\|`artwork`\|`app_user`\|`notice`\|`app_setting` |
| `target_id` | uuid | Y | | |
| `summary` | varchar(200) | N | | 사람이 읽는 한 줄 |
| `changes` | jsonb | Y | | `{"before": {...}, "after": {...}}`. **비밀번호 해시·전화번호 전체는 담지 않는다** |
| `request_id` | varchar(40) | Y | | API 응답 `meta.request_id`와 대조 |
| `created_at` | timestamptz | N | `now()` | |

**인덱스** — `ix_audit_log_created (created_at DESC)`, `ix_audit_log_target (target_type, target_id, created_at DESC)`, `ix_audit_log_actor (actor_id, created_at DESC)`.

---

## 5. 열거형 카탈로그

> **📘 쉬운 설명**
>
> "정해진 몇 개 중 하나만 들어갈 수 있는 칸"의 목록입니다. 예를 들어 회원 등급은 `viewer` 아니면 `curator`, 그 외의 값은 저장되지 않습니다.
>
> 이걸 한 곳에 모아두는 이유는, 같은 값을 **백엔드·프런트엔드·데이터베이스 세 곳에서 각자 적어두면 반드시 어긋나기** 때문입니다. 여기를 원본으로 정하고 나머지는 이걸 베끼기로 했습니다.

애플리케이션 `chalicelib/db/models/enums.py`가 단일 진실 원천이며, 프런트엔드 `shared/types/enums.ts`가 이를 미러링한다(API 문서 §3.6에 값 목록을 명시).

| 열거형 | 값 | 사용처 |
|---|---|---|
| `UserRole` | `viewer`, `curator` | `app_user.role` |
| `FontScale` | `normal`, `large` | `app_user.font_scale` |
| `CreatedVia` | `self`, `curator` | `app_user.created_via` |
| `ImageStatus` | `empty`, `uploading`, `processing`, `ready`, `failed` | `artwork.image_status` |
| `ExhibitionDayStatus` | `published`, `carried_over`, `empty` | **DB 컬럼 아님.** 관리자 달력 응답의 파생 상태(Y/↑/N) |
| `NotificationKind` | `morning_exhibition`, `late_publish`, `curator_carryover`, `curator_signup` | `notification_log.kind` |
| `NotificationStatus` | `pending`, `sent`, `skipped`, `failed` | `notification_log.status` |
| `ThrottleScope` | `login`, `signup`, `password_reset`, `media_session` | `auth_throttle.scope` |
| `PushPlatform` | `ios`, `android`, `desktop`, `unknown` | `push_subscription.platform` |

---

## 6. 상태 전이

> **📘 쉬운 설명**
>
> **상태 전이**란 "어떤 상태에서 어떤 상태로 갈 수 있고, 무엇이 그 이동을 일으키는가"입니다.
>
> 신호등으로 치면 "빨강 → 초록 → 노랑 → 빨강" 순서가 정해져 있고 "빨강 → 노랑"은 없는 것과 같습니다. 이걸 미리 적어두지 않으면, 코드 여기저기서 상태를 마음대로 바꾸다가 있을 수 없는 상태(예: 발행됐는데 발행 시각은 비어 있음)가 만들어집니다.

### 6.1 전시 라이프사이클

> **📘 쉬운 설명**
>
> 전시가 태어나서 사람들에게 보이기까지의 과정입니다.
>
> `없음 → 드래프트(작성 중) → 발행됨(걸림) → 숨김`
>
> 아래 **불변식**이라는 말은 "무슨 일이 있어도 항상 참이어야 하는 것"입니다. 그중 5번을 보세요 — "미래 날짜의 전시가 미리 만들어져 있을 수 있다"입니다. 큐레이터가 주말에 다음 주치를 미리 채워두면, **그날이 되는 순간 저절로 걸립니다.** 따로 예약 기능을 만들지 않아도 되는 이유는 "오늘 이하의 날짜만 보여준다"는 조건 하나로 해결되기 때문입니다.

| 상태 | 조건 | 관람자 노출 | 다음 상태 |
|---|---|---|---|
| **없음** | 해당 날짜 행 자체가 없음 | — | 드래프트(B-2 진입 시 행 생성) |
| **드래프트** | `is_published=false` | 미노출 | 발행 (조건 충족 시) · 삭제 (§8.3 조건부) |
| **발행됨** | `is_published=true`, `is_hidden=false` | `exhibition_date <= 오늘`이면 노출 대상 | 숨김 |
| **숨김** | `is_published=true`, `is_hidden=true` | 미노출. 아카이브에서도 제외 | 발행됨 (숨김 해제) |

**불변식**

1. `is_published`는 **단조 증가**한다(false→true만 허용).
2. 드래프트 → 발행 전환은 발행 조건(§4.4)이 충족되는 저장 요청의 트랜잭션 안에서만 일어난다.
3. 발행 전환과 동시에 `notification_log`에 그 전시의 알림 작업이 등록된다(§4.10).
4. `exhibition_date > 오늘`인 발행본은 존재할 수 있다(미리 채워둔 미래 전시). 관람자 질의가 `exhibition_date <= 오늘` 조건으로 걸러내므로 별도 예약 처리가 필요 없다.
5. 발행일이 과거인 새 전시 생성(백필)은 **서비스 계층에서 거부**한다. DB 제약으로는 강제하지 않는다 — 날짜가 지나면 기존 행도 자동으로 과거가 되므로 제약으로 표현할 수 없다.

### 6.2 이미지 파이프라인 상태

> **📘 쉬운 설명**
>
> 사진을 올린 뒤 실제로 쓸 수 있게 되기까지의 단계입니다. **파이프라인**은 "공장의 컨베이어 벨트"라고 생각하면 됩니다 — 원본이 들어가서 세 가지 크기로 나옵니다.
>
> 여기서 중요한 건 마지막 문장입니다. **처리가 끝나지 않은 그림은 "완성"으로 세지 않습니다.** 그래서 사진만 올려두고 아직 변환이 안 끝난 상태로 전시가 발행되는 일이 없습니다.

| 상태 | 진입 계기 | 이탈 계기 |
|---|---|---|
| `empty` | 그림 행 생성 | 업로드 URL 발급 → `uploading` |
| `uploading` | Presigned URL 발급 | S3 이벤트 수신 → `processing` / 30분 무응답 → `failed`(`UPLOAD_TIMEOUT`) |
| `processing` | 리사이즈 Lambda 시작 | 3종 생성 성공 → `ready` / 예외 → `failed` |
| `ready` | 썸네일·디스플레이·LQIP 생성 완료 | 재업로드 시 `uploading`으로 회귀 |
| `failed` | 처리 예외 | 재업로드 시 `uploading`으로 회귀 |

`ready` 이외의 상태는 `is_complete=false`를 강제하므로(§4.5 생성 컬럼) **이미지 처리가 끝나지 않은 그림은 발행 카운트에 잡히지 않는다.**

### 6.3 알림 상태

> **📘 쉬운 설명**
>
> 아침 알림은 **늦게 가면 의미가 없습니다.** 오후 3시에 "좋은 아침입니다" 알림이 오면 성가시기만 하죠.
>
> 그래서 다른 실패와 달리 계속 재시도하지 않고, 정해진 시각(밤 9시)이 지나면 **그냥 포기**합니다. 포기했다는 사실은 기록에 남깁니다.

`pending` → (`sent` | `skipped` | `failed`). `failed`는 최대 3회까지 재시도하며 초과 시 그대로 종료한다. 아침 알림은 시의성이 전부이므로 **당일 `notify_cutoff_hour`를 넘기면 재시도하지 않고 `skipped(cutoff_passed)`로 종료**한다.

---

## 7. 핵심 질의 패턴

> **📘 쉬운 설명**
>
> **질의(Query)**는 데이터베이스에게 던지는 질문입니다. "오늘 걸려야 할 전시가 뭐야?" 같은 것이죠.
>
> 이 절이 중요한 이유 — 어떤 질문은 **하루에 수천 번** 던져지고, 어떤 질문은 **한 달에 한 번**입니다. 자주 던지는 질문은 빨리 답할 수 있게 미리 준비(인덱스)해둬야 합니다.
>
> 표의 **Q1**을 보세요. "현재 전시" 질문은 모든 관람자의 모든 접속이 반드시 거치는 질문입니다. 이것 하나가 느리면 서비스 전체가 느려집니다. 그래서 이 질문 전용 인덱스를 따로 만들어뒀습니다.

모든 질의는 KST 기준 날짜를 애플리케이션에서 계산해 파라미터로 주입한다(§2.4).

| ID | 질의 | 조건식 | 사용 인덱스 | 호출 빈도 |
|---|---|---|---|---|
| **Q1** | **현재 전시** | `is_published AND NOT is_hidden AND exhibition_date <= :today` `ORDER BY exhibition_date DESC LIMIT 1` | `ix_exhibition_live` | 최고 (모든 진입) |
| **Q2** | 특정 날짜 전시 | `exhibition_date = :date AND is_published AND NOT is_hidden` | `uq_exhibition_date` | 중 (아카이브 상세) |
| **Q3** | 아카이브 목록 | Q1과 동일 조건 + `LIMIT :archive_size` (기본 30) | `ix_exhibition_live` | 중 |
| **Q4** | 전시 그림 12점 | `exhibition_id = :id ORDER BY position` | `ix_artwork_exhibition` | 높음 |
| **Q5** | 알림 대상 회원 | `notify_enabled AND NOT is_blocked AND notify_at BETWEEN :from AND :to` | `ix_app_user_notify` | 5분마다 |
| **Q6** | 관리자 달력 | §7.1 참조 | `uq_exhibition_date` + `ix_exhibition_live` | 낮음 |
| **Q7** | 일별 입장자 수 | `viewed_on BETWEEN :from AND :to AND NOT is_anonymized` `GROUP BY viewed_on` | `ix_view_log_day` | 낮음 |
| **Q8** | 회원별 감상 상세 | `user_id = :id AND viewed_on >= :from` + 전시별 열람 그림 수 | `ix_view_log_user_recent`, `ix_artwork_view_log_user_day` | 낮음 |
| **Q9** | 주간 감상률(NSM) | 회원별 `count(DISTINCT viewed_on) >= 3`인 회원 비율 | `ix_view_log_day` | 낮음 |
| **Q10** | 관람 표식 | `user_id = :id AND exhibition_id = :ex` | `ix_artwork_view_log_exhibition` | 높음 |
| **Q11** | 현재 휴관 공지 | `is_active AND :today BETWEEN starts_on AND ends_on` | `ix_notice_period` | 높음 (A 화면) |
| **Q12** | 회원 목록(B-3) | §7.2 참조 | `ix_app_user_created_at`, `ix_view_log_user_recent`, `ix_push_subscription_user` | 낮음 |

### 7.1 관리자 달력 질의(Q6) — 연장 상태 해석

> **📘 쉬운 설명**
>
> 관리자 화면의 날짜 목록에 뜨는 `Y`(발행됨) / `↑`(연장됨) / `N`(비어 있음) 표시를 **어떻게 계산하는가**입니다.
>
> 이 값들은 데이터베이스에 저장돼 있지 않습니다. 물어볼 때마다 "이 날짜는 어떤 상태였지?"를 계산해서 만들어냅니다.
>
> 마지막 문단의 **N+1 금지**가 중요한 지적입니다. 날짜 7개를 보여주려고 "8월 27일 상태는?" "8월 28일 상태는?" 하고 7번 따로 물으면(= 1번 + 7번), 30일치를 보면 31번을 묻게 됩니다. 이걸 **한 번의 질문으로 전부 받아오라**는 규칙입니다. 화면이 느려지는 가장 흔한 원인이 바로 이것입니다.

B 관리자 화면의 3열(`Y` / `↑ MM.DD` / `N`)은 **저장된 값이 아니라 날짜 범위에 대해 계산되는 파생값**이다. 계산 규칙:

1. 요청 범위의 각 날짜 `d`에 대해,
2. `exhibition` 행이 있고 `is_published AND NOT is_hidden`이면 → `published`(`Y`)
3. 아니고 `d < 오늘`이면 → `d` 이하의 최근 발행 전시를 찾아 `carried_over`(`↑ 발행일`). 찾지 못하면(개관 전) `empty`
4. 아니고 `d >= 오늘`이면 → `empty`(`N`)

구현은 날짜 시리즈 생성 후 `LATERAL` 조인으로 각 날짜의 대표 전시를 1건씩 끌어오는 **단일 질의**로 수행한다. 날짜별 반복 질의(N+1)를 금지한다. 범위 상한은 기본 7일, 과거 스크롤 시 30일 단위 페이지네이션으로 확장한다.

또한 각 날짜 행에는 드래프트 존재 여부(`has_draft`)와 진행률(`complete_artwork_count`)을 함께 반환한다 — 과거 미발행일의 `오늘 날짜로 이어서 쓰기` 노출 조건이 이 값이다(PRD §6.9).

### 7.2 회원 목록 질의(Q12) — 파생 필드 결합

> **📘 쉬운 설명**
>
> 회원 목록 화면에는 회원 정보 외에 **"마지막으로 온 날"과 "알림을 받고 있는지"**도 함께 보여야 합니다. 그런데 이 두 정보는 다른 표에 들어 있습니다.
>
> 아무 생각 없이 만들면 회원 한 명당 두 번씩 추가 질문을 하게 되고(§7.1의 N+1), 회원이 100명이면 201번을 묻습니다. 그래서 한 번에 가져오는 방법을 미리 정해뒀습니다.
>
> 마지막 문단은 **"지금은 이렇게 하고, 회원이 5,000명을 넘으면 이렇게 바꾼다"**까지 적어둔 것입니다. 지금 필요 없는 최적화를 미리 하지 않되, 언제 해야 하는지는 적어두는 태도입니다.

`MemberItem`(API 문서 §3.8)은 회원 행마다 **마지막 입장일**과 **푸시 상태**를 함께 요구한다. 두 값 모두 다른 테이블에 있으므로 행마다 조회하면 N+1이 된다. 다음과 같이 **단일 질의**로 해결한다.

1. `app_user`를 필터·정렬·페이징한다(서브쿼리로 페이지 경계를 먼저 확정).
2. 그 결과에 `LATERAL` 로 `view_log`의 `max(viewed_on)`을 붙인다 — `ix_view_log_user_recent`가 인덱스 온리 스캔으로 해결한다.
3. 같은 방식으로 `push_subscription`을 집계해 `push_status`(활성 1건 이상이면 `active`, 구독은 있으나 전부 비활성이면 `inactive`, 없으면 `none`)와 `platform` 배열을 만든다.

`sort=-last_viewed_on`처럼 **파생 필드로 정렬하는 경우**에는 1과 2의 순서가 뒤바뀐다(전체 회원에 대해 파생값을 먼저 계산한 뒤 정렬·페이징). 회원 수가 수백 명 수준이므로 전체 스캔이 허용되며, 회원이 5,000명을 넘으면 §13의 `daily_stat` 롤업 또는 `app_user.last_viewed_on` 비정규화를 도입한다.

### 7.3 성능 예산

| 질의 | 목표 | 대상 규모 |
|---|---|---|
| Q1 | ≤ 3ms | 전시 행 수 = 운영일수(연 365) |
| Q4 | ≤ 5ms | 12행 |
| Q7·Q9 | ≤ 50ms | 회원 100 × 180일 = 최대 18,000행 |
| Q6 | ≤ 30ms | 최대 30일 범위 |

전 테이블 합계 예상 행 수는 3년 운영 기준 **약 25만 행**, 데이터 크기 **200MB 미만**(이미지는 S3)이다. RDS 최소 인스턴스(db.t4g.micro)로 충분하며, 인덱스는 전량 메모리에 상주한다.

---

## 8. 데이터 무결성 규칙

> **📘 쉬운 설명**
>
> **무결성**은 "정보가 앞뒤가 안 맞는 상태가 되지 않게 하는 것"입니다.
>
> 이 절의 요점은 **"규칙을 어디서 지킬 것인가"**입니다. 두 곳에서 지킬 수 있습니다.
>
> - **데이터베이스가 지킨다** — 어기면 저장 자체가 거부됩니다. 확실하지만 표현할 수 있는 규칙이 단순한 것들뿐입니다
> - **프로그램이 지킨다** — 복잡한 규칙도 표현되지만, 개발자가 그 코드를 안 거치는 경로를 만들면 뚫립니다
>
> 그래서 **단순하고 절대적인 규칙은 데이터베이스에**, 상황 판단이 필요한 규칙은 프로그램에 두었습니다. §8.1과 §8.2가 그 구분입니다.

### 8.1 DB가 보장하는 것

| 규칙 | 수단 |
|---|---|
| 하루에 전시 하나 | `uq_exhibition_date` |
| 전시 내 슬롯 중복 없음 | `uq_artwork_slot` |
| 슬롯 번호 1–12 | `ck_artwork_position` |
| 관람일당 입장 1행 | `uq_view_log_user_day` |
| (회원, 그림)당 열람 1행 | `uq_artwork_view_log_user_artwork` |
| 알림 중복 발송 없음 | `uq_notification_log_dedupe` |
| 휴관 공지 기간 중첩 없음 | `ex_notice_no_overlap` |
| 큐레이터 계정 유일 | `uq_app_user_single_curator` |
| 발행 상태와 발행 시각의 정합 | `ck_exhibition_published_at` |
| `ready` 이미지의 키 존재 | `ck_artwork_image_keys` |
| 완성 판정의 단일 정의 | `artwork.is_complete` 생성 컬럼 |

### 8.2 애플리케이션이 보장하는 것

| 규칙 | 위치 | 실패 시 |
|---|---|---|
| `is_published` 단방향 | `ExhibitionService.apply_publish_rules` | 무시(상태 유지) |
| 백필 금지 | `ExhibitionService.assert_editable` | `409 EXHIBITION_BACKFILL_FORBIDDEN` |
| 이어쓰기 대상 중복 검사 | `DraftService.carry_over` | `409 DRAFT_TARGET_OCCUPIED` |
| 카운터 재계산 | `ArtworkService` 전 변경 경로 | 야간 배치가 교정 |
| 가입 잠금 | `AuthService.signup` | `403 SIGNUP_CLOSED` |
| 차단 회원 로그인 거부 | `AuthService.login` | `401 AUTH_INVALID_CREDENTIALS`(사실 은닉) |
| 글자수 상한 | Pydantic 스키마 + `varchar(n)` 이중 방어 | `422 VALIDATION_FAILED` |

### 8.3 삭제 제한

> **📘 쉬운 설명**
>
> **일부러 삭제 기능을 만들지 않은 것들**의 목록입니다.
>
> 특히 마지막 항목 — 그림을 지워도 이미지 파일은 7일 뒤에 지웁니다. 실수로 지웠을 때 되돌릴 여지를 남겨두는 것입니다. 저장 공간은 싸고, 하루치 작업은 비쌉니다.

- **발행된 전시(`is_published=true`)는 삭제하지 않는다.** 유일한 철회 수단은 `is_hidden`이다. API에 삭제 엔드포인트를 두지 않는다.
- 드래프트 전시는 그림이 0개일 때만 삭제 가능하다. 그림이 있으면 그림을 먼저 비워야 한다 — 실수로 하루치 작업을 날리는 경로를 만들지 않는다.
- 그림 삭제는 슬롯 비우기(행 삭제)로 처리하고, S3 오브젝트는 즉시 지우지 않고 **7일 뒤 정리 배치**가 회수한다(되돌리기 여지 확보).

---

## 9. 마이그레이션 전략

> **📘 쉬운 설명**
>
> **마이그레이션**은 이미 운영 중인 데이터베이스의 구조를 바꾸는 작업입니다.
>
> 왜 이게 어렵냐면 — 이미 정보가 들어 있는 상태에서 바꿔야 하기 때문입니다. 이사할 때 빈 집으로 옮기는 게 아니라, **사람이 살고 있는 집의 벽을 옮기는 것**에 가깝습니다.
>
> 그래서 (1) 모든 변경을 순서대로 파일로 남기고, (2) 되돌리는 방법도 함께 적고, (3) 진짜 서비스에 적용하기 전에 연습 환경에서 먼저 해봅니다.

### 9.1 도구와 배치

Alembic을 `backend/migrations/`에 둔다. Chalice 배포 패키지에는 포함하지 않으며, **마이그레이션은 배포 파이프라인의 독립 단계**로 실행한다(백엔드 문서 §11).

| 항목 | 규약 |
|---|---|
| 리비전 파일명 | `{순번4자리}_{동사}_{대상}.py` — 예 `0003_add_notice_exclusion.py` |
| 브랜치 | 사용하지 않음. 단일 선형 히스토리 |
| `down_revision` | 항상 명시. `downgrade()`는 반드시 구현 |
| 자동 생성 | `--autogenerate` 결과를 **그대로 쓰지 않는다.** 부분 인덱스·EXCLUDE·생성 컬럼은 감지되지 않으므로 수기 보정한다 |
| 확장 | `0001`에서 `pg_trgm`, `btree_gist` 생성 |

### 9.2 안전 규칙

> **📘 쉬운 설명**
>
> 여기 적힌 4가지는 전부 **"한 번에 하지 말고 나눠서 하라"**는 이야기입니다.
>
> 예를 들어 칸 이름을 바꿀 때, 한 번에 바꾸면 그 순간 옛날 이름을 쓰던 코드가 전부 고장 납니다. 그래서 ① 새 이름 칸을 추가하고 양쪽에 다 쓰다가 ② 다음 배포에서 옛 칸을 지웁니다. 느려 보이지만 **중간에 서비스가 멈추지 않습니다.**

1. **파괴적 변경은 2단계로 나눈다.** 컬럼 삭제·이름 변경은 (a) 새 컬럼 추가 + 이중 쓰기 배포 → (b) 다음 릴리스에서 구 컬럼 제거.
2. **인덱스는 `CONCURRENTLY`로 만든다.** 이 경우 해당 리비전은 트랜잭션 밖에서 실행하도록 표시한다.
3. `NOT NULL` 추가는 (기본값 포함 컬럼 추가) → (백필) → (제약 추가) 순서로 나눈다.
4. 마이그레이션은 **롤백 가능해야 하고**, 스테이징에서 프로덕션 스냅샷 복원본에 먼저 적용해 검증한다.

### 9.3 시드 데이터

> **📘 쉬운 설명**
>
> 서비스를 처음 켤 때 **반드시 있어야 하는 최소한의 정보**를 미리 넣어두는 것입니다. 큐레이터 계정이 없으면 아무도 전시를 올릴 수 없으니 서비스가 시작조차 안 됩니다.
>
> 마지막 문장이 좋은 태도입니다 — 큐레이터 계정 정보가 없으면 **조용히 넘어가지 않고 일부러 실패시킵니다.** 실패하면 바로 알아채지만, 조용히 넘어가면 나중에 이상한 곳에서 문제가 터집니다.

`0002_seed.py`가 아래를 멱등하게 삽입한다(존재하면 건너뜀).

| 대상 | 내용 |
|---|---|
| 큐레이터 계정 | 환경변수 `SEED_CURATOR_PHONE`·`SEED_CURATOR_PASSWORD`·`SEED_CURATOR_NAME` 기반 1건. `must_change_password=true` |
| `app_setting` | §4.9 시드 표 전량 |

시드용 환경변수가 없으면 마이그레이션은 실패한다 — 큐레이터 계정 없는 배포는 동작 불가 상태이므로 조용히 넘기지 않는다.

---

## 10. 보존·파기 정책

> **📘 쉬운 설명**
>
> **"언제까지 갖고 있다가 언제 지울 것인가"**입니다. 개인정보는 오래 갖고 있을수록 위험이 커지므로, 필요 없어지는 시점을 미리 정해두고 자동으로 지웁니다.
>
> 전시와 그림은 영구 보관이지만, 방문 기록은 180일 뒤 자동 삭제입니다. 6개월이면 이 서비스가 보려는 지표를 계산하기에 충분하기 때문입니다.

| 데이터 | 보존 기간 | 파기 방식 | 근거 |
|---|---|---|---|
| `exhibition`, `artwork` | 영구 | — | PRD §7.3 |
| `view_log`, `artwork_view_log` | **180일** | 일 1회 배치 하드 삭제 | PRD §7.3 |
| `notification_log` | 90일 | 일 1회 배치 하드 삭제 | 운영 문의 대응 기간 |
| `audit_log` | 365일 | 일 1회 배치 하드 삭제 | 관리자 조작 추적 |
| `auth_throttle` | 24시간(비활성 행) | 일 1회 배치 | |
| `push_subscription` | 비활성 후 30일 | 일 1회 배치 | |
| 탈퇴 회원(`app_user`) | 즉시 | 하드 삭제 + 로그 익명화 | PRD §7.3 |
| S3 원본 이미지 | 영구 | — | |
| S3 고아 오브젝트 | 7일 | 정리 배치 | §8.3 |

### 10.1 탈퇴 처리 트랜잭션

> **📘 쉬운 설명**
>
> 회원이 탈퇴할 때 벌어지는 일을 순서대로 적어둔 것입니다. 5개 작업이 **전부 성공하거나 전부 취소되어야** 합니다(= 트랜잭션). 중간에 멈추면 계정은 지워졌는데 알림은 계속 가는 이상한 상태가 됩니다.
>
> 마지막 항목이 세심한 부분입니다. 탈퇴 사실을 기록으로 남기되, **누가 탈퇴했는지는 어디에도 남기지 않습니다.** "회원 1명이 탈퇴함"만 남습니다.

1. `view_log`·`artwork_view_log`의 해당 `user_id`를 NULL로 바꾸고 `is_anonymized=true`로 표시한다.
2. `push_subscription`·`notification_log`·`auth_throttle`의 관련 행을 삭제한다.
3. `audit_log.actor_id`는 FK `SET NULL`로 자동 해제된다(관리자 조작 기록의 형태는 남는다).
4. `app_user` 행을 삭제한다.
5. `audit_log`에 `member.withdraw` 1건을 남긴다 — **actor는 NULL, target_id도 NULL, summary에만 "회원 1명 탈퇴"를 남긴다.** 탈퇴자를 식별할 수 있는 값은 어디에도 남기지 않는다.

익명화된 로그는 §3.2 지표의 **분모·분자 모두에서 제외**된다. 모든 지표 질의는 `is_anonymized = false` 조건을 포함한다.

---

## 11. 운영 배치

> **📘 쉬운 설명**
>
> **배치**는 사람이 시키지 않아도 정해진 시각에 스스로 도는 청소·점검 작업입니다. 새벽 4시대에 몰아둔 이유는 사용자가 없는 시간이기 때문입니다.
>
> 마지막 문장 — "처리 건수를 기록으로 남긴다"가 중요합니다. **아무 일도 안 한 날에도 "0건 처리함"을 남겨야** 이 작업이 죽었는지 살아 있는지 알 수 있습니다.

| 배치 | 주기 | 내용 |
|---|---|---|
| `retention_cleanup` | 매일 04:00 KST | §10 보존 기간 초과 행 삭제 |
| `consistency_check` | 매일 04:10 KST | `exhibition` 카운터 재계산·불일치 시 교정 및 경보 |
| `stuck_upload_sweeper` | 30분마다 | `uploading`/`processing` 30분 초과 건을 `failed`로 전환 |
| `orphan_object_cleanup` | 매일 04:20 KST | DB가 참조하지 않는 S3 오브젝트 중 7일 경과분 삭제 |
| `push_subscription_prune` | 매일 04:30 KST | 비활성 30일 경과 구독 삭제 |

배치는 모두 **멱등**해야 하며, 처리 건수를 구조화 로그로 남긴다.

---

## 12. 백업·복구

> **📘 쉬운 설명**
>
> **RPO**는 "사고가 나면 최대 몇 분치 정보를 잃을 수 있는가", **RTO**는 "복구하는 데 몇 시간이 걸리는가"입니다. 여기서는 5분 / 2시간으로 잡았습니다.
>
> 마지막 줄의 **복원 리허설**이 핵심입니다. 백업은 받아두는 것보다 **실제로 되살려보는 것**이 중요합니다. 막상 사고가 났을 때 백업 파일이 깨져 있었다는 이야기가 흔합니다.

| 항목 | 설정 |
|---|---|
| 자동 백업 | RDS 자동 백업 7일 보관, PITR 활성화 |
| 스냅샷 | 배포 직전 수동 스냅샷 1회 (마이그레이션 포함 배포에 한함) |
| 복구 목표 | RPO 5분 / RTO 2시간 (가용성 목표 99%에 대응) |
| 검증 | 분기 1회 스테이징으로 복원 리허설 |
| S3 | 버전 관리 활성화 + 90일 후 비현행 버전 만료 |

---

## 13. 확장 훅 (v1.1 / v1.2)

> **📘 쉬운 설명**
>
> **지금은 만들지 않지만, 나중에 만들 때 고생하지 않도록 자리만 봐둔 것**입니다.
>
> 예를 들어 "카카오 로그인"은 지금 안 만들지만, 나중에 붙일 때 회원 표를 건드리지 않고 새 표 하나만 추가하면 되도록 미리 생각해뒀습니다. 이렇게 해두면 나중의 작업이 **"고치는 일"이 아니라 "더하는 일"**이 됩니다.
>
> 마지막 항목을 보세요 — 다중 큐레이터는 "안 만들기로 한 것"인데도, **막을 때 나중에 열기 쉬운 방법으로 막았습니다**(제약 하나만 지우면 열림).

MVP에서 **테이블을 만들지 않되** 스키마 변경이 국소적이 되도록 설계 지점만 확정해 둔다.

| 기능 | 시점 | 스키마 변경 | 영향 범위 |
|---|---|---|---|
| SMS 비밀번호 재설정 (A-2) | v1.1 | 신규 테이블 `password_reset_token`(`phone`, `code_hash`, `expires_at`, `attempt_count`, `consumed_at`, `created_at`) | 신규 테이블만. 기존 무영향 |
| 카카오 로그인 | v1.2 | 신규 테이블 `social_identity`(`user_id`, `provider`, `provider_uid` UNIQUE) | `app_user` 무변경. 계정 병합 로직만 추가 |
| 예약 발행(시각 지정) | v1.2 | `exhibition.publish_at timestamptz` 추가 + Q1 조건에 `publish_at <= now()` 추가 | Q1 인덱스를 `(exhibition_date DESC, publish_at)`로 확장 |
| 작가별·테마별 다시 보기 | v1.2 | `artwork.artist_normalized varchar(40)` + `ix_artwork_artist` | 정규화 백필 필요 |
| 통계 롤업 | 필요 시 | `daily_stat`(`stat_on`, `entrant_count`, `artwork_view_count`) 일 1행 | 회원 100명 규모에서는 **불필요.** 실시간 집계로 충분하며, 회원 1,000명 초과 시 도입 |
| 즉시 차단(세션 무효화) | 필요 시 | 없음 — `token_version` 증가로 구현 가능 | API만 추가 |
| 다중 큐레이터 | Non-goal | `uq_app_user_single_curator` 제거 + `audit_log` 기반 권한 분리 | 제거만으로 열림 |

---

## 14. PRD 대비 변경·보완 사항

> **📘 쉬운 설명**
>
> 기획서(PRD)에 적혀 있던 것과 이 설계서가 **달라진 부분과 그 이유**입니다.
>
> 이런 표를 남기는 이유는, 기획한 사람이 나중에 이 문서를 봤을 때 **"내가 쓴 거랑 다른데?"** 하고 놀라지 않게 하기 위해서입니다. 설계하다 보면 기획 단계에서 미처 몰랐던 사정이 드러나는데, 말없이 바꾸면 신뢰가 깨집니다.

| # | PRD 기술 | 이 문서의 결정 | 사유 |
|---|---|---|---|
| **D-1** | `User.notify_at`이 NULL이면 알림 없음 | `notify_enabled` 불리언을 분리하고 `notify_at`은 NOT NULL | 알림을 껐다 켤 때 이전에 고른 시각이 보존되어야 한다(C-4 UX) |
| **D-2** | 테이블명 `User` | `app_user` | `user`는 PostgreSQL 예약어 |
| **D-3** | `Exhibition.date` | `exhibition_date` | `date`는 타입명과 충돌해 질의 가독성을 해친다 |
| **D-4** | 이미지 S3 키 3종만 명시 | `image_status`·`image_lqip`·`image_width/height`·`image_error_code` 추가 | 비동기 리사이즈(PRD §9.2)의 중간 상태와 블러 플레이스홀더(§6.5)를 표현하려면 필수 |
| **D-5** | `ArtworkViewLog(user_id, artwork_id, viewed_at)` | `first_viewed_on`·`view_count` 추가, (user, artwork) UNIQUE | "중복 제거해서 센다"를 제약으로 표현하고, B-1-1의 일자별 `8/12`를 조인 없이 산출 |
| **D-6** | `ViewLog`에 전시 기록 | `entry_count`·`last_entered_at` 추가 | 지표에는 쓰지 않되 이상 트래픽 진단에 필요 |
| **D-7** | 전역 설정 `signup_open` 하나 | `app_setting` 키-값 테이블 | 알림 컷오프 등 조정 가능해야 할 값이 최소 10개다(부록 B) |
| **D-8** | (없음) | `auth_throttle`, `push_subscription`, `notification_log`, `audit_log` 신설 | 각각 로그인 차단·웹푸시·중복 발송 방지·관리자 조작 추적. 모두 PRD 본문 기능의 구현 필수 요소 |
| **D-9** | (없음) | `exhibition.artwork_count` / `complete_artwork_count` 비정규화 | 관리자 달력이 날짜별 진행률을 표시해야 하는데 매 행마다 그림 집계를 하면 N+1이 된다 |
| **D-10** | (없음) | `notice` 기간 중첩 금지 EXCLUDE 제약 | 겹치는 공지가 있으면 "현재 공지"가 비결정적이 된다 |
| **D-11** | 교차 검토 | `app_setting`에 `media_signing_mode` 추가 | API 문서 §6.10이 참조하는 키가 시드 목록에 없었다 |
| **D-12** | 교차 검토 | 회원 목록 파생 필드 질의(Q12) 정의 | `last_viewed_on`·`push_status`가 응답 스키마에만 있고 산출 방법이 없어 N+1이 될 자리였다 |
| **D-13** | 교차 검토 | `notification_log.kind`의 각 값에 사용 시점을 명기 | 열거값의 의미가 문서에 없으면 구현자가 임의로 쓴다 |
