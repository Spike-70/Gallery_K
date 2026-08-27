"""Chalice 진입점 (백엔드 문서 §3).

이 파일이 하는 일은 셋뿐이다.
  1. 미들웨어·데코레이터 조립 (`api/deps.py`)
  2. 블루프린트 등록 — 경로별 라우트는 `chalicelib/api/routes/` 안에 있다
  3. 스케줄 핸들러 선언 — 루틴 본문은 `chalicelib/jobs/` 안에 있다

라우트 본문·도메인 규칙을 여기에 쓰지 않는다.
"""

from __future__ import annotations

from dataclasses import asdict

from chalice import Chalice, CORSConfig, Rate

from chalicelib.api import deps
from chalicelib.api.routes import artworks, auth, exhibitions, me, public, system
from chalicelib.api.routes.admin import exhibitions as admin_exhibitions
from chalicelib.api.routes.admin import members as admin_members
from chalicelib.config.constants import CSRF_HEADER_NAME, REQUEST_ID_HEADER
from chalicelib.config.settings import settings
from chalicelib.core.logging import configure_logging

configure_logging()

#: 야간 정리를 도는 KST 시각과 창. 5분 주기 안에서 하루 한 번만 걸리게 한다.
NIGHTLY_HOUR_KST = 3
NIGHTLY_WINDOW_MINUTES = 5

app = Chalice(app_name="gallery-k")
app.debug = settings.is_development

# 로컬 개발 CORS (API 문서 §2.11).
#
# 프리플라이트(OPTIONS)는 애플리케이션 미들웨어보다 앞에서 처리된다 — `chalice local`도
# API Gateway도 그렇다. 그래서 Chalice의 CORS 설정을 함께 켠다. 응답 헤더 자체는
# `core/middleware.dev_cors`가 오류 응답까지 빠짐없이 붙인다.
#
# **프로덕션에서는 설정이 비어 있어 아무 것도 켜지지 않는다.** 동일 오리진 배포이므로
# 프리플라이트가 발생하지 않는다.
if settings.dev_cors_origin:
    app.api.cors = CORSConfig(
        allow_origin=settings.dev_cors_origin,
        allow_headers=[CSRF_HEADER_NAME, "Content-Type", "If-None-Match"],
        expose_headers=[REQUEST_ID_HEADER, "ETag", "Retry-After"],
        max_age=600,
        allow_credentials=True,
    )

deps.install(app)

# 블루프린트. `url_prefix`를 주지 않는다 — 전체 경로가 라우트 선언부에 그대로 보이는 편이
# "이 경로가 어디 있더라"를 찾는 시간을 줄인다.
app.register_blueprint(system.bp)
app.register_blueprint(public.bp)
app.register_blueprint(auth.bp)
app.register_blueprint(me.bp)
app.register_blueprint(exhibitions.bp)
app.register_blueprint(artworks.bp)
app.register_blueprint(admin_exhibitions.bp)
app.register_blueprint(admin_members.bp)


# ── 스케줄 핸들러 (백엔드 문서 §11) ────────────────────────────────────────
# 핸들러는 **하나**이며 두 가지 일을 한다. 루틴 본문은 `chalicelib/jobs/`에 있다.
# 중복 기동은 `dedupe_key` 유니크와 조건부 상태 갱신으로 무해하다.


@app.schedule(Rate(5, unit=Rate.MINUTES), name="scheduler")
def scheduler(event: object) -> dict[str, object]:
    """짧은 주기 — 발송 예정 시각이 지난 대기 알림을 배치 처리한다.

    KST 새벽 3시대의 첫 기동에서는 야간 정리도 함께 돈다. 잡을 둘로 나누지 않는 이유는
    자원을 늘리는 결정에 지금 필요한 근거가 없기 때문이다(BA-6). 아침 관람 피크와
    가장 먼 시각이라 정리 작업이 관람에 닿지 않는다.
    """
    from chalicelib.core.timeutil import now_kst
    from chalicelib.jobs import dispatch_due_notifications, run_nightly_maintenance

    dispatched = dispatch_due_notifications()
    result: dict[str, object] = {"dispatch": asdict(dispatched)}

    now = now_kst()
    if now.hour == NIGHTLY_HOUR_KST and now.minute < NIGHTLY_WINDOW_MINUTES:
        result["nightly"] = asdict(run_nightly_maintenance())
    return result
