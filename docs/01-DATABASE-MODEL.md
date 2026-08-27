# 갤러리 K — 데이터 모델 설계서

| | |
|---|---|
| **문서 버전** | v2.0 |
| **상위 문서** | `PRD.md`, `02-API-SPEC.md`, `04-BACKEND-ARCHITECTURE.md` |
| **스택** | PostgreSQL 16 · SQLModel/SQLAlchemy 2.x · Alembic |
| **상태** | 확정 (구현 기준선) |

이 문서는 **구조와 규칙**만 정한다. DDL·질의문·튜닝은 구현 단계에서 결정한다.

---

## 1. 원칙

| # | 원칙 |
|---|---|
| DP-1 | 무결성의 최종 방어선은 DB 제약이다. 애플리케이션 검증은 UX용이다 |
| DP-2 | 한 행 안에서 결정되는 파생값은 생성 컬럼으로 둔다 |
| DP-3 | 업무 날짜는 예외 없이 KST 캘린더 기준이며 애플리케이션이 계산해 주입한다 |
| DP-4 | 되돌리기 어려운 조작과 부수효과는 이력 행을 남긴다 |
| DP-5 | 개인정보는 최소로 수집하고 즉시 파기한다 |
| DP-6 | 운영 중 조정될 값은 컬럼이 아니라 설정 행으로 둔다 |

---

## 2. 공통 규약

**명명** — 테이블 단수형 `snake_case`(예약어 충돌 시 접두), 컬럼 `snake_case`(`is_`/`has_`, `_at`, `_on`/`_date`, `_count`), PK는 `id`, FK는 `{테이블}_id`. 제약·인덱스 접두: `ix_` `uq_` `ck_` `fk_` `ex_`.

**타입** — PK는 애플리케이션 생성 UUIDv7. 열거형은 `text` + `CHECK`(네이티브 ENUM 미사용). 시각은 `timestamptz`(UTC 저장), 업무일은 `date`. 문자열은 전부 `varchar(n)`(무제한 `text` 금지). 구조화 설정만 `jsonb`.

**믹스인** — `UUIDPKMixin`(`id`) · `TimestampMixin`(`created_at`, `updated_at`) · `VersionMixin`(`version`, 낙관적 잠금 → 충돌 시 `409 CONFLICT_VERSION`). `updated_at`은 ORM `onupdate`로 갱신한다.

**시간대** — DB 세션 TZ는 UTC 고정. SQL 안에서 `CURRENT_DATE`를 쓰지 않는다(Lambda TZ가 UTC라 KST 09:00 이전에 하루 어긋난다). KST는 `zoneinfo`로 다룬다.

**삭제 정책** — 하드 삭제(회원 탈퇴·보존기간 만료 로그·만료 구독), 숨김 플래그(`exhibition.is_hidden`), 익명화(열람 로그의 `user_id`→NULL). 소프트 삭제(`deleted_at`) 패턴은 채택하지 않는다.

---

## 3. 개체 관계

```
app_user ─┬─< view_log >─ exhibition
          ├─< artwork_view_log >─ artwork ─< exhibition
          ├─< push_subscription
          ├─< social_identity
          ├─< notification_log
          ├─< audit_log
          ├─< exhibition (created_by)
          └─< notice (created_by)

app_setting · auth_throttle — 독립 테이블
```

### 3.1 참조 무결성

전 FK에 `ON DELETE`를 명시한다. 기본값(`NO ACTION`)에 의존하지 않는다.

| 자식 → 부모 | ON DELETE | 근거 |
|---|---|---|
| `artwork.exhibition_id` → `exhibition` | `CASCADE` | 전시 없는 그림은 의미가 없다 |
| `artwork_view_log.artwork_id` → `artwork` | `CASCADE` | 그림 교체 시 그 열람 기록은 의미를 잃는다 |
| `artwork_view_log.exhibition_id` → `exhibition` | `CASCADE` | 집계 기준 비정규화 컬럼 |
| `push_subscription.user_id` → `app_user` | `CASCADE` | 개인정보성 자원, 즉시 파기 |
| `social_identity.user_id` → `app_user` | `CASCADE` | 회원이 사라지면 외부 계정 연결도 의미가 없다 |
| `view_log.user_id` → `app_user` | `SET NULL` | 집계 형태는 남기고 식별만 끊는다 |
| `view_log.exhibition_id` → `exhibition` | `SET NULL` | 방어적 |
| `artwork_view_log.user_id` → `app_user` | `SET NULL` | 동상 |
| `notification_log.user_id` / `.exhibition_id` | `SET NULL` | 발송 이력의 형태는 보존 |
| `audit_log.actor_id` → `app_user` | `SET NULL` | 조작 기록의 형태는 보존 |
| `exhibition.created_by` · `notice.created_by` · `app_setting.updated_by` → `app_user` | `SET NULL` | 작성자 소실이 본문을 지우면 안 된다 |

