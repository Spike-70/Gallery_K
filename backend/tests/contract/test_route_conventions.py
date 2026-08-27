"""규약 준수 메타 테스트 (백엔드 문서 §12).

개별 기능 테스트가 아니라 **새 라우트가 자동으로 검사 대상이 되게 하는 장치**다.
라우트를 하나 추가하면 아래 검사가 그 라우트에도 즉시 적용된다.

  ① 전 라우트에 권한 데코레이터가 있다
  ② 전 응답이 봉투 스키마를 만족한다 (`test_pipeline.py`와 각 라우트 테스트가 담당)
  ③ 발생하는 오류 코드가 카탈로그에 있다 (`AppError`가 생성 시점에 강제한다)
"""

from __future__ import annotations

import pytest

from chalicelib.config.constants import MUTATING_METHODS
from chalicelib.core.decorators import CURATOR, MEMBER, PUBLIC
from chalicelib.core.errors import CATALOG


@pytest.fixture(scope="module", autouse=True)
def _load_routes() -> None:
    """앱을 import 해야 레지스트리가 채워진다."""
    import app  # noqa: F401


def _registry() -> list:
    from chalicelib.api.routes._base import REGISTRY

    return REGISTRY


def test_every_route_declares_an_access_level() -> None:
    missing = [f"{r.method} {r.path}" for r in _registry() if r.meta.access is None]
    assert missing == [], f"@require 가 없는 라우트: {missing}"


def test_access_levels_are_from_the_documented_set() -> None:
    allowed = {PUBLIC, MEMBER, CURATOR}
    for entry in _registry():
        assert entry.meta.access in allowed


def test_admin_routes_require_curator() -> None:
    """`CURATOR` 판정은 서버에서만 한다 (API 문서 §2.7)."""
    wrong = [
        f"{r.method} {r.path}"
        for r in _registry()
        if r.path.startswith("/admin") and r.meta.access != CURATOR
    ]
    assert wrong == [], f"관리자 경로인데 CURATOR가 아닙니다: {wrong}"


def test_admin_mutations_are_audited() -> None:
    """관리자 변경 조작은 전건 기록한다 (백엔드 문서 §13)."""
    missing = [
        f"{r.method} {r.path}"
        for r in _registry()
        if r.path.startswith("/admin") and r.method in MUTATING_METHODS and r.meta.audited_action is None
    ]
    assert missing == [], f"@audited 가 없는 관리자 변경 라우트: {missing}"


def test_public_paths_are_actually_public() -> None:
    """점검 모드에서도 열려 있어야 하는 경로가 인증을 요구하면 안 된다."""
    for entry in _registry():
        if entry.path.startswith(("/public", "/system")):
            assert entry.meta.access == PUBLIC, f"{entry.path} 는 PUBLIC 이어야 합니다"


def test_no_duplicate_route_registrations() -> None:
    seen = [(r.method, r.path) for r in _registry()]
    assert len(seen) == len(set(seen)), f"중복 등록된 라우트가 있습니다: {seen}"


def test_paths_follow_the_naming_rule() -> None:
    """경로 세그먼트는 소문자 kebab-case. 경로 변수만 중괄호 안에서 snake_case다 (API 문서 §2.1)."""
    import re

    for entry in _registry():
        assert entry.path.startswith("/")
        literal = re.sub(r"\{[^}]+\}", "", entry.path)
        assert literal == literal.lower(), entry.path
        assert "_" not in literal, f"경로에 밑줄이 있습니다(kebab-case 규약): {entry.path}"
        for variable in re.findall(r"\{([^}]+)\}", entry.path):
            assert variable == variable.lower(), entry.path
            assert "-" not in variable, f"경로 변수는 snake_case 다: {entry.path}"


def test_error_catalog_is_the_only_source_of_codes() -> None:
    """카탈로그에 없는 코드는 `AppError` 생성 자체가 거부한다."""
    from chalicelib.core.errors import AppError

    with pytest.raises(LookupError):
        AppError("MADE_UP_CODE")
    assert len(CATALOG) == 43


def test_decorator_injected_arguments_match_view_signatures() -> None:
    """데코레이터가 넣어 주는 인자를 뷰가 실제로 받는지 확인한다.

    불일치는 요청이 들어와야만 `TypeError`로 드러난다 — 배포 후에 발견된다는 뜻이다.
    """
    from chalicelib.api.routes._base import registered_views
    from chalicelib.core.decorators import view_parameters

    injected = {"payload": "body_schema", "params": "query_schema", "pagination": "paginated"}
    problems: list[str] = []
    for entry, view in registered_views():
        parameters = view_parameters(view)
        for argument, meta_attribute in injected.items():
            declared = getattr(entry.meta, meta_attribute) is not None
            accepts = argument in parameters
            if declared and not accepts:
                problems.append(f"{entry.method} {entry.path}: {argument} 인자를 받지 않습니다")
            if accepts and not declared:
                problems.append(f"{entry.method} {entry.path}: {argument} 를 채울 데코레이터가 없습니다")
    assert problems == [], problems
