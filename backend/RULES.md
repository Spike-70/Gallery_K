# 백엔드 개발 규칙

**문서가 코드보다 앞선다.** 구조·계약 판단은 `../docs/`의 소유 문서를 근거로 하고, 코드를 근거로 삼지 않는다.

| 결정 | 소유 |
|---|---|
| 봉투·오류 코드·엔드포인트·페이지네이션 | `02-API-SPEC` §2·§4·§5 |
| 테이블·제약·보존·열거형 | `01-DATABASE-MODEL` |
| 계층·미들웨어·데코레이터·배치 | `04-BACKEND-ARCHITECTURE` |
| 발행·연장·백필·이어쓰기 | `PRD` §4.3, 부록 B |
| 화면 문구·상태 | `06-USER-EXPERIENCE` |

---

## 1. 계층

`api → services → db` 단방향. `core`는 전 계층 참조 가능, `utils`는 도메인 무지식.

- `services`: `chalice`·`api`·`schemas` import 금지
- `api`: `db.models` 직접 import 금지 → 필요한 열거형은 서비스가 별칭 재노출 (`auth_service.VIA_CURATOR`, `throttle_service.LOGIN`)
- `core`: 상위 계층 import 금지. 도메인 동작은 `MiddlewareDeps`/`DecoratorDeps` 주입
- `boto3`·`pywebpush`: `integrations/`에서만
- **모델 객체는 서비스 밖으로 나가지 않는다.** 서비스가 완성된 dict를 반환하고 라우트는 봉투에 담기만 한다

`make arch`(import-linter)가 강제. 조립 지점은 `api/deps.py` 하나.

미들웨어 순서(바깥→안): `request_context` `access_log` **`dev_cors`** `error_boundary`
`maintenance_gate` `csrf_guard` `db_session` `authentication` `response_finalize`.
CORS는 오류 경계 **바깥**이어야 오류 응답에도 헤더가 붙는다. 프리플라이트는 `app.py`의 `CORSConfig`가 맡는다.

## 2. 재사용 지도 — 새로 만들기 전에 확인

| 필요한 일 | 쓸 것 |
|---|---|
| 현재 시각·KST 오늘·날짜 파싱·표시 라벨 | `core/timeutil`: `now_utc` `kst_today` `kst_datetime` `to_kst` `date_label` `carried_over_label` `parse_date` `parse_time_of_day` `format_rfc3339` `format_date` `date_range` `week_start` `freeze_time` |
| PK·요청 ID·UUID 파싱 | `core/ids`: `new_id` `new_request_id` `parse_uuid` |
| 오류 발생·변환 | `core/errors`: `AppError(ErrorCode.X, details=…)` `translate_exception` `FieldError` `CONSTRAINT_ERROR_MAP` |
| 라우트 반환값·304 | `core/envelope`: `Result(data, status, pagination, cache_control, etag, headers)` `NotModified` |
| 커서·페이지 메타 | `core/pagination`: `Cursor` `cursor_meta` `page_meta` `clamp_limit` `parse_page` |
| 비밀번호·토큰·쿠키 | `core/security`: `hash_password` `verify_password` `issue_session_token` `decode_session_token` `build_session_cookie` `read_cookie` |
| 로그 | `core/logging`: `get_logger(name)` + `log_event(logger, "도메인.사건", **필드)`. 마스킹은 필터가 자동 수행 |
| 전화번호·문자열·해시·확장자 | `utils/text`: `normalize_phone` `mask_phone` `normalize_text` `sha256_hex` `safe_extension` |
| 질의 | `db/query`: §4 참조 |
| 요청 컨텍스트 | `core/context.current()` → `.db` `.today` `.now` `.actor_id` `.actor_role` `.request_id` `.set_cookies` `.audit_entries` |

재사용 가능한 응답 조각은 `serialize_*`로 이미 있다 — `session_user` `member_item` `notice` `setting`
`subscription`(`push_service`) `summary`/`detail`(`artwork_service`) `slot`(`artwork_admin_service`)
`day`(`exhibition_admin_service`) · 이미지는 `media_service.image_set`. 새로 조립하기 전에 찾는다.

