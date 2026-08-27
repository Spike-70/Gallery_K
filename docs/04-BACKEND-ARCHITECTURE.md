# 갤러리 K — 백엔드 아키텍처 설계서

| | |
|---|---|
| **문서 버전** | v1.0 |
| **작성일** | 2026-08-27 |
| **상위 문서** | `docs/PRD.md` v1.1, `01-DATABASE-MODEL.md`, `02-API-SPEC.md` |
| **런타임** | Python 3.12 · AWS Chalice 1.33 · Lambda(ARM64) · API Gateway REST |
| **데이터** | AWS RDS for PostgreSQL 16 · SQLModel + SQLAlchemy 2.x · Alembic |
| **상태** | 확정 (구현 기준선) |

---

## 1. 설계 원칙

| # | 원칙 | 적용 |
|---|---|---|
| **BA-1** | **계층 단방향** | `api → service → repository → model`. 역방향 참조와 계층 건너뛰기를 금지하고 정적 검사로 강제한다 |
| **BA-2** | **라우트는 얇게** | 라우트 함수는 (입력 파싱 → 서비스 호출 → 응답 조립) 3줄 구조를 넘지 않는다. 비즈니스 분기가 라우트에 들어가는 순간 테스트 불가능해진다 |
| **BA-3** | **도메인 규칙은 서비스에 하나씩만** | 백필 금지·발행 조건·연장 판정 같은 규칙은 정확히 한 곳에 존재한다. API 문서 §3.9에서 `edit_mode`를 서버가 결정하는 이유가 이것이다 |
| **BA-4** | **횡단 관심사는 미들웨어와 데코레이터로** | 인증·트랜잭션·로깅·오류 변환을 각 핸들러가 반복하지 않는다 |
| **BA-5** | **Chalice에 종속되는 코드를 최소화한다** | 프레임워크 객체(`app.current_request`)는 어댑터 계층에서만 만진다. 서비스는 순수 Python이며 프레임워크 없이 테스트된다 |
| **BA-6** | **서버리스 제약을 설계 전제로 삼는다** | 콜드 스타트·6MB 페이로드·15분 타임아웃·커넥션 고갈은 나중에 최적화할 문제가 아니라 구조를 결정하는 조건이다 |
| **BA-7** | **모든 부수효과는 이력을 남긴다** | 알림·관리자 조작·이미지 처리는 결과 행을 남긴다(DB 문서 DP-4) |

---

## 2. 시스템 구성

### 2.1 구성 요소

| 구성 요소 | 역할 | 비고 |
|---|---|---|
| CloudFront | 단일 진입점. `/` → S3(프런트 정적), `/api/*` → API Gateway, `/media/*` → S3(이미지, 서명 접근) | 동일 오리진이므로 CORS·SameSite 문제가 없다(API 문서 §2.11) |
| S3 `web` | 프런트 빌드 산출물 | OAC로 CloudFront만 접근 |
| S3 `media` | 원본·디스플레이·썸네일 이미지 | **비공개.** `/media/artworks/*`는 서명 필수, `/media/public/*`(정문 OG 이미지)만 공개 |
| API Gateway (REST) | Lambda 프록시 | 스로틀·요청 크기 제한 |
| Lambda `api` | Chalice 앱 본체 | ARM64, 메모리 1024MB, 타임아웃 29초 |
| Lambda `image-worker` | 이미지 리사이즈 | ARM64, 메모리 2048MB, 타임아웃 120초, Pillow 레이어 |
| Lambda `scheduler` | 알림·배치 | ARM64, 메모리 512MB, 타임아웃 300초 |
| RDS PostgreSQL | 주 데이터 저장소 | 단일 AZ(MVP) → Multi-AZ(확대 시) |
| RDS Proxy | 커넥션 풀링 | Lambda 동시성 대비 필수 |
| EventBridge Scheduler | 알림 5분 주기, 야간 배치 | |
| Secrets Manager | DB 자격증명, JWT 시크릿, VAPID 키, CloudFront 키페어 | |
| CloudWatch Logs / Alarms | 구조화 로그·경보 | |

### 2.2 Lambda 분리 근거

한 Lambda에 모두 담지 않는 이유는 **자원 프로필과 실패 격리**가 다르기 때문이다.

| 함수 | 메모리 | 이유 |
|---|---|---|
| `api` | 1024MB | 응답 지연이 UX다. Pillow를 담지 않아 패키지가 작고 콜드 스타트가 짧다 |
| `image-worker` | 2048MB | 20MB 이미지 디코딩·리사이즈는 메모리와 CPU가 필요하다. 이 함수가 느려도 API는 영향받지 않는다 |
| `scheduler` | 512MB | 배치·알림. 실패해도 관람 경험에 즉시 영향이 없다 |

Chalice는 `app.py` 하나에서 `@app.route`, `@app.on_s3_event`, `@app.schedule`를 모두 선언하면 **동일 배포 패키지의 서로 다른 Lambda**로 생성한다. 패키지 분리를 위해 무거운 의존성(Pillow)은 Lambda Layer로 빼고 `image-worker`에만 부착한다.

### 2.3 네트워크

- Lambda는 **VPC 안**에 둔다(RDS 접근). 프라이빗 서브넷 + NAT 게이트웨이 대신 **VPC 엔드포인트**(S3 Gateway, Secrets Manager Interface)를 사용해 NAT 비용을 제거한다.
- 웹 푸시(외부 HTTPS)가 필요한 `scheduler`만 NAT를 경유한다. 비용을 감안해 NAT Gateway 대신 **NAT 인스턴스(t4g.nano)** 또는 푸시 발송을 VPC 밖 Lambda로 분리하는 선택지를 둔다. **MVP 결정: `scheduler`를 VPC 밖에 두지 않고 NAT 인스턴스를 사용한다** — DB 접근이 필요하기 때문이다.

---

## 3. 디렉터리 구조

