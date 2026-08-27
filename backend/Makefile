# 갤러리 K 백엔드 — 검증·실행 명령 단일 지점 (백엔드 문서 §14)
# 파이프라인: 검증 → 마이그레이션 독립 실행 → 배포 → 스모크

STAGE ?= prod

PY := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: install lint format typecheck arch audit test test-unit test-integration verify migrate serve smoke package-arm64 deploy-dev deploy-prod

install:            ## 개발 의존성 설치
	$(PIP) install -r requirements-dev.txt

lint:               ## 린트 (환경변수·시간 직접 접근 금지 규칙 포함)
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .

format:             ## 자동 정렬
	.venv/bin/ruff check --fix .
	.venv/bin/ruff format .

typecheck:
	.venv/bin/mypy

arch:               ## 계층 계약 (백엔드 문서 §5)
	.venv/bin/lint-imports

# PYSEC-2026-3721은 pip 자신의 권고다. pip는 배포 패키지에 들어가지 않는 빌드 도구이고,
# 수정본(26.2)은 chalice 1.33이 `pip<26.2`로 막고 있다. chalice가 핀을 풀면 함께 올린다.
audit:              ## 배포 패키지에 들어가는 의존성의 취약점 점검 (문서 §13)
	.venv/bin/pip-audit -r requirements.txt --progress-spinner off \
		--ignore-vuln PYSEC-2026-3721

test:
	$(PY) -m pytest

test-unit:
	$(PY) -m pytest -m "not integration"

test-integration:   ## 실제 PostgreSQL 필요. 없으면 scripts/setup_test_postgres.sh 가 준비한다
	$(PY) -m pytest -m integration

verify: lint typecheck arch audit test   ## 배포 전 검증 전량

migrate:            ## 배포 파이프라인의 독립 단계. 기동 시 자동 실행하지 않는다 (DB 문서 §9)
	.venv/bin/alembic upgrade head

serve:
	.venv/bin/chalice local --port 8000 --stage dev

smoke:              ## 배포 후 스모크 — 헬스·첫 화면·로그인 왕복 (문서 §14)
	bash scripts/smoke.sh

package-arm64:      ## ARM64 배포 패키지 빌드 (문서 §2). Chalice는 x86만 만들므로 우회한다
	bash scripts/package_arm64.sh $(STAGE)

deploy-dev:         ## dev는 chalice deploy로 충분하다 (아키텍처를 따지지 않는다)
	.venv/bin/chalice deploy --stage dev

# 운영은 ARM64다. chalice deploy를 쓰지 않는 이유는 Chalice 1.33이 x86_64로만
# 패키징하기 때문이다(scripts/package_arm64.sh 주석 참고).
#   ARTIFACT_BUCKET=... STACK_NAME=gallery-k-prod make deploy-prod
deploy-prod: STAGE = prod
deploy-prod: package-arm64
	@test -n "$(ARTIFACT_BUCKET)" || (echo "ARTIFACT_BUCKET이 필요합니다" >&2; exit 1)
	@test -n "$(STACK_NAME)" || (echo "STACK_NAME이 필요합니다" >&2; exit 1)
	aws cloudformation package \
		--template-file dist/arm64/sam.json \
		--s3-bucket $(ARTIFACT_BUCKET) \
		--output-template-file dist/arm64/packaged.yaml
	aws cloudformation deploy \
		--template-file dist/arm64/packaged.yaml \
		--stack-name $(STACK_NAME) \
		--capabilities CAPABILITY_IAM