## 3. 단일 지점 — 여기 외에서 다시 구현하지 않는다

| 규칙 | 위치 |
|---|---|
| 발행 전환 (조건 판정·알림 큐·백필 거부) | `services/publishing.apply()` — 모든 변경 경로가 마지막에 호출 |
| 카운터 재계산 | `publishing.recount()` |
| 세션 무효화 | `session_service.revocation_values()` |
| 세션 수명 | `session_service.session_ttl_seconds()` |
| 푸시 상태 판정 | `push_service.push_status_of()` |
| 연장 여부·문구 | `exhibition_service.carryover_state()` |
| 편집 모드 | `exhibition_admin_service.edit_mode_for()` |
| 시도 제한 정책 | `throttle_service.POLICIES` / `Policy.lock_at` |
| 알림 중복 키 | `notification_service.*_dedupe_key()` |
| presigned URL·이미지 키 | `services/media_service` (외부에서 `integrations.storage` 직접 호출 금지) |
| 이미지 변환 | `services/image_service.process()` |
| 운영 설정 | `setting_service.SettingKey` + `get_bool/get_int/get_str` |
| LIKE 이스케이프 | `db/query.escape_like()` |

## 4. DB

`db/query`만 쓴다. 문자열 SQL 조립 금지.

- 연산: `fetch` `fetch_one` `exists` `count` `aggregate` `insert` `bulk_insert` `update` `bulk_update` `upsert` `delete`
- 필터: `where={"필드__연산자": 값}` / 결합 `Q(a=1) & (Q(b=2) | ~Q(c=3))`
- 연산자: `eq ne lt lte gt gte in not_in like ilike contains startswith endswith isnull between`
- 관계 경로 `관계__필드`는 조인 자동 구성. **UPDATE/DELETE에는 쓸 수 없다**
- 로딩: `selectin=[...]` / `joined=[...]`. 관계는 `lazy="raise"`이므로 미지정 접근은 예외
- 투영: `columns=[...]` → dict 반환
- 낙관적 잠금: `update(..., expected_version=n)` → 불일치 시 `CONFLICT_VERSION`
- 멱등 기록: `upsert(values=…|[…], conflict=[…], update_values=…, returning=[…])`. 여러 행은 한 문장
- 삭제는 DB `ON DELETE`에 위임. 자식 행을 루프로 지우지 않는다

**전용 질의는 3개뿐**이며 늘리려면 근거가 필요하다: `db/queries/admin_calendar`(LATERAL 달력)·`member_list`(회원+파생필드)·`stats`(기간 집계).

### N+1 금지
목록·배치에서 행마다 질의하지 않는다. 기존 일괄 조회를 먼저 찾는다:
`artwork_service.viewed_artwork_ids` · `view_log_service.viewed_counts_by_exhibition` ·
`push_service.active_subscriptions_for`.
회원 수에 비례하는 INSERT도 금지 — `upsert`에 리스트를 넘긴다.
존재 확인은 `count`가 아니라 `exists`.

## 5. 라우트

```
@route(bp, "/경로", methods=("POST",))
@require(CURATOR)          # 필수. PUBLIC | MEMBER | CURATOR
@audited("도메인.액션")     # /admin 변경 계열 필수
@paginated(PAGE|CURSOR, default_limit=…, max_limit=…)
@query(스키마)   # → params 인자
@body(스키마)    # → payload 인자
@throttled(scope, key=…, count_attempts=…)
@etag(cache_control=…)
def view(경로변수, payload, params, pagination) -> Result: ...
```

- 데코레이터가 주입하는 인자명은 고정: `payload` `params` `pagination`
- 라우트가 하는 일: 경로 변수 해석 → 서비스 호출 → `Result` 반환 → 감사 항목 적재. 그 외 분기 금지
- 감사: `context.audit_entries.append({"target_type","target_id","summary","changes"})`. `changes`는 `audit_service.scrub`이 걸러 저장
- 캐시: `CACHE_LANDING` `CACHE_EXHIBITION_CURRENT` `CACHE_EXHIBITION_BY_DATE` `CACHE_NO_STORE`. `/admin/*`는 미들웨어가 `no-store` 강제
- 블루프린트는 `app.py`에 등록. `url_prefix` 쓰지 않는다