**ORM 규약** — 모든 관계에 `passive_deletes=True`를 지정해 삭제 동작을 DB에 위임한다. 지정하지 않으면 SQLAlchemy가 부모 삭제 시 자식을 먼저 로드해 `SET NULL` UPDATE를 시도하여 DB 정의와 어긋난다. 부모 없이는 존재할 수 없는 컬렉션(`exhibition.artworks`)에만 `cascade="all, delete-orphan"`을 함께 둔다. **애플리케이션이 자식 행을 루프로 지우지 않는다.**

---

## 4. 테이블

각 테이블의 컬럼 세부(길이·기본값)는 구현 시 확정한다. 여기서는 **역할·키·제약**만 정한다.

### 4.1 `app_user` — 회원
관람자·큐레이터를 `role`로 구분하는 단일 테이블. 큐레이터는 시드로 1건만 생성한다.

- 신원·인증: `phone`(로그인 ID, 하이픈 없는 숫자), `password_hash`(bcrypt, **NULL 허용** — 소셜로만 가입한 회원은 비밀번호가 없다), `name`, `role`, `token_version`(JWT 무효화 카운터), `must_change_password`, `last_login_at`
- 설정: `notify_enabled`, `notify_at`(끄더라도 값 보존), `font_scale`
- 운영: `is_blocked`, `blocked_at`, `blocked_reason`, `created_via`
- 제약: `uq_app_user_phone` · `uq_app_user_single_curator`(`role='curator'` 부분 유니크) · `role`/`font_scale`/`created_via`/`phone` 형식 CHECK
- 인덱스: 알림 대상 조회용 부분 인덱스, 가입일 정렬, 이름 부분 검색(`pg_trgm`)
- 규칙: 차단은 기존 세션을 끊지 않는다(로그인 시점에만 작동)
- 규칙: **`phone`은 소셜 가입에서도 필수다.** 아침 알림 타겟팅·대행 가입·차단·회원 관리가 전부 전화번호에 걸려 있어, 전화번호 없는 회원은 운영 화면에서 다룰 수 없다(소셜 문서 SA-2)

### 4.2 `auth_throttle` — 인증 시도 제한
Lambda는 인스턴스 메모리를 신뢰할 수 없으므로 시도 상태를 DB에 둔다.

- `throttle_key`(= `{scope}:{식별자}`, UNIQUE), `scope`, `fail_count`, `first_failed_at`, `last_failed_at`, `locked_until`
- 규칙: 실패는 UPSERT로 원자적 증가, 성공 시 행 삭제. 임계 초과 시 `locked_until` 설정

### 4.3 `push_subscription` — 웹 푸시 구독
한 회원이 여러 단말을 구독할 수 있어 1:N.

- `user_id`, `endpoint`, `endpoint_hash`(UNIQUE — 엔드포인트가 인덱스 상한을 넘길 수 있다), `p256dh`, `auth`, `platform`, `is_active`, `failure_count`
- 규칙: 같은 엔드포인트가 다른 회원으로 재등록되면 소유자를 갱신. 푸시 404/410이면 즉시 비활성, 5xx는 연속 실패 누적 후 비활성

### 4.4 `social_identity` — 외부 계정 연결
한 회원이 여러 제공자를 연결할 수 있어 1:N. **소셜은 로그인 수단이지 신원이 아니다**(소셜 문서 SA-2).

- `user_id`, `provider`, `provider_uid`, `email`(선택 동의라 비어 올 수 있다), `display_name`, `linked_at`, `last_login_at`
- 제약: `uq_social_identity_provider_uid`(`provider`, `provider_uid` 복합 UNIQUE) · `provider` 값 CHECK
- 인덱스: `user_id`(연결 목록 조회)
- 규칙: **이메일로 계정을 병합하지 않는다.** 제공자가 이메일 소유를 검증하지 않으면 계정 탈취 경로가 된다. 신원은 `(provider, provider_uid)` 하나뿐이다
- 규칙: 비밀번호가 없는 회원의 **마지막 연결은 해제할 수 없다** — 해제하면 로그인 수단이 0이 되어 영구 잠금이다

