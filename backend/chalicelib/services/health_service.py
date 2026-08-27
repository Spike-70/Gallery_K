"""헬스 체크 (API 문서 §10.1).

의존성 확인은 서비스가 한다 — 라우트가 `integrations`를 직접 부르면 계층이 하나 건너뛰게
되고, 나중에 확인 항목이 늘어날 때 라우트가 두꺼워진다.

**`degraded`여도 HTTP 200이다.** 헬스 체크가 5xx를 내면 CloudFront 오리진 실패로 잡혀
A 첫 화면까지 죽는다(PRD §8.5).
"""

from __future__ import annotations

from typing import Any

from chalicelib.config.settings import settings
from chalicelib.db.engine import ping as database_ping
from chalicelib.integrations.storage import is_available as storage_available


def check() -> dict[str, Any]:
    database_ok = database_ping()
    storage_ok = storage_available()
    return {
        "status": "ok" if database_ok and storage_ok else "degraded",
        "checks": {
            "database": "ok" if database_ok else "fail",
            "storage": "ok" if storage_ok else "fail",
        },
        "version": settings.app_version,
    }