```
backend/
├── app.py                          # Chalice 진입점. 블루프린트 등록 + 이벤트 핸들러 선언만
├── requirements.txt                # 런타임 의존성
├── requirements-dev.txt            # 테스트·린트 의존성
├── .chalice/
│   ├── config.json                 # 스테이지별 환경변수·Lambda 설정
│   └── policy-prod.json            # 최소 권한 IAM 정책(자동 생성 비활성화)
├── migrations/                     # Alembic. 배포 패키지에서 제외
│   ├── env.py
│   └── versions/
│       ├── 0001_initial_schema.py
│       └── 0002_seed_settings_and_curator.py
├── chalicelib/
│   ├── __init__.py
│   ├── config/
│   │   ├── settings.py             # 환경변수 → 설정 객체(pydantic-settings). 단일 진실 원천
│   │   ├── constants.py            # 도메인 상수(ARTWORK_SLOT_COUNT=12 등)
│   │   └── secrets.py              # Secrets Manager 조회 + 프로세스 캐시
│   ├── core/
│   │   ├── envelope.py             # 표준 응답 봉투 생성기(API 문서 §2.2)
│   │   ├── errors.py               # AppError 계층 + 오류 코드 레지스트리(§5 카탈로그)
│   │   ├── error_handler.py        # 예외 → HTTP 응답 매핑
│   │   ├── context.py              # RequestContext (request_id, actor, now, today_kst)
│   │   ├── middleware.py           # 미들웨어 체인 조립
│   │   ├── security.py             # JWT 발급·검증, bcrypt, 쿠키 직렬화
│   │   ├── permissions.py          # 권한 등급 판정(PUBLIC/MEMBER/CURATOR)
│   │   ├── validation.py           # 요청 바디·쿼리 파싱 및 검증 어댑터
│   │   ├── pagination.py           # cursor/page 공용 처리 + 커서 인코딩
│   │   ├── query_params.py         # 필터·정렬 화이트리스트 파서(API 문서 §2.6)
│   │   ├── throttle.py             # auth_throttle 기반 시도 제한
│   │   ├── etag.py                 # ETag 생성·조건부 응답
│   │   ├── logging.py              # 구조화 JSON 로거
│   │   └── timeutil.py             # KST 헬퍼(now_kst, today_kst, to_utc)
│   ├── db/
│   │   ├── engine.py               # 엔진·세션팩토리(전역 1회 생성)
│   │   ├── session.py              # 요청 스코프 세션·트랜잭션 컨텍스트
│   │   ├── base.py                 # SQLModel 베이스 + 믹스인(UUIDPk, Timestamp, Version)
│   │   ├── types.py                # UUIDv7 생성기, 커스텀 타입
│   │   ├── models/
│   │   │   ├── __init__.py         # 전 모델 재수출(Alembic 메타데이터 수집용)
│   │   │   ├── enums.py            # 열거형 단일 정의(DB 문서 §5)
│   │   │   ├── user.py             # AppUser
│   │   │   ├── exhibition.py       # Exhibition
│   │   │   ├── artwork.py          # Artwork
│   │   │   ├── view_log.py         # ViewLog, ArtworkViewLog
│   │   │   ├── notice.py           # Notice
│   │   │   ├── setting.py          # AppSetting
│   │   │   ├── push.py             # PushSubscription
│   │   │   ├── notification.py     # NotificationLog
│   │   │   ├── audit.py            # AuditLog
│   │   │   └── throttle.py         # AuthThrottle
│   │   └── repositories/
│   │       ├── base.py             # 공통 CRUD·페이지네이션 헬퍼
│   │       ├── user_repo.py
│   │       ├── exhibition_repo.py  # 현재 전시·달력·아카이브 질의
│   │       ├── artwork_repo.py
│   │       ├── view_log_repo.py    # UPSERT 기록, 통계 집계
│   │       ├── notice_repo.py
│   │       ├── setting_repo.py
│   │       ├── push_repo.py
│   │       ├── notification_repo.py
│   │       ├── audit_repo.py
│   │       └── throttle_repo.py
│   ├── schemas/                    # 요청·응답 DTO (pydantic v2). API 계약의 코드 표현
│   │   ├── common.py               # Envelope, Meta, Pagination, FieldError
│   │   ├── auth.py
│   │   ├── exhibition.py           # ExhibitionDetail, ExhibitionSummary
│   │   ├── artwork.py              # ArtworkSummary, ArtworkDetail, ImageSet
│   │   ├── me.py
│   │   ├── notice.py
│   │   ├── admin_exhibition.py     # AdminExhibitionDay, AdminArtworkSlot
│   │   ├── admin_member.py
│   │   ├── admin_setting.py
│   │   ├── admin_stats.py
│   │   └── upload.py
│   ├── services/
│   │   ├── auth_service.py         # 가입·로그인·세션·비밀번호
│   │   ├── session_service.py      # 세션 조회·슬라이딩 갱신
│   │   ├── exhibition_service.py   # 현재 전시·연장 판정·발행 규칙·숨김
│   │   ├── exhibition_admin_service.py # 달력·드래프트·이어쓰기·edit_mode
│   │   ├── artwork_service.py      # 슬롯 CRUD·순서 변경·완성도
│   │   ├── archive_service.py      # 아카이브 목록
│   │   ├── view_log_service.py     # 입장·열람 기록
│   │   ├── member_service.py       # 회원 목록·대행가입·차단·초기화
│   │   ├── notice_service.py
│   │   ├── setting_service.py      # 전역 설정 조회·변경 + 캐시
│   │   ├── stats_service.py        # 요약·일별·회원별 통계
│   │   ├── media_service.py        # 서명 쿠키·URL 조립
│   │   ├── upload_service.py       # Presigned URL 발급·완료 처리
│   │   ├── image_service.py        # 리사이즈 파이프라인 도메인 로직
│   │   ├── notification_service.py # 알림 큐 생성·발송·스킵 판정
│   │   └── audit_service.py
│   ├── integrations/               # 외부 시스템 어댑터. 여기서만 boto3를 import한다
│   │   ├── s3_client.py
│   │   ├── cloudfront_signer.py
│   │   ├── webpush_client.py
│   │   ├── sms_client.py           # v1.1. MVP는 NullSmsClient
│   │   └── image_processor.py      # Pillow 래퍼(리사이즈·WebP·LQIP)
│   ├── api/
│   │   ├── __init__.py             # 전 블루프린트 수집
│   │   ├── deps.py                 # 라우트용 의존성 헬퍼(현재 사용자, 서비스 팩토리)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── public.py           # /public/*
│   │       ├── auth.py             # /auth/*
│   │       ├── media.py            # /media/session
│   │       ├── exhibitions.py      # /exhibitions/*
│   │       ├── artworks.py         # /artworks/*
│   │       ├── me.py               # /me/*
│   │       ├── system.py           # /system/health
│   │       └── admin/
│   │           ├── __init__.py
│   │           ├── summary.py
│   │           ├── exhibitions.py
│   │           ├── artworks.py
│   │           ├── members.py
│   │           ├── notices.py
│   │           ├── settings.py
│   │           └── stats.py
│   ├── jobs/
│   │   ├── image_pipeline.py       # S3 이벤트 핸들러
│   │   ├── notify_dispatcher.py    # 5분 주기 알림 발송
│   │   ├── carryover_alert.py      # 연장 2일 큐레이터 알림
│   │   ├── retention_cleanup.py    # 보존기간 만료 삭제
│   │   ├── consistency_check.py    # 카운터 정합성
│   │   ├── stuck_upload_sweeper.py
│   │   ├── orphan_object_cleanup.py
│   │   └── push_subscription_prune.py
│   └── utils/
│       ├── phone.py                # 전화번호 정규화·마스킹
│       ├── text.py                 # 공백 정규화·길이 검증 보조
│       ├── dates.py                # 날짜 라벨 포맷(2026. 08. 27. 목)
│       └── ids.py                  # UUIDv7, ULID(request_id)
└── tests/
    ├── conftest.py                 # DB 픽스처(트랜잭션 롤백), 팩토리
    ├── factories/
    ├── unit/                       # 서비스·도메인 규칙
    ├── integration/                # 리포지토리 + 실제 PostgreSQL
    ├── api/                        # Chalice 테스트 클라이언트로 계약 검증
    └── jobs/
```

