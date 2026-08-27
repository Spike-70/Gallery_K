"""블루프린트 조립 (백엔드 문서 §3·§7).

라우트는 얇다 — 입력 바인딩 → 서비스 호출 → 응답 조립 외의 분기를 두지 않는다(BA-2).

`route()`가 모든 뷰에 `endpoint` 경계를 자동으로 씌운다. 개별 라우트가 그것을 기억해야
한다면 언젠가 빠뜨리고, 빠뜨린 그 하나가 봉투 없는 500을 내보낸다.

동시에 라우트를 **레지스트리에 등록**한다. 계약 테스트가 이 레지스트리를 순회해 권한
데코레이터 누락을 검출한다(§12).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

from chalice import Blueprint

from chalicelib.core.decorators import RouteMeta, endpoint, meta_of


@dataclass(frozen=True, slots=True)
class RegisteredRoute:
    path: str
    method: str
    view_name: str
    meta: RouteMeta


#: 앱이 아는 전 라우트. import 시점에 채워진다.
REGISTRY: list[RegisteredRoute] = []

#: (메서드, 경로) → 원본 뷰 함수. 계약 테스트가 시그니처를 확인하는 데 쓴다.
VIEWS: dict[tuple[str, str], Callable[..., Any]] = {}


def registered_views() -> Iterator[tuple[RegisteredRoute, Callable[..., Any]]]:
    """등록된 (라우트, 원본 뷰) 쌍. 계약 테스트가 시그니처를 확인하는 데 쓴다.

    메타데이터만으로는 "데코레이터가 넣어 주는 인자를 뷰가 실제로 받는가"를 알 수 없다.
    """
    for entry in REGISTRY:
        view = VIEWS.get((entry.method, entry.path))
        if view is not None:
            yield entry, view


def blueprint(module_name: str) -> Blueprint:
    return Blueprint(module_name)


def route(
    bp: Blueprint,
    path: str,
    *,
    methods: tuple[str, ...] = ("GET",),
    **options: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        wrapped = endpoint(view)
        for method in methods:
            REGISTRY.append(
                RegisteredRoute(path=path, method=method, view_name=view.__name__, meta=meta_of(wrapped))
            )
            VIEWS[(method, path)] = view
        return bp.route(path, methods=list(methods), **options)(wrapped)

    return decorator
