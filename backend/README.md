# 갤러리 K — 백엔드

Python 3.12 · AWS Chalice · PostgreSQL 16 · SQLModel/SQLAlchemy 2.x · Alembic

설계 기준선은 [`docs/04-BACKEND-ARCHITECTURE.md`](../docs/04-BACKEND-ARCHITECTURE.md), 데이터
모델은 [`docs/01-DATABASE-MODEL.md`](../docs/01-DATABASE-MODEL.md), 계약은
[`docs/02-API-SPEC.md`](../docs/02-API-SPEC.md)다. **문서가 코드보다 앞선다.**

## 시작하기

```bash
cd backend
python3.12 -m venv .venv
make install
cp .env.example .env          # 값을 채운다. .env는 커밋하지 않는다

# 로컬 PostgreSQL이 없다면 (pgserver 내장 바이너리로 띄운다)
.venv/bin/python scripts/dev_db.py start   # 출력된 URL을 .env의 DATABASE_URL에 넣는다

make migrate                  # 스키마 + 시드(큐레이터 1건, app_setting 10종)
make serve                    # http://localhost:8000
```

로컬 `chalice local`에는 API Gateway 스테이지 접두가 붙지 않는다. 배포 환경에서만
`/api`가 붙는다(CloudFront가 `/api/*`를 API Gateway로 보낸다).

소셜 로그인(카카오·구글)은 **리다이렉트 방식**이며 콜백 URI는 아래 한 형태뿐이다
(`docs/08-SOCIAL-AUTH.md` §7). 제공자 콘솔에 **글자 그대로** 등록한다.

```
{SOCIAL_REDIRECT_BASE_URL}/api/auth/social/{kakao|google}/callback
```

로컬에서는 오리진이 **5173**이다 — Vite dev 서버가 `/api`를 8000으로 프록시하므로
브라우저가 보는 오리진은 하나뿐이고, 8000을 등록하면 쿠키가 다른 오리진에 심겨
세션이 성립하지 않는다. `client_id`가 없는 제공자는 목록에서 빠지고 화면에 버튼도
뜨지 않는다.

프런트가 다른 포트(`localhost:5173`)에서 뜨므로 로컬에서만 CORS를 연다. `DEV_CORS_ORIGIN`이
비어 있으면(=프로덕션) 관련 헤더를 **하나도** 붙이지 않는다 — 동일 오리진 배포이므로
프리플라이트가 발생하지 않는다(API 문서 §2.11).

## 검증

```bash
make verify      # 린트 · 타입 · 계층 계약 · 의존성 취약점 · 테스트
```

| 명령 | 검사하는 것 |
|---|---|
| `make lint` | 코드 스타일 + **환경변수·현재시각 직접 접근 금지**(문서 §8.1·§8.4) |
| `make typecheck` | mypy strict 계열 |
| `make arch` | 계층 단방향 계약(문서 §5). 규칙이 테스트로 존재해야 유지된다 |
| `make audit` | 배포 패키지에 들어가는 의존성의 알려진 취약점(문서 §13) |
| `make test` | 단위 · 통합 · 계약 |
| `make smoke` | 배포 후 헬스·첫 화면·로그인 왕복(문서 §14) |

### 통합 테스트의 PostgreSQL

`make test`의 통합 테스트는 실제 PostgreSQL을 쓴다(문서 §12). 부분 인덱스·EXCLUDE·생성
컬럼·DEFERRABLE은 PostgreSQL에만 있고, 그것들이 이 제품의 무결성 분담에서 DB가 맡은 몫
전부이기 때문이다(DB 문서 §8).

* `TEST_DATABASE_URL`이 있으면 그 DB를 쓴다.
* 없으면 dev 의존성 `pgserver`가 담고 있는 PostgreSQL 16 바이너리로 임시 인스턴스를 띄운다.
  이 휠에는 contrib 확장이 없으므로 최초 1회 `scripts/setup_test_postgres.sh`가 같은 버전
  소스에서 `pg_trgm`·`btree_gist`만 PGXS로 빌드해 얹는다.

### 규약 준수 메타 테스트

개별 기능 테스트가 아니라 **새 라우트가 자동으로 검사 대상이 되게 하는 장치**다(문서 §12).

| 테스트 | 확인하는 것 |
|---|---|
| `tests/contract/test_route_conventions.py` | 전 라우트에 권한 데코레이터가 있다 · 관리자 경로는 CURATOR · 관리자 변경은 `@audited` |
| `tests/contract/test_endpoint_catalogue.py` | API 문서 §4 총람 49행과 구현이 정확히 일치한다(누락·초과·권한 불일치 모두 실패) |
| `tests/integration/test_envelope_conformance.py` | 전 라우트를 실제로 호출해 응답이 봉투 스키마를 만족한다 · 오류 코드가 카탈로그에 있다 |

## 구조

코드를 고치기 전에 [`RULES.md`](RULES.md)를 읽는다 — 재사용해야 할 헬퍼와 단일 지점이 거기 정리되어 있다.