### 3.1 모듈 배치 규칙

| 질문 | 배치 |
|---|---|
| DB 테이블에 대응하는가? | `db/models/` |
| SQL을 직접 작성하는가? | `db/repositories/` |
| 여러 리포지토리를 조합해 규칙을 적용하는가? | `services/` |
| HTTP 요청·응답 모양을 아는가? | `schemas/` 또는 `api/` |
| AWS SDK·외부 HTTP를 호출하는가? | `integrations/` |
| 요청과 무관하게 주기적으로 도는가? | `jobs/` |
| 도메인과 무관한 순수 함수인가? | `utils/` |
| 모든 요청이 거치는가? | `core/` |

**모듈을 어디에 둘지 애매하면 그 모듈은 책임이 두 개다.** 나누고 다시 판단한다.

---

## 4. 계층 아키텍처

### 4.1 의존 방향

```
app.py
  └─ api/v1/*            (Chalice Blueprint · 얇음)
       ├─ schemas/*      (DTO)
       └─ services/*     (도메인 규칙)
            ├─ db/repositories/*
            │    └─ db/models/*
            ├─ integrations/*
            └─ core/*    (전 계층에서 참조 가능)
```

| 규칙 | 강제 방법 |
|---|---|
| `services`는 `chalice`를 import 하지 않는다 | `import-linter` 계약 |
| `services`는 `api`·`schemas`를 import 하지 않는다 | 동일 |
| `repositories`는 `services`를 import 하지 않는다 | 동일 |
| `api`는 `db.models`를 직접 import 하지 않는다 | 동일 |
| `integrations`는 `db`를 import 하지 않는다 | 동일 |
| `core`는 어떤 상위 계층도 import 하지 않는다 | 동일 |

CI에서 `import-linter`가 계약 위반 시 빌드를 실패시킨다. **아키텍처 규칙은 문서가 아니라 테스트로 존재해야 유지된다.**

### 4.2 계층별 책임

| 계층 | 하는 일 | 하지 않는 일 |
|---|---|---|
| `api/v1` | 경로 선언, 입력 스키마 바인딩, 서비스 호출, 응답 DTO → 봉투 | 조건 분기, DB 접근, 권한 판정 로직 작성(데코레이터 사용은 함) |
| `schemas` | 필드·제약 선언, 직렬화 | DB 조회, 계산 |
| `services` | 도메인 규칙, 트랜잭션 경계 정의, 여러 리포지토리 조합, 도메인 이벤트 발행 | HTTP 상태 코드 결정, SQL 작성 |
| `repositories` | 질의·저장, 페이지네이션 실행 | 규칙 판정, 권한 확인 |
| `models` | 테이블 구조, 제약 | 비즈니스 메서드 |
| `integrations` | 외부 호출, 재시도, 예외 변환 | 도메인 판단 |

### 4.3 DTO 변환 경계

**모델 객체는 서비스 밖으로 나가지 않는다.** 서비스는 `schemas`의 응답 DTO를 반환한다. 이유:

1. 라우트가 실수로 `password_hash`를 직렬화할 여지를 없앤다.
2. 지연 로딩된 관계가 세션 종료 후 접근되는 사고를 차단한다.
3. API 계약이 DB 스키마 변경에 자동으로 끌려가지 않는다.

변환은 서비스 내 전용 매퍼 함수(`_to_exhibition_detail` 등)에 모으고, 매퍼는 그 서비스 파일 하단에 둔다.

---

## 5. 요청 처리 파이프라인

Chalice HTTP 미들웨어를 순서대로 조립한다. 바깥에서 안쪽으로:

| # | 미들웨어 | 책임 | 실패 시 |
|---|---|---|---|
| 1 | `request_context` | `request_id`(ULID) 생성, 시작 시각·KST 오늘 계산, 컨텍스트 변수 설정 | — |
| 2 | `access_log` | 시작·종료 구조화 로그, 소요 시간 기록 | — |
| 3 | `error_boundary` | 모든 예외를 잡아 표준 봉투로 변환 | 미분류 예외는 `SYSTEM_INTERNAL` + 스택은 로그에만 |
| 4 | `maintenance_gate` | `maintenance_mode`면 `/public/*`·`/system/*` 외 차단 | `503 MAINTENANCE_MODE` |
| 5 | `csrf_guard` | 변경 메서드에 `X-Requested-With` 확인 | `403 CSRF_HEADER_MISSING` |
| 6 | `db_session` | 요청 스코프 세션을 **지연 생성**으로 등록. 첫 사용 시점에 커넥션을 얻고, 정상 종료 시 commit, 예외 시 rollback, 항상 close | |
| 7 | `authentication` | 세션 쿠키 파싱·JWT 검증·`token_version` 대조·슬라이딩 갱신 | `401` 계열 |
| 8 | `response_finalize` | 봉투의 `meta` 채우기, 캐시 헤더·`Set-Cookie` 부착 | |

