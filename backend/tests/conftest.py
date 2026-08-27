"""테스트 공통 설정.

`chalicelib.config.settings`는 import 시점에 환경변수를 검증한다(백엔드 문서 §8.1).
따라서 어떤 테스트 모듈보다 먼저 환경을 세워야 한다 — conftest 최상단에서 수행한다.
"""

from __future__ import annotations

import os

os.environ.setdefault("APP_ENV", "dev")
os.environ.setdefault("APP_VERSION", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-for-unit-tests-only-0123456789")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
os.environ.setdefault("MEDIA_BUCKET", "gallery-k-test")
os.environ.setdefault("AWS_REGION", "ap-northeast-2")
# presigned URL 서명은 로컬 계산이다. 자격증명만 있으면 네트워크 없이 동작한다.
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test-access-key")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test-secret-key")
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-northeast-2")

os.environ.setdefault("CURATOR_SEED_PHONE", "01000000000")
os.environ.setdefault("CURATOR_SEED_NAME", "테스트큐레이터")
os.environ.setdefault("CURATOR_SEED_PASSWORD", "test-curator-password")