### 4.5 `exhibition` — 전시(하루 단위)
**드래프트와 발행본이 같은 행이다.** 별도 draft 테이블을 두지 않는다.

- 식별: `exhibition_date`(발행일, UNIQUE — 하루 하나)
- 본문: `title`, `theme`(드래프트 단계에서는 NULL 허용)
- 상태: `is_published`(단방향), `published_at`, `is_hidden`, `hidden_at`, `hidden_reason`, `draft_updated_at`
- 파생 카운터: `artwork_count`, `complete_artwork_count`(그림 변경과 같은 트랜잭션에서 재계산 UPDATE)
- 제약: 카운터 범위 CHECK, `is_published`↔`published_at` 정합 CHECK, `is_hidden`↔`hidden_at` 정합 CHECK
- 인덱스: 관람자 질의 전용 부분 인덱스(`is_published AND NOT is_hidden`, 날짜 역순) — 모든 관람 트래픽이 이 하나를 탄다
- 발행 조건: 제목·테마·완성 그림 12점. **서비스 계층에서만 판정하며 DB 트리거를 쓰지 않는다**(발행은 알림을 유발하는 도메인 이벤트다)

### 4.6 `artwork` — 그림
- 소속·순서: `exhibition_id`, `position`(1–12, `(exhibition_id, position)` UNIQUE, 범위 CHECK)
- 본문: `title`, `artist`, `year_text`, `description`, `collection`, `source_url`(https CHECK)
- 이미지: `image_status`, 키 3종(원본·디스플레이·썸네일), `image_lqip`, `image_width/height`, `image_bytes`, `image_mime`, `image_error_code`, `image_uploaded_at`, `image_ready_at`
- 생성 컬럼 `is_complete` — 본문 4종이 채워지고 `image_status='ready'`일 때 참. `STORED GENERATED`로 두어 완성 판정이 코드에 흩어지지 않게 한다
- 제약: `ready`면 이미지 키가 존재해야 한다
- 순서 변경: 슬롯 유니크를 `DEFERRABLE`로 선언하고 트랜잭션 안에서 일괄 재할당한다. 임시 오프셋 트릭을 쓰지 않는다

### 4.7 `view_log` — 갤러리 입장 기록
**관람일 기준 하루 1행**이 전부다.

- `user_id`, `viewed_on`(관람일 KST), `exhibition_id`(그날 실제로 걸린 전시), `first_entered_at`, `last_entered_at`, `entry_count`(진단용, 지표 미사용), `is_anonymized`
- 제약: `(user_id, viewed_on)` UNIQUE
- 규칙: 진입 시 UPSERT. 충돌 시 `exhibition_id`는 갱신하지 않는다(그날 처음 연 전시가 대표값). 아카이브 진입도 같은 입장으로 센다
- 두지 않는 컬럼: 오늘/아카이브 구분, `session_id`, `ip`, `user_agent` (DP-5)

### 4.8 `artwork_view_log` — 그림 열람 기록
**(회원, 그림) 조합당 1행.** 중복 제거 집계를 제약으로 표현한다.

- `user_id`, `artwork_id`, `exhibition_id`(비정규화), `first_viewed_on`, `first_viewed_at`, `last_viewed_at`, `view_count`, `is_anonymized`
- 제약: `(user_id, artwork_id)` UNIQUE
- 활용: 갤러리 그리드의 "열어봄" 표식은 **전시 기준**으로 조회한다

### 4.9 `notice` — 휴관 공지
- `starts_on`, `ends_on`, `body`, `is_active`, `created_by`
- 제약: 기간 순서 CHECK, **활성 공지 기간 중첩 금지 EXCLUDE**(`btree_gist`). 겹침을 허용하면 "오늘의 공지"가 비결정적이 된다
- 활용: 공지 기간은 발행 빈도 지표의 분모와 큐레이터 연장 알림에서 제외된다

### 4.10 `app_setting` — 전역 설정
키-값 단일 테이블. 설정마다 컬럼을 늘리지 않는다.

- `key`(PK), `value`(jsonb), `value_type`, `description`, `is_mutable`, `updated_by`
- 시드 키: `signup_open` · `notify_default_time` · `notify_cutoff_hour` · `carryover_alert_days` · `archive_size` · `admin_calendar_days` · `log_retention_days` · `media_url_ttl_seconds` · `maintenance_mode` · `session_ttl_days`
- **배포로만 바뀌는 값은 환경변수, 운영 중 조정되는 값은 이 테이블**이다. 이 구분을 흐리지 않는다

