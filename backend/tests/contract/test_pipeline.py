"""요청 파이프라인 규약 (백엔드 문서 §6, API 문서 §2)."""

from __future__ import annotations

from chalice.test import Client

from chalicelib.config.constants import REQUEST_ID_HEADER, SECURITY_HEADERS
from chalicelib.core.errors import CATALOG, ErrorCode
from chalicelib.schemas.public import HealthOut, LandingOut

from .conftest import assert_envelope


def test_health_always_answers_two_hundred(client: Client) -> None:
    """`degraded`여도 200이다 — 5xx면 CloudFront 오리진 실패로 잡힌다(PRD §8.5)."""
    response = client.http.get("/system/health")
    assert response.status_code == 200
    assert_envelope(response.json_body)
    HealthOut.model_validate(response.json_body["data"])


def test_landing_never_fails_even_without_a_database(client: Client) -> None:
    """DB가 없어도 오늘 날짜와 가입 기본값은 나온다 (API 문서 §6.1)."""
    response = client.http.get("/public/landing")
    assert response.status_code == 200
    body = response.json_body
    assert_envelope(body)
    data = LandingOut.model_validate(body["data"])
    assert data.today == body["meta"]["server_date"]
    assert data.today_label.endswith(("월", "화", "수", "목", "금", "토", "일"))
    assert data.signup_open is True
    assert data.is_authenticated is False


def test_meta_is_present_on_every_response(client: Client) -> None:
    response = client.http.get("/public/landing")
    meta = response.json_body["meta"]
    assert set(meta) == {
        "request_id",
        "server_time",
        "server_date",
        "api_version",
        "pagination",
        "deprecation",
    }
    assert meta["api_version"] == "v1"
    assert len(meta["request_id"]) == 26
    assert response.headers[REQUEST_ID_HEADER] == meta["request_id"]


def test_request_ids_are_unique_per_request(client: Client) -> None:
    first = client.http.get("/public/landing").json_body["meta"]["request_id"]
    second = client.http.get("/public/landing").json_body["meta"]["request_id"]
    assert first != second


def test_security_headers_are_attached(client: Client) -> None:
    """검색 노출 차단이 보안 요구사항이다 (PRD §8.4)."""
    response = client.http.get("/public/landing")
    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value
    assert "noindex" in response.headers["X-Robots-Tag"]


def test_cache_control_follows_the_endpoint_table(client: Client) -> None:
    assert client.http.get("/public/landing").headers["Cache-Control"] == "private, max-age=60"
    assert client.http.get("/system/health").headers["Cache-Control"] == "no-store"


def test_mutating_request_without_csrf_header_is_refused(client: Client) -> None:
    """`SameSite=Lax` + 커스텀 헤더. 헤더가 없으면 처리하지 않는다 (API 문서 §2.7)."""
    response = client.http.post("/public/landing", body=b"{}")
    assert response.status_code == 403
    assert_envelope(response.json_body)
    assert response.json_body["error"]["code"] == ErrorCode.CSRF_HEADER_MISSING


def test_unknown_path_is_stopped_before_the_application(client: Client) -> None:
    """등록되지 않은 경로는 API Gateway가 먼저 끊는다. Lambda까지 오지 않는다."""
    response = client.http.get("/no/such/path")
    assert response.status_code == 403


def test_framework_error_still_returns_an_envelope(client: Client, csrf_headers: dict[str, str]) -> None:
    """존재하는 경로의 지원하지 않는 메서드는 Lambda까지 온다. 봉투로 나가야 한다."""
    response = client.http.put("/system/health", body=b"{}", headers=csrf_headers)
    assert_envelope(response.json_body)
    assert response.json_body["error"]["code"] == ErrorCode.NOT_FOUND
    assert response.status_code == 404


def test_error_codes_come_from_the_catalog(client: Client) -> None:
    response = client.http.post("/public/landing", body=b"{}")
    assert response.json_body["error"]["code"] in CATALOG


def test_doc_hint_is_null_outside_production(client: Client) -> None:
    """개발 환경에서는 채워질 수 있고 프로덕션에서는 항상 null이다 (API 문서 §2.5)."""
    response = client.http.post("/public/landing", body=b"{}")
    assert "doc_hint" in response.json_body["error"]


def test_development_cors_allows_the_local_frontend(client: Client) -> None:
    """로컬에서만 다른 포트의 프런트가 붙는다 (API 문서 §2.11).

    프로덕션은 동일 오리진이므로 이 헤더가 붙지 않는다.
    """
    from chalicelib.config.settings import settings

    assert settings.dev_cors_origin == "http://localhost:5173"
    response = client.http.get("/public/landing")
    assert response.headers["Access-Control-Allow-Origin"] == settings.dev_cors_origin
    # 세션 쿠키가 오가야 하므로 credentials가 켜져 있어야 한다.
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert "X-Requested-With" in response.headers["Access-Control-Allow-Headers"]


def test_cors_headers_are_present_on_error_responses(client: Client) -> None:
    """오류 응답에 CORS 헤더가 빠지면 브라우저가 본문을 읽지 못해 원인을 알 수 없다."""
    response = client.http.post("/public/landing", body=b"{}")
    assert response.status_code == 403
    assert "Access-Control-Allow-Origin" in response.headers