## 6. 스키마

`schemas/`는 요청 검증 + 계약 테스트용 응답 모델. 요청 모델은 `model_config = STRICT`(미지원 필드 거부 → `QUERY_UNKNOWN_PARAM`).
정렬은 `sort: Literal[...]`로 선언하면 `@query`가 `QUERY_INVALID_SORT`(400) + `details.allowed[]`로 거절한다.
전화번호 입력은 `PhoneMixin` 상속. 길이 상한은 `config/constants.LIMIT_*` 참조(리터럴 금지).

## 7. 오류

`AppError(ErrorCode.X)`만 사용. 카탈로그(`core/errors.CATALOG`, 43종)에 없는 코드는 생성 자체가 실패한다.
새 상황에는 새 코드를 추가하되 `02-API-SPEC` §5를 먼저 갱신한다.
제약 위반은 `CONSTRAINT_ERROR_MAP`에 제약명을 등록해 코드로 매핑한다.

## 8. 새로 추가할 때

| 추가 대상 | 함께 갱신 |
|---|---|
| 엔드포인트 | `02-API-SPEC` §4 → `tests/contract/test_endpoint_catalogue.py` DOCUMENTED |
| 오류 코드 | `02-API-SPEC` §5 → `core/errors` |
| 열거형 값 | `01-DATABASE-MODEL` §5 → `db/models/enums.py` → 프런트 `shared/types/enums.ts` |
| 운영 설정 | `01-DATABASE-MODEL` §4.9 → `setting_service.SettingKey`+`DEFAULTS` → 시드 마이그레이션 → **실사용처** |
| 테이블·컬럼 | 모델 → Alembic 리비전(`downgrade()` 필수) → `test_upgrade_head_matches_the_models` 통과 |
| 관계 | `passive_deletes=True` + `lazy="raise"` 필수 |
| 외부 호출 | `integrations/`에 어댑터. 결과는 상태 코드가 아니라 **의미**로 반환 |
| 배치 루틴 | `jobs/`에 본문, `app.py`는 선언만. 멱등 + 처리 0건도 `log_event` |

## 9. 금지

린트가 잡는 것: `os.environ`/`os.getenv` · `datetime.now`/`utcnow`/`date.today`/`time.time` · 계층 위반.
리뷰가 잡는 것: 문자열 SQL 조립 · 사양 값 하드코딩(→`config/constants`) · 서비스·라우트에서의 커밋(커밋은 미들웨어 책임) ·
N+1 · 비밀번호·해시·토큰·엔드포인트 원문·전화번호 전체를 로그·감사에 남기는 것(관리자 응답의 `phone`만 예외).

## 10. 테스트

| 종류 | 위치 | 대상 |
|---|---|---|
| 단위 | `tests/unit` | 순수 도메인 규칙 |
| 통합 | `tests/integration` (`pytestmark = pytest.mark.integration`) | 실제 PostgreSQL |
| 계약 | `tests/contract` | 봉투·권한·경로 총람. DB 없이 |

픽스처: `session`(롤백) · `write_session`(커밋) · `api_client`(실 DB 붙은 Chalice 클라이언트) · `migration_engine`.
헬퍼: `helpers.signup/login/curator_token/auth_headers/json_body` · `factories.make_exhibition/make_artwork` · `fake_storage.install`.
시각 고정은 `freeze_time`. 새 라우트는 아래가 자동으로 검사한다 — 통과하지 못하면 규약 위반이다:
`test_route_conventions`(권한·감사·명명·주입 인자) · `test_endpoint_catalogue`(문서 총람 일치) ·
`test_envelope_conformance`(전 라우트 호출 후 봉투·오류 코드).

## 11. 명령

`make verify`(린트·타입·계층·취약점·테스트) · `make migrate` · `make serve` · `make test-integration` · `make package-arm64` · `make smoke`