문서 §3의 배치 기준을 그대로 따른다. 어디에 둘지 애매한 모듈은 책임이 두 개이므로 나눈다.

```
app.py                진입점. 블루프린트 등록 + 스케줄 핸들러 선언
migrations/           Alembic. 배포 패키지 제외
chalicelib/
  config/             환경변수를 읽는 유일한 지점 + 사양 고정 상수
  core/               봉투 · 오류 · 컨텍스트 · 미들웨어 · 데코레이터 · 보안 · 시간 · 로깅 · 식별자
  db/                 엔진 · 범용 질의 헬퍼 · 전용 질의 3종 · 모델 11종
  schemas/            요청·응답 DTO
  services/           도메인 규칙 (프레임워크를 모른다)
  integrations/       외부 어댑터. boto3·웹푸시는 여기서만 import
  api/                라우트 블루프린트 + 조립 지점(`deps.py`)
  jobs/               스케줄 루틴
  utils/              도메인 무지식 순수 함수
```

### 알아 두면 좋은 결정 몇 가지

* **발행 전환은 `services/publishing.py`의 함수 하나에서만** 일어난다. 제목 저장·그림
  저장·삭제·이어쓰기의 모든 경로가 마지막에 그 함수를 부른다.
* **모델 객체는 서비스 밖으로 나가지 않는다.** 서비스가 완성된 응답 dict를 반환하고
  라우트는 그것을 봉투에 담기만 한다.
* 모든 ORM 관계는 `lazy="raise"`다. 로딩을 지정하지 않고 접근하면 예외가 나므로 N+1이
  런타임에 드러난다.
* 시도 제한 카운터는 **요청 트랜잭션과 별개로 커밋한다.** 로그인 실패는 401로 끝나고
  요청이 롤백되는데, 그때 카운터까지 되돌아가면 제한이 성립하지 않는다.
* 관리자 경로의 `Cache-Control: no-store`는 라우트가 아니라 미들웨어가 경로로 못박는다 —
  오류 응답과 새로 추가되는 라우트까지 예외 없이 덮기 위해서다.

## 배포

파이프라인은 **검증 → 마이그레이션 독립 실행 → 배포 → 스모크**다. 마이그레이션은
애플리케이션 기동 시 자동 실행하지 않는다 — Lambda 동시 실행이 곧 동시 마이그레이션이 된다.

```bash
make verify
make migrate
ARTIFACT_BUCKET=… STACK_NAME=gallery-k-prod make deploy-prod
BASE_URL=https://…/api SMOKE_PHONE=… SMOKE_PASSWORD=… make smoke
```

배포 금지 시간대는 아침 관람 피크(07:00–09:00)다.

### ARM64 (문서 §2)

**Chalice 1.33의 패키저는 의존성 휠의 플랫폼 태그를 `x86_64`로 하드코딩한다**
(`chalice/deploy/packager.py::_get_pip_platforms`). 그래서 `chalice deploy`만으로는
ARM64 Lambda가 나오지 않는다. 우회 경로를 `scripts/package_arm64.sh`가 담당한다.

1. 의존성 전체를 **aarch64 휠**로 받아 `vendor/`에 푼다. Chalice는 `vendor/`를 그대로
   담고 자신의 런타임 파일(`chalice/app.py`·`__init__.py`, 둘 다 표준 라이브러리만 쓴다)은
   직접 주입하므로 requirements.txt를 비워도 안전하다.
2. `chalice package --pkg-format cloudformation`으로 산출물을 만든다.
3. `scripts/patch_architecture.py`가 템플릿의 각 Lambda에 `Architectures: [arm64]`를 박는다.

빌드는 x86 휠이 하나라도 섞이면 중단한다. 산출물 검증:

```bash
make package-arm64          # dist/arm64/{sam.json, deployment.zip, layer-deployment.zip}
```

* 네이티브 확장 33개 전부 AArch64 ELF (x86 0개)
* 레이어 압축 25.9MB / 해제 88.7MB — Lambda 한도(50MB · 250MB) 안

`chalice`를 **런타임 의존성에서 뺀 이유**도 여기 있다. requirements.txt에 두면
botocore·PyYAML·pip 같은 CLI 의존성이 딸려 들어와 레이어가 45.6MB로 불어난다.

> `aws cloudformation deploy` 단계는 이 저장소에서 실행해 검증하지 못했다(AWS 자격증명
> 없음). 패키지 산출물까지는 검증되어 있다.

### IAM 정책

`autogen_policy`를 끄고 `.chalice/policy-{stage}.json`에 명시한다 — 자동 생성은 최소
권한을 보장하지 않고, Chalice 1.33의 정적 분석기가 이 코드베이스에서 깨지기도 한다.
정책은 CloudWatch Logs와 **`gallery-k-media*` 버킷**만 허용하므로, 미디어 버킷 이름이
그 접두를 벗어나면 정책을 함께 고쳐야 한다.