### 4.11 `notification_log` — 알림 발송 이력
중복 발송 방지와 사후 추적을 함께 담당한다.

- `user_id`, `kind`, `dedupe_key`(UNIQUE), `exhibition_id`, `status`, `skip_reason`, `scheduled_for`, `sent_at`, `attempt_count`, `last_error`, `payload`(발송 시점 스냅샷)
- 규칙: `dedupe_key` UNIQUE가 "하루 1회"와 "연장 기간당 1회"를 DB 수준에서 보장한다. **발송하지 않기로 한 경우에도 `skipped` 행을 남긴다** — 보내지 않은 이유가 남아야 문의에 답할 수 있다

### 4.12 `audit_log` — 관리자 조작 이력
- `actor_id`, `actor_role`(시점 스냅샷), `action`, `target_type`, `target_id`, `summary`, `changes`(before/after), `request_id`
- 규칙: 비밀번호 해시·전화번호 전체를 담지 않는다

---

## 5. 열거형

애플리케이션의 열거형 모듈이 단일 진실 원천이고 프런트엔드가 이를 미러링한다.

| 열거형 | 값 |
|---|---|
| `UserRole` | `viewer`, `curator` |
| `FontScale` | `normal`, `large` |
| `CreatedVia` | `self`, `curator`, `social` |
| `ImageStatus` | `empty`, `uploading`, `ready`, `failed` |
| `ExhibitionDayStatus` | `published`, `carried_over`, `empty` (컬럼 아님 — 달력 응답의 파생값) |
| `NotificationKind` | `morning_exhibition`, `late_publish`, `curator_carryover`, `curator_signup` |
| `NotificationStatus` | `pending`, `sent`, `skipped`, `failed` |
| `ThrottleScope` | `login`, `signup`, `password_reset`, `upload_url` |
| `PushPlatform` | `ios`, `android`, `desktop`, `unknown` |
| `SocialProvider` | `kakao`, `google` |

---

## 6. 상태 전이

**전시** — 없음 → 드래프트(편집 진입 시 행 생성) → 발행됨 → 숨김 ⇄ 발행됨.
불변식: ① `is_published`는 단조 증가한다 ② 발행 전환은 저장 트랜잭션 안에서만 일어나고 동시에 알림 행이 등록된다 ③ 미래 날짜 발행본은 존재할 수 있으며 관람자 질의가 날짜로 걸러낸다 ④ 과거 날짜 신규 발행(백필)은 서비스 계층에서 거부한다(제약으로는 표현 불가).

**이미지** — `empty` → `uploading`(업로드 URL 발급) → `ready` | `failed`(업로드 완료 통지 시 동기 변환). 재업로드하면 `uploading`으로 되돌아간다. `ready`가 아니면 `is_complete`가 거짓이므로 **처리되지 않은 그림은 발행 카운트에 잡히지 않는다.**

**알림** — `pending` → `sent` | `skipped` | `failed`. 아침 알림은 시의성이 전부이므로 당일 컷오프를 넘기면 재시도하지 않고 `skipped`로 종료한다.

---

## 7. 질의 규약

모든 업무 날짜는 애플리케이션이 계산해 파라미터로 주입한다. 질의는 원칙적으로 **공용 DB 헬퍼**(백엔드 문서 §4)로 작성하고, 헬퍼로 표현되지 않는 것만 명명된 전용 질의 모듈에 격리한다.

전용 질의가 필요한 것은 현재 셋뿐이다.

| 질의 | 이유 |
|---|---|
| 관리자 달력 | 날짜 시리즈 각각에 대해 "그날 걸린 전시"를 1건씩 끌어오는 측면 조인. 날짜별 반복 질의(N+1)를 금지한다 |
| 회원 목록 | 회원 행마다 마지막 입장일·푸시 상태를 결합. 파생 필드 정렬 시 계산이 페이징보다 앞선다 |
| 통계 집계 | 기간별 그룹 집계 |

**N+1을 만드는 코드는 리뷰에서 반려한다.** 헬퍼의 관계 로딩 옵션을 쓰거나 전용 질의로 옮긴다.

---

## 8. 무결성 분담

**DB가 보장** — 하루 1전시 · 슬롯 중복 없음 · 슬롯 번호 범위 · 관람일당 입장 1행 · (회원,그림)당 열람 1행 · 알림 중복 없음 · 공지 기간 중첩 없음 · 큐레이터 유일 · 발행 상태 정합 · `ready` 이미지 키 존재 · 완성 판정 단일 정의.