**순서의 근거** — 오류 경계가 인증보다 바깥에 있어야 인증 실패도 봉투로 나간다. `authentication`은 `token_version` 대조를 위해 DB를 읽어야 하므로 **`db_session`이 그보다 바깥에 있어야 한다.** 다만 미인증·정적 성격의 요청(`/system/health`, 캐시 히트로 `304`가 되는 요청)이 커넥션을 점유하지 않도록 세션은 **지연 생성**한다 — 미들웨어는 세션 획득자(getter)만 컨텍스트에 심고, 실제 커넥션은 최초 질의 시점에 열린다.

### 5.1 라우트 데코레이터

미들웨어로 표현되지 않는 라우트별 관심사는 데코레이터로 처리한다.

| 데코레이터 | 역할 |
|---|---|
| `@require(PUBLIC \| MEMBER \| CURATOR)` | 권한 등급 강제. 라우트 선언부에서 권한이 **눈으로 보이게** 한다 |
| `@body(SchemaClass)` | 바디 파싱·검증 → `field_errors` 자동 생성 |
| `@query(SchemaClass)` | 쿼리 파싱·화이트리스트 검사 |
| `@paginated(mode, default_limit, max_limit)` | 페이지네이션 파라미터 처리 |
| `@etag(source)` | 조건부 요청 처리(`304`) |
| `@throttled(scope, key_fn, limit, window)` | 시도 제한 |
| `@audited(action, target_type)` | 성공 시 감사 로그 자동 기록 |

데코레이터는 **선언적 메타데이터**이기도 하다. 테스트가 전 라우트를 순회하며 "권한 데코레이터가 없는 라우트"를 검출한다(§14.2).

---

## 6. 횡단 관심사

### 6.1 설정

`config/settings.py`가 환경변수를 단일 객체로 로드한다. 사용처는 이 객체만 참조하고 `os.environ`을 직접 읽지 않는다.

