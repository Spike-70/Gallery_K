"""엔드포인트 총람 대조 (API 문서 §4, 교차검토 §4 계약 표).

경로는 `02-API-SPEC` §4가 소유하고 백엔드 `api/routes/*`와 프런트 `shared/api/endpoints.ts`가
그것을 참조한다. 이 테스트는 **문서의 표를 그대로 옮겨 놓고** 구현과 대조한다 —
어느 한쪽만 바뀌면 실패한다.
"""

from __future__ import annotations

import pytest

#: API 문서 §4 총람 49행. (메서드, 경로, 권한)
DOCUMENTED: list[tuple[str, str, str]] = [
    ("GET", "/public/landing", "PUBLIC"),
    ("GET", "/public/notice", "PUBLIC"),
    ("POST", "/auth/signup", "PUBLIC"),
    ("POST", "/auth/login", "PUBLIC"),
    ("POST", "/auth/logout", "MEMBER"),
    ("GET", "/auth/session", "PUBLIC"),
    ("POST", "/auth/password", "MEMBER"),
    ("POST", "/auth/password/reset/request", "PUBLIC"),
    ("POST", "/auth/password/reset/confirm", "PUBLIC"),
    ("GET", "/exhibitions/current", "MEMBER"),
    ("GET", "/exhibitions/{date}", "MEMBER"),
    ("GET", "/exhibitions", "MEMBER"),
    ("POST", "/exhibitions/{date}/view", "MEMBER"),
    ("GET", "/artworks/{artwork_id}", "MEMBER"),
    ("POST", "/artworks/{artwork_id}/view", "MEMBER"),
    ("GET", "/me", "MEMBER"),
    ("PATCH", "/me/settings", "MEMBER"),
    ("DELETE", "/me", "MEMBER"),
    ("POST", "/me/push-subscriptions", "MEMBER"),
    ("GET", "/me/push-subscriptions", "MEMBER"),
    ("DELETE", "/me/push-subscriptions/{subscription_id}", "MEMBER"),
    ("GET", "/admin/summary", "CURATOR"),
    ("GET", "/admin/exhibitions/calendar", "CURATOR"),
    ("GET", "/admin/exhibitions/{date}", "CURATOR"),
    ("PUT", "/admin/exhibitions/{date}", "CURATOR"),
    ("POST", "/admin/exhibitions/{date}/hide", "CURATOR"),
    ("POST", "/admin/exhibitions/{date}/unhide", "CURATOR"),
    ("POST", "/admin/exhibitions/{date}/carry-draft", "CURATOR"),
    ("GET", "/admin/exhibitions/{date}/preview", "CURATOR"),
    ("PUT", "/admin/exhibitions/{date}/artworks/{position}", "CURATOR"),
    ("DELETE", "/admin/exhibitions/{date}/artworks/{position}", "CURATOR"),
    ("POST", "/admin/exhibitions/{date}/artworks/reorder", "CURATOR"),
    ("POST", "/admin/exhibitions/{date}/artworks/upload-urls", "CURATOR"),
    ("POST", "/admin/artworks/{artwork_id}/image/complete", "CURATOR"),
    ("GET", "/admin/members", "CURATOR"),
    ("POST", "/admin/members", "CURATOR"),
    ("POST", "/admin/members/{member_id}/block", "CURATOR"),
    ("POST", "/admin/members/{member_id}/unblock", "CURATOR"),
    ("POST", "/admin/members/{member_id}/reset-password", "CURATOR"),
    ("GET", "/admin/settings", "CURATOR"),
    ("PATCH", "/admin/settings", "CURATOR"),
    ("GET", "/admin/notices", "CURATOR"),
    ("POST", "/admin/notices", "CURATOR"),
    ("PATCH", "/admin/notices/{notice_id}", "CURATOR"),
    ("DELETE", "/admin/notices/{notice_id}", "CURATOR"),
    ("GET", "/admin/stats/daily", "CURATOR"),
    ("GET", "/admin/stats/members", "CURATOR"),
    ("GET", "/admin/stats/members/{member_id}", "CURATOR"),
    ("GET", "/system/health", "PUBLIC"),
]


@pytest.fixture(scope="module", autouse=True)
def _load_routes() -> None:
    import app  # noqa: F401


def _implemented() -> dict[tuple[str, str], str | None]:
    from chalicelib.api.routes._base import REGISTRY

    return {(entry.method, entry.path): entry.meta.access for entry in REGISTRY}


def test_the_documented_table_has_forty_nine_rows() -> None:
    assert len(DOCUMENTED) == 49


def test_every_documented_endpoint_is_implemented() -> None:
    implemented = _implemented()
    missing = [f"{method} {path}" for method, path, _ in DOCUMENTED if (method, path) not in implemented]
    assert missing == [], f"문서에 있으나 구현되지 않은 엔드포인트: {missing}"


def test_no_undocumented_endpoint_exists() -> None:
    """문서에 없는 경로가 조용히 늘어나지 않게 한다."""
    documented = {(method, path) for method, path, _ in DOCUMENTED}
    extra = [f"{method} {path}" for method, path in _implemented() if (method, path) not in documented]
    assert extra == [], f"문서에 없는 엔드포인트: {extra}"


def test_access_levels_match_the_documented_table() -> None:
    implemented = _implemented()
    mismatched = [
        f"{method} {path}: 문서 {access} ≠ 구현 {implemented[(method, path)]}"
        for method, path, access in DOCUMENTED
        if implemented.get((method, path)) != access
    ]
    assert mismatched == [], mismatched