**애플리케이션이 보장** — 발행 단방향 · 백필 금지 · 이어쓰기 대상 중복 검사 · 카운터 재계산 · 가입 잠금 · 차단 회원 로그인 거부(사실 은닉) · 글자수 상한(스키마 + `varchar` 이중).

**삭제 제한** — 발행된 전시는 삭제하지 않는다(유일한 철회 수단은 숨김이며 API에 삭제 엔드포인트를 두지 않는다). 드래프트는 그림이 0개일 때만 삭제 가능하다. 그림 삭제 시 S3 오브젝트는 즉시 지우지 않고 정리 배치가 회수한다.

---

## 9. 마이그레이션

**Alembic이 유일한 스키마 변경 수단이다.** `backend/migrations/`에 두고 배포 패키지에서 제외하며, 배포 파이프라인의 독립 단계에서 `alembic upgrade head`로 실행한다. 애플리케이션 기동 시 자동 실행하지 않는다(Lambda 동시 실행이 곧 동시 마이그레이션이 된다).

| 항목 | 규약 |
|---|---|
| 히스토리 | 단일 선형. 브랜치 미사용. `down_revision` 항상 명시, `downgrade()` 반드시 구현 |
| 파일명 | `{순번4자리}_{동사}_{대상}.py` |
| 자동 생성 | `--autogenerate` 결과를 그대로 쓰지 않는다. 부분 인덱스·EXCLUDE·생성 컬럼은 감지되지 않으므로 수기 보정한다 |
| 확장 | 최초 리비전에서 `pg_trgm`, `btree_gist` 생성 |
| 파괴적 변경 | 2단계로 나눈다(추가+이중 쓰기 → 다음 릴리스에서 제거) |
| `NOT NULL` 추가 | 기본값 포함 컬럼 추가 → 백필 → 제약 추가 |
| 인덱스 | 운영 데이터가 쌓인 뒤에는 `CONCURRENTLY`. 해당 리비전은 트랜잭션 밖에서 실행 |
| 검증 | 스테이징에 프로덕션 스냅샷 복원본으로 먼저 적용 |

**시드** — 큐레이터 계정 1건(환경변수 기반, `must_change_password=true`)과 `app_setting` 전량을 멱등하게 삽입한다. 시드용 환경변수가 없으면 마이그레이션은 실패한다 — 큐레이터 없는 배포는 동작 불가 상태다.

---

## 10. 보존·파기

| 데이터 | 보존 | 방식 |
|---|---|---|
| `exhibition`, `artwork`, S3 원본 | 영구 | — |
| `view_log`, `artwork_view_log` | 180일 | 야간 배치 하드 삭제 |
| `notification_log` | 90일 | 야간 배치 |
| `audit_log` | 365일 | 야간 배치 |
| `auth_throttle`(비활성) | 24시간 | 야간 배치 |
| `push_subscription`(비활성) | 30일 | 야간 배치 |
| 미참조 S3 오브젝트 | 7일 | 야간 배치 |
| 탈퇴 회원 | 즉시 | 하드 삭제 + 로그 익명화 |

**탈퇴 트랜잭션** — 열람 로그를 익명화하고, 구독·알림·시도 제한 행을 삭제하고, 회원 행을 삭제한다. 감사 로그에는 `member.withdraw` 1건을 남기되 **actor·target·본문 어디에도 탈퇴자를 식별할 값을 남기지 않는다.** 익명화된 로그는 전 지표의 분모·분자에서 제외된다.

**백업** — RDS 자동 백업 + PITR. 마이그레이션을 포함한 배포 직전에는 수동 스냅샷 1회. S3는 버전 관리 활성화.

---

## 11. 확장 훅

MVP에서 **만들지 않되** 나중의 스키마 변경이 국소적이 되도록 지점만 확정한다.

| 기능 | 변경 범위 |
|---|---|
| SMS 비밀번호 재설정 | 신규 테이블 1개. 기존 무영향 |
| 소셜 제공자 추가(네이버·애플 등) | 스키마 무변경. `SocialProvider` CHECK에 값 추가 + 서술자 1개 |
| 예약 발행(시각 지정) | `exhibition`에 시각 컬럼 추가 + 관람자 질의 조건·인덱스 확장 |
| 통계 롤업 테이블 | 회원 100명 규모에서는 불필요. 실시간 집계로 충분하며 규모가 커지면 도입 |
| 즉시 차단(세션 무효화) | 스키마 변경 없음. `token_version` 증가로 구현 |
| 다중 큐레이터 | 큐레이터 유일 제약 제거만으로 열린다 |