| 변수 | 예 | 출처 |
|---|---|---|
| `STAGE` | `dev`/`staging`/`prod` | Chalice config |
| `DATABASE_URL` | RDS Proxy 엔드포인트 | Secrets Manager |
| `JWT_SECRET` | | Secrets Manager |
| `SESSION_TTL_DAYS` | 90 | Chalice config |
| `MEDIA_BUCKET`, `MEDIA_CDN_DOMAIN` | | Chalice config |
| `CF_KEY_PAIR_ID`, `CF_PRIVATE_KEY` | | Secrets Manager |
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` | | Secrets Manager |
| `SEED_CURATOR_*` | | 마이그레이션 전용 |
| `LOG_LEVEL` | `INFO` | Chalice config |

**시크릿은 Lambda 환경변수에 평문으로 넣지 않는다.** Secrets Manager에서 조회하고 **프로세스 전역에 캐시**한다(콜드 스타트당 1회). 런타임 조정이 필요한 값은 `app_setting` 테이블(§6.4)이고, 배포로만 바뀌는 값이 환경변수다. 이 구분을 흐리지 않는다.

### 6.2 오류 처리

```
AppError (기반)
├── ValidationError        → 422
├── AuthError              → 401
├── ForbiddenError         → 403
├── NotFoundError          → 404
├── ConflictError          → 409
├── PayloadTooLargeError   → 413
├── RateLimitError         → 429
├── DependencyError        → 503
└── InternalError          → 500
```

각 예외는 `code`·`message`·`details`·`retryable`을 갖는다. 오류 코드 카탈로그(API 문서 §5)는 `core/errors.py`의 **레지스트리 딕셔너리 하나**로 표현되며, 테스트가 "카탈로그에 없는 코드로 예외를 발생시키는 것"을 금지한다.

| 원천 예외 | 변환 |
|---|---|
| `pydantic.ValidationError` | `ValidationError` + `field_errors` 매핑 |
| `sqlalchemy.IntegrityError` (제약명 파싱) | 제약 → 코드 매핑 테이블 참조. 예 `uq_app_user_phone` → `SIGNUP_PHONE_TAKEN` |
| `StaleDataError` (버전 충돌) | `CONFLICT_VERSION` |
| `OperationalError` (커넥션) | `SYSTEM_DEPENDENCY_UNAVAILABLE` |
| `botocore.ClientError` | `DependencyError` |
| 그 외 | `InternalError`. 상세는 로그에만 |

**제약명 → 오류코드 매핑 테이블**을 두는 이유는 경쟁 조건 때문이다. 사전 조회로 중복을 검사해도 동시 요청에서는 제약 위반이 발생하며, 그때도 사용자에게는 같은 문구가 나가야 한다.

### 6.3 로깅

JSON 한 줄 로그. 필수 필드: `timestamp`, `level`, `request_id`, `route`, `method`, `status`, `duration_ms`, `actor_id`, `actor_role`, `event`, `message`.

| 금지 | 대안 |
|---|---|
| 전화번호 전체 | 마스킹(`010****5678`) |
| 비밀번호·해시·토큰 | 절대 기록하지 않음 |
| 요청 바디 전체 | 필드명 목록만 |
| 이미지 바이너리 | 키·크기만 |

민감 필드 마스킹은 로거 필터에서 **자동**으로 수행한다. 호출부의 주의에 의존하지 않는다.

### 6.4 설정 캐시

`app_setting`은 거의 변하지 않고 거의 모든 요청이 읽는다. `setting_service`가 **프로세스 전역 캐시(TTL 60초)**를 유지하고, 관리자가 값을 바꾸면 응답에 캐시 무효화 마커를 남긴다. Lambda 인스턴스가 여러 개이므로 최대 60초의 전파 지연이 있으며, 이는 모든 설정 항목에서 허용 가능하다(가입 잠금이 60초 늦게 닫히는 것은 문제가 되지 않는다).

### 6.5 시간

`core/timeutil.py`만이 시간을 만든다. `datetime.now()`를 다른 파일에서 호출하는 것을 린트로 금지한다.

| 함수 | 반환 |
|---|---|
| `now_utc()` | 현재 UTC (aware) |
| `now_kst()` | 현재 KST (aware) |
| `today_kst()` | KST 오늘 `date` |
| `kst_date_label(d)` | `2026. 08. 27. 목` |
| `kst_short_label(d)` | `8월 30일의 전시` |

테스트는 이 모듈을 한 곳에서 고정(freeze)해 날짜 경계 시나리오를 검증한다.

### 6.6 트랜잭션

- 요청당 세션 1개, 트랜잭션 1개가 기본이다.
- 서비스는 세션을 인자로 받고 스스로 commit하지 않는다. **commit은 미들웨어의 책임**이다.
- 예외적으로 커밋 경계를 나눠야 하는 경우(대량 배치)에만 서비스가 명시적으로 `session.begin_nested()`를 쓴다.
- **외부 호출(S3·웹푸시)은 트랜잭션 안에서 하지 않는다.** DB 커밋 후 수행하거나, 실패 가능성이 있으면 `notification_log` 같은 상태 행에 먼저 기록하고 별도 워커가 처리한다.

---

## 7. 도메인 서비스 명세

각 서비스의 **책임 범위와 불변식**을 정의한다. 메서드 시그니처는 구현 시 결정한다.

### 7.1 `exhibition_service` — 이 시스템의 심장

| 책임 | 규칙 |
|---|---|
| 현재 전시 조회 | DB 문서 Q1. `today_kst()`를 주입받아 계산 |
| 연장 판정 | `exhibition_date < viewing_date`이면 연장. 라벨 문자열까지 서비스가 생성 |
| 발행 규칙 적용 | 제목·테마·완성 그림 12점 충족 시 `is_published=true` 1회 전환 + `published_at` 기록 + 알림 큐 생성 |
| 발행 되돌림 금지 | 이미 `true`이면 어떤 경로로도 `false`로 쓰지 않는다 |
| 숨김·해제 | 숨김 후 관람자에게 걸릴 전시를 재계산해 반환 |
| 백필 차단 | 과거 날짜에 `is_published=false`인 행을 새로 만드는 요청 거부 |

**발행 전환은 단 하나의 함수(`apply_publish_rules`)에서만 일어난다.** 제목 저장·그림 저장·그림 삭제·순서 변경 등 모든 변경 경로가 이 함수를 마지막에 호출한다.

### 7.2 `exhibition_admin_service`

| 책임 | 규칙 |
|---|---|
| 달력 조립 | 날짜 시리즈 + LATERAL 단일 질의(DB 문서 §7.1). N+1 금지 |
| `edit_mode` 결정 | `create`(오늘·미래·행없음) / `edit`(발행됨 또는 오늘·미래 드래프트) / `carry_draft`(과거·미발행·드래프트 있음) / `locked`(과거·미발행·드래프트 없음) |
| 이어쓰기 | 원본 드래프트를 오늘 날짜로 **이동**. 대상 점유 시 거부. 원자적 트랜잭션 |
| 미리보기 | 관람자 DTO와 동일 스키마 생성 |

### 7.3 `artwork_service`

| 책임 | 규칙 |
|---|---|
| 슬롯 upsert | `(exhibition_id, position)` 기준. 없으면 생성 |
| 슬롯 비우기 | 행 삭제 + S3 키를 고아 목록에 남김(즉시 삭제 금지) |
| 순서 변경 | 목표 배치 전체를 받아 지연 제약으로 일괄 갱신 |
| 카운터 갱신 | 모든 변경 후 `exhibition`의 두 카운터를 재계산 |
| 발행 규칙 트리거 | 변경 후 `exhibition_service.apply_publish_rules` 호출 |

### 7.4 `view_log_service`

| 책임 | 규칙 |
|---|---|
| 입장 기록 | `(user_id, today_kst())` UPSERT. 신규 여부를 반환 |
| 열람 기록 | `(user_id, artwork_id)` UPSERT. `first_viewed_on`은 최초 1회만 설정 |
| 실패 내성 | 기록 실패가 조회 응답을 막지 않도록 **별도 엔드포인트**로 분리되어 있다(API 문서 §7.4) |

### 7.5 `notification_service`

| 책임 | 규칙 |
|---|---|
| 발행 시 큐 생성 | 대상: `notify_enabled AND NOT is_blocked`인 전 회원. `dedupe_key`로 중복 차단 |
| 발송 시각 계산 | 사용자의 `notify_at`이 아직 오지 않았으면 그 시각, 이미 지났으면 즉시. 단 `notify_cutoff_hour` 초과분은 `skipped` |
| 스킵 판정 | 연장된 날은 큐 생성 자체를 하지 않는다(§4.3 규칙 3) |
| 큐레이터 알림 | 연장 2일 연속 시 1회, 휴관 공지 기간에는 발송 안 함 / 신규 가입 시 즉시 |
| 발송 | 5분 주기 워커가 `pending`을 배치 처리. 404/410 응답 시 구독 비활성화 |

### 7.6 `media_service` · `upload_service` · `image_service`

| 서비스 | 책임 |
|---|---|
| `media_service` | CloudFront 서명 쿠키 생성, `ImageSet` URL 조립. **키 → URL 변환의 유일한 장소.** `app_setting.media_signing_mode`(`cookie`\|`url`)에 따라 서명 쿠키와 서명 URL 중 하나를 선택하며, 호출부는 어느 쪽인지 알지 못한다 |
| `upload_service` | Presigned PUT URL 발급(조건: content-type, 크기 상한), 슬롯 상태 `uploading` 전환, 완료 통지 처리 |
| `image_service` | S3 이벤트 수신 후 원본 검증 → 3종 생성 → LQIP 생성 → 메타 갱신 → 상태 전환. 실패 시 `failed` + 오류 코드 |

### 7.7 기타 서비스

| 서비스 | 핵심 불변식 |
|---|---|
| `auth_service` | 계정 존재 여부를 응답 차이로 노출하지 않는다. 실패 시 throttle 증가, 성공 시 초기화 |
| `session_service` | 만료 30일 이내면 재발급. `token_version` 불일치는 즉시 거부 |
| `member_service` | 큐레이터 계정은 차단·탈퇴·비밀번호 변경 대상이 아니다. 대행 가입은 가입 잠금과 무관 |
| `notice_service` | 활성 공지 기간 중첩 불가(DB EXCLUDE 제약과 이중 방어) |
| `setting_service` | `is_mutable=false` 키 변경 거부. 값 타입 검증 |
| `stats_service` | 모든 집계에서 `is_anonymized=false` 필터 필수 |
| `audit_service` | 실패해도 주 트랜잭션을 롤백시키지 않는다(로그 기록 실패로 조작이 취소되면 안 된다) |

---

## 8. 이미지 파이프라인

### 8.1 흐름

| 단계 | 주체 | 동작 |
|---|---|---|
| 1 | 프런트 | `POST .../upload-urls` — N개 슬롯의 Presigned PUT URL 요청 |
| 2 | `upload_service` | 슬롯 행 생성/확보, `image_status='uploading'`, 15분 만료 URL 발급 |
| 3 | 프런트 | S3에 직접 PUT (동시 3개) |
| 4 | S3 | `ObjectCreated:*` 이벤트 발행 (`uploads/` 접두 한정) |
| 5 | `image-worker` | 원본 검증 → 리사이즈 3종 → LQIP → S3 저장 → DB 갱신 → `ready` |
| 6 | 프런트 | `GET /admin/exhibitions/{date}` 폴링으로 `ready` 확인 |

`POST /admin/artworks/{id}/image/complete`는 4를 기다리지 않고 5를 직접 기동하는 **보조 경로**다. 두 경로가 동시에 들어와도 `image_status`를 조건부 갱신(`WHERE image_status = 'uploading'`)하므로 중복 처리되지 않는다.

### 8.2 오브젝트 키 규약

| 용도 | 키 |
|---|---|
| 원본(업로드 착지) | `uploads/{exhibition_date}/{artwork_id}/{upload_id}.{ext}` |
| 원본(확정) | `media/artworks/{artwork_id}/origin.{ext}` |
| 디스플레이 | `media/artworks/{artwork_id}/display.webp` |
| 썸네일 | `media/artworks/{artwork_id}/thumb.webp` |
| 공개(OG) | `media/public/entrance.jpg` |

`uploads/`와 `media/`를 분리하는 이유: **업로드 착지 지점은 서명 접근 대상이 아니며**, CloudFront는 `media/`만 오리진으로 본다. 처리 실패한 업로드가 CDN 경로에 남지 않는다.

### 8.3 처리 규격

| 산출물 | 규격 | 비고 |
|---|---|---|
| 썸네일 | 400×400, 중앙 정사각 크롭, WebP q80 | PRD §8.2 |
| 디스플레이 | 긴 변 1600px, 비율 유지, WebP q85 | |
| LQIP | 긴 변 16px, WebP q40, data URL(≤1.5KB) | 블러 플레이스홀더 |
| 원본 | 업로드 그대로 | 확대 요청 시에만 전송 |

**추가 처리** — EXIF 방향 보정(회전), EXIF 개인정보(GPS 등) 제거, 색 프로파일을 sRGB로 변환. 색 변환은 미술 작품에서 중요하다 — Adobe RGB 원본이 브라우저에서 탁하게 보이는 것을 막는다.

### 8.4 실패 처리

| 실패 | 코드 | 사용자 표시 |
|---|---|---|
| 파일이 이미지가 아님 | `INVALID_IMAGE` | 이미지 파일이 아닙니다 |
| 20MB 초과 | `TOO_LARGE` | 20MB까지 올릴 수 있습니다 |
| 픽셀 폭탄(1억 픽셀 초과) | `DIMENSION_LIMIT` | 이미지 크기가 너무 큽니다 |
| 처리 타임아웃 | `PROCESSING_TIMEOUT` | 처리에 실패했습니다. 다시 시도해 주세요 |
| 알 수 없음 | `UNKNOWN` | 동일 |

실패 시 `image_status='failed'` + `image_error_code`를 기록하고 **재업로드로만 복구**한다. 자동 재시도는 하지 않는다 — 대부분 파일 자체의 문제이고, 재시도는 큐레이터의 대기 시간만 늘린다. Lambda `image-worker`에는 SQS DLQ를 붙여 인프라성 실패를 별도로 관측한다.

---

## 9. 알림 파이프라인

### 9.1 구성

| 단계 | 주체 | 주기 |
|---|---|---|
| 큐 생성 | `notification_service` (발행 트랜잭션 내) | 발행 시 |
| 발송 | `notify_dispatcher` (EventBridge) | 5분 |
| 연장 감시 | `carryover_alert` (EventBridge) | 매일 23:00 KST |

### 9.2 발송 워커 동작

1. `status='pending' AND scheduled_for <= now()` 인 행을 최대 200건 조회
2. 각 행의 사용자 활성 구독을 모아 웹 푸시 전송(동시 10)
3. 성공 → `sent`, 4xx(404/410) → 구독 비활성화 후 남은 구독이 없으면 `skipped(no_subscription)`, 5xx → `attempt_count+1`, 3회 초과 시 `failed`
4. 당일 `notify_cutoff_hour` 초과 행은 발송하지 않고 `skipped(cutoff_passed)`

**`kind`의 구분** — 사용자의 `notify_at` 이전에 발행되어 예약 발송되는 건은 `morning_exhibition`, 이미 `notify_at`이 지난 뒤 발행되어 즉시 발송되는 건은 `late_publish`다. 두 종류는 발송 로직이 같고 `scheduled_for` 계산만 다르며, 구분해 두는 이유는 **"늦게 올린 날의 도달률"을 사후에 따로 볼 수 있어야** 하기 때문이다(PRD §6.12의 늦은 발행 규칙이 실제로 효과가 있는지 판단하는 근거).

**동시 실행 방지** — EventBridge가 중복 기동해도 `dedupe_key` 유니크와 조건부 상태 갱신(`WHERE status='pending'`)으로 이중 발송이 발생하지 않는다.

### 9.3 알림 문구

`오늘의 전시 · {전시 제목}` (PRD §6.12). 12점의 내용은 담지 않는다. 클릭 시 **A 첫 화면**으로 이동한다. 페이로드에 `url`, `tag`(= `exhibition_date`), `renotify: false`를 담아 같은 날 중복 배너가 쌓이지 않게 한다.

### 9.4 큐레이터 알림

| 종류 | 조건 | 빈도 |
|---|---|---|
| 연장 2일 | 오늘·어제 모두 미발행, 휴관 공지 기간 아님 | 연장 기간당 1회 (`dedupe_key`로 보장) |
| 신규 가입 | 회원 가입 성공 | 즉시, 가입 건당 1회 |

---

## 10. 배치 잡

| 잡 | 스케줄(KST) | 동작 | 실패 시 |
|---|---|---|---|
| `notify_dispatcher` | 5분마다 | §9.2 | 다음 주기에 재시도 |
| `carryover_alert` | 23:00 | §9.4 | 경보 |
| `retention_cleanup` | 04:00 | DB 문서 §10 | 경보 |
| `consistency_check` | 04:10 | 카운터 재계산·교정 | 교정 건수 로그 + 경보 |
| `stuck_upload_sweeper` | 30분마다 | 30분 초과 `uploading`/`processing` → `failed` | 경보 |
| `orphan_object_cleanup` | 04:20 | 미참조 S3 오브젝트(7일 경과) 삭제 | 경보 |
| `push_subscription_prune` | 04:30 | 비활성 30일 경과 구독 삭제(DB 문서 §11) | 경보 |

모든 잡은 **멱등**하고, 시작·종료·처리 건수를 구조화 로그로 남기며, 처리 0건도 로그를 남긴다(잡이 죽었는지 알 수 있어야 한다).

---

## 11. 데이터베이스 연결 관리

서버리스에서 가장 흔한 장애 원인이므로 명시적으로 규정한다.

| 항목 | 결정 | 근거 |
|---|---|---|
| 커넥션 경유 | **RDS Proxy 필수** | Lambda 동시성이 곧 커넥션 수가 되는 문제를 해소 |
| SQLAlchemy 풀 | `NullPool` | 실행 컨텍스트 재사용 시 죽은 커넥션을 잡고 있는 문제를 피한다. 풀링은 Proxy가 담당 |
| 엔진 생성 | **모듈 로드 시 전역 1회** | 콜드 스타트 비용을 요청마다 내지 않는다 |
| `pool_pre_ping` | 활성 | |
| 커넥션 타임아웃 | connect 3초 / statement 10초 | Lambda 타임아웃(29초) 전에 실패해야 오류 응답을 돌려줄 수 있다 |
| 세션 격리 수준 | `READ COMMITTED` (기본) | |
| 재시도 | 연결 오류에 한해 1회 즉시 재시도 | 쓰기 요청은 재시도하지 않는다 |
| 준비 문 캐시 | 비활성(`prepare_threshold=None` 상당) | RDS Proxy 핀닝 방지 |

### 11.1 콜드 스타트 대응

PRD §9.2가 지적한 아침 7:30 피크에 대응한다.

| 수단 | 적용 |
|---|---|
| 패키지 경량화 | `api` Lambda에서 Pillow·numpy 계열 제외. 목표 zip < 15MB |
| 전역 초기화 | 엔진·시크릿·설정 캐시를 모듈 로드 시 준비 |
| 지연 import | `integrations` 모듈은 사용 시점에 import |
| **프로비저닝** | 06:50–09:30 KST에 Provisioned Concurrency 2 (Application Auto Scaling 스케줄) |
| ARM64 | Graviton2로 비용·성능 개선. **`psycopg[binary]`(psycopg3)를 사용해 아키텍처 휠 문제를 회피**(PRD §9.2) |

**psycopg2 → psycopg3 전환은 결정 사항이다.** PRD가 지적한 x86 휠 불일치 위험을 근본적으로 없애고, SQLAlchemy 2.x가 psycopg3을 1급으로 지원한다.

---

## 12. 보안

| 영역 | 조치 |
|---|---|
| 인증 | JWT HS256, HttpOnly·Secure·SameSite=Lax 쿠키. 토큰을 응답 바디에 넣지 않는다 |
| 세션 무효화 | `token_version` 대조 |
| 비밀번호 | bcrypt cost 12. 검증 실패도 **동일 시간**이 걸리도록 더미 해시 검증 수행(타이밍 공격 방지) |
| 권한 | `@require(CURATOR)`가 서버에서 판정(PRD §8.4) |
| 시도 제한 | `auth_throttle` (§5.1) |
| 입력 검증 | pydantic 스키마 + DB 제약 이중 |
| SQL 인젝션 | ORM·바인딩 파라미터만 사용. 문자열 조립 SQL 금지 |
| 파일 업로드 | Presigned URL에 content-type·크기 조건 포함. 워커가 매직 바이트로 실제 형식 재검증 |
| 이미지 접근 | S3 비공개 + CloudFront 서명. `media/public/*`만 예외(OG 이미지) |
| 검색 노출 | 전 응답에 `X-Robots-Tag: noindex, nofollow`. 프런트 정적 응답도 동일 |
| 보안 헤더 | `Strict-Transport-Security`, `X-Content-Type-Options`, `Referrer-Policy: same-origin`, `Permissions-Policy`, CSP(프런트 문서 §12.2) |
| 로그 | 민감 필드 자동 마스킹(§6.3) |
| IAM | Lambda별 최소 권한. `api`는 S3 `PutObject` 서명 권한만, `image-worker`만 `GetObject/PutObject` |
| 감사 | 관리자 변경 조작 전건 `audit_log` |
| 의존성 | `pip-audit` CI 실행. 주 1회 자동 갱신 PR |

### 12.1 응답에서 존재를 숨기는 규칙

| 상황 | 응답 |
|---|---|
| 미가입 번호 로그인 | `AUTH_INVALID_CREDENTIALS` |
| 차단 회원 로그인 | `AUTH_INVALID_CREDENTIALS` |
| 미가입 번호 재설정 요청 | 성공 응답, 실제 발송 없음 |
| 미발행/숨김 전시 조회 | `EXHIBITION_NOT_FOUND` |
| 회원이 관리자 API 접근 | `AUTH_FORBIDDEN` (숨기지 않음, API 문서 §2.7) |

---

## 13. 배포

### 13.1 스테이지

| 스테이지 | 용도 | DB | 도메인 |
|---|---|---|---|
| `dev` | 로컬 개발 | 로컬 Docker PostgreSQL | `localhost` |
| `staging` | 통합 검증 | RDS(공유 소형) | 별도 서브도메인, `noindex` |
| `prod` | 운영 | RDS | 서비스 도메인 |

### 13.2 파이프라인

1. **검증** — 린트(ruff) · 타입(mypy) · 아키텍처(import-linter) · 단위·통합 테스트
2. **마이그레이션** — 별도 실행 단계에서 `alembic upgrade head`. 실패 시 배포 중단
3. **배포** — `chalice deploy --stage {stage}`
4. **스모크** — `/system/health`, `/public/landing`, 로그인 왕복 검증
5. **롤백** — 실패 시 직전 배포로 되돌리고 마이그레이션은 `downgrade` 한 단계

**배포 금지 시간대** — 07:00–09:00 KST(PRD §8.5).

### 13.3 IaC 범위

Chalice가 만들지 않는 자원(RDS, RDS Proxy, S3, CloudFront, EventBridge, Secrets, VPC)은 Terraform으로 관리한다. Chalice의 자동 IAM 정책 생성은 **비활성화**하고 `policy-prod.json`을 수기 관리한다 — 자동 생성은 과대 권한을 만든다.

---

## 14. 테스트 전략

### 14.1 계층별

| 종류 | 대상 | 도구 | 비중 |
|---|---|---|---|
| 단위 | 서비스 도메인 규칙(연장 판정, 발행 조건, edit_mode, 알림 스킵) | pytest + 가짜 리포지토리 | 50% |
| 통합 | 리포지토리 질의, 제약 위반, 마이그레이션 | pytest + 실제 PostgreSQL(testcontainers) | 30% |
| API 계약 | 라우트 입출력, 봉투 구조, 오류 코드, 권한 | Chalice `Client` | 20% |
| 잡 | 배치 멱등성, 알림 스킵 시나리오 | pytest | — |

### 14.2 반드시 있어야 하는 테스트

| # | 시나리오 | 근거 |
|---|---|---|
| T-1 | 연장 시나리오 전체 (PRD §4.3 동작 예시 표를 그대로 재현) | 이 제품의 핵심 규칙 |
| T-2 | 발행 후 12점이 깨져도 `is_published`가 유지됨 | PRD §6.10 |
| T-3 | 과거 날짜 신규 발행 거부 / 발행된 과거 전시 수정 허용 | 백필 규칙 |
| T-4 | 이어쓰기 — 대상 점유 시 거부, 원본 삭제, 원자성 | PRD 부록 B |
| T-5 | 관람일 경계(KST 23:59 / 00:01)의 입장 기록 | 시간대 버그의 단골 |
| T-6 | 연장된 날 알림 미발송 / 컷오프 초과 스킵 | PRD §6.12 |
| T-7 | 로그인 5회 실패 차단·성공 시 초기화 | PRD §6.2 |
| T-8 | 미가입·차단·오답이 동일 응답 | 보안 |
| T-9 | 숨김 처리 시 직전 전시가 걸림 | PRD §6.9 |
| T-10 | 탈퇴 시 로그 익명화 + 통계에서 제외 | PRD §7.3 |
| T-11 | 전 라우트에 권한 데코레이터 존재 (메타 테스트) | 권한 누락 방지 |
| T-12 | 전 응답이 봉투 스키마를 만족 (메타 테스트) | 계약 일관성 |
| T-13 | 오류 발생 코드가 카탈로그에 존재 (메타 테스트) | 코드 난립 방지 |

T-11~13은 **개별 기능 테스트가 아니라 규약 준수 테스트**다. 새 라우트를 추가하면 자동으로 검사 대상이 된다.

---

## 15. 관측성

| 항목 | 내용 |
|---|---|
| 로그 | CloudWatch Logs, JSON. 보관 30일(prod) |
| 지표(커스텀) | `exhibition.published`, `notification.sent/skipped/failed`, `image.processed/failed`, `auth.login_failed`, `view.entered` |
| 경보 | API 5xx 비율 > 2%(5분) / p95 지연 > 3초 / 알림 실패 > 10건 / 이미지 실패 > 3건 / DB 커넥션 오류 발생 / 배치 미실행 |
| 대시보드 | 요청량·지연·오류율, 발행 상태, 알림 결과, 이미지 파이프라인 |
| 추적 | X-Ray 활성(prod 샘플링 10%) |

**운영자가 1인이므로 경보는 적어야 한다.** 위 6개 외의 경보를 추가하지 않는다. 알림 피로가 곧 무시로 이어진다.

---

## 16. 성능 목표

| 항목 | 목표 | 측정 |
|---|---|---|
| `GET /exhibitions/current` p95 | ≤ 300ms (웜) | CloudWatch |
| 콜드 스타트 | ≤ 1.5초 | |
| `GET /admin/exhibitions/calendar` p95 | ≤ 400ms | |
| 이미지 1장 처리 | ≤ 8초 | |
| 12장 동시 처리 | ≤ 30초 | 워커 동시 실행 |
| 알림 100명 발송 | ≤ 30초 | |

---

## 17. PRD 대비 변경·보완 사항

| # | PRD | 이 문서의 결정 | 사유 |
|---|---|---|---|
| **B-1** | `psycopg2-binary` 아키텍처 문제 지적(§9.2) | **psycopg3 채택 + ARM64 확정** | 아키텍처 휠 불일치를 근본 제거하고 SQLAlchemy 2.x의 1급 지원을 얻는다 |
| **B-2** | Lambda 콜드 스타트 검토(§9.2) | 07:00 전후 Provisioned Concurrency 2 + `api` 패키지 경량화 | 아침 피크가 곧 서비스의 전부다 |
| **B-3** | 리사이즈 S3 이벤트 권장(§9.2) | S3 이벤트 + 완료 통지 API **이중 트리거** | 이벤트 지연 시 큐레이터가 무한 대기하는 문제 방지 |
| **B-4** | (없음) | RDS Proxy + NullPool 확정 | 서버리스 커넥션 고갈은 확실히 발생하는 장애다 |
| **B-5** | (없음) | Lambda 3분할(api/image-worker/scheduler) | 자원 프로필과 실패 격리가 다르다 |
| **B-6** | (없음) | `import-linter` 아키텍처 계약 CI | 계층 규칙은 강제되지 않으면 6개월 뒤 사라진다 |
| **B-7** | (없음) | 미들웨어 8단 + 라우트 데코레이터 7종 | 횡단 관심사 중복 제거(BA-4) |
| **B-8** | (없음) | 규약 준수 메타 테스트(T-11~13) | 권한 누락·봉투 이탈·코드 난립을 구조적으로 차단 |
| **B-9** | (없음) | EXIF 제거·sRGB 변환 | 개인정보(GPS) 유출 방지 + 작품 색 재현 |
| **B-10** | (없음) | `media/public/*` 경로 분리 | OG 이미지만 공개, 작품은 예외 없이 서명(PRD §8.4 부록 B) |
| **B-11** | 교차 검토 | 미들웨어 순서 정정 — `db_session`을 `authentication` 바깥으로, 단 **지연 생성** | 인증이 `token_version`을 읽으려면 세션이 필요하다. 초안의 순서로는 인증 단계에서 세션이 없다 |
| **B-12** | 교차 검토 | `push_subscription_prune` 잡을 배치 목록·디렉터리에 추가 | DB 문서 §11에만 있고 백엔드 잡 목록에서 누락되어 있었다 |
| **B-13** | 교차 검토 | `notification_log.kind`의 `late_publish` 사용처 정의 | 열거형에만 있고 어느 경로에서 쓰이는지 미정의였다 |
| **B-14** | 교차 검토 | `media_signing_mode` 설정을 `media_service` 내부로 캡슐화 | 서명 방식 전환이 호출부에 새어 나가면 안 된다 |
