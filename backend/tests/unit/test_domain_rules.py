"""도메인 규칙 단위 테스트 (백엔드 문서 §12 "단위").

연장 판정 · 발행 조건 · 편집 모드 · 알림 스킵. 모두 DB 없이 판정되는 순수 규칙이며,
그렇게 만든 것 자체가 설계의 일부다 — 규칙이 질의에 섞여 있으면 이 파일이 존재할 수 없다.
"""

from __future__ import annotations

import datetime as dt

import pytest

from chalicelib.db.models.enums import EditMode, ExhibitionDayStatus
from chalicelib.services import exhibition_admin_service, exhibition_service, publishing

TODAY = dt.date(2026, 8, 27)


# ── 연장 판정 (PRD §4.3) ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("exhibition_date", "viewing_date", "carried", "label"),
    [
        (dt.date(2026, 8, 27), TODAY, False, None),
        (dt.date(2026, 8, 30), dt.date(2026, 8, 31), True, "8월 30일의 전시"),
        (dt.date(2026, 9, 3), dt.date(2026, 9, 5), True, "9월 3일의 전시"),
    ],
)
def test_carryover_state(
    exhibition_date: dt.date, viewing_date: dt.date, carried: bool, label: str | None
) -> None:
    assert exhibition_service.carryover_state(exhibition_date, viewing_date) == (carried, label)


def test_prd_worked_example() -> None:
    """PRD §4.3의 동작 예시를 그대로 확인한다.

    큐레이터가 8/29·8/30·9/01·9/03·9/06에 올린 경우, 관람자가 보는 전시.
    """
    published = [
        dt.date(2026, 8, 29),
        dt.date(2026, 8, 30),
        dt.date(2026, 9, 1),
        dt.date(2026, 9, 3),
        dt.date(2026, 9, 6),
    ]

    def hanging(viewing_date: dt.date) -> dt.date:
        return max(day for day in published if day <= viewing_date)

    expected = {
        dt.date(2026, 8, 29): dt.date(2026, 8, 29),
        dt.date(2026, 8, 30): dt.date(2026, 8, 30),
        dt.date(2026, 8, 31): dt.date(2026, 8, 30),  # 연장
        dt.date(2026, 9, 1): dt.date(2026, 9, 1),
        dt.date(2026, 9, 2): dt.date(2026, 9, 1),  # 연장
        dt.date(2026, 9, 3): dt.date(2026, 9, 3),
        dt.date(2026, 9, 4): dt.date(2026, 9, 3),  # 연장
        dt.date(2026, 9, 5): dt.date(2026, 9, 3),  # 연장 2일째
        dt.date(2026, 9, 6): dt.date(2026, 9, 6),
    }
    for viewing_date, exhibition_date in expected.items():
        assert hanging(viewing_date) == exhibition_date
        carried, label = exhibition_service.carryover_state(exhibition_date, viewing_date)
        assert carried == (exhibition_date < viewing_date)
        assert (label is not None) == carried


# ── 편집 모드 (API 문서 §3.9) ──────────────────────────────────────────────


@pytest.mark.parametrize(
    ("day", "row", "expected"),
    [
        # 발행된 전시는 과거·오늘·미래 모두 수정할 수 있다.
        (dt.date(2026, 8, 20), {"own_is_published": True}, EditMode.EDIT),
        (TODAY, {"own_is_published": True}, EditMode.EDIT),
        (dt.date(2026, 9, 1), {"own_is_published": True}, EditMode.EDIT),
        # 오늘·미래의 빈 날은 새로 쓴다.
        (TODAY, {}, EditMode.CREATE),
        (dt.date(2026, 9, 1), {}, EditMode.CREATE),
        # 과거의 빈 날은 백필 금지이므로 잠긴다.
        (dt.date(2026, 8, 20), {}, EditMode.LOCKED),
        # 과거에 쓰다 만 작업물이 있으면 이어쓰기를 제안한다.
        (dt.date(2026, 8, 20), {"own_title": "쓰다 만 제목"}, EditMode.CARRY_DRAFT),
        (dt.date(2026, 8, 20), {"own_artwork_count": 3}, EditMode.CARRY_DRAFT),
        (dt.date(2026, 8, 20), {"own_theme": "테마만 썼다"}, EditMode.CARRY_DRAFT),
        # 빈 문자열은 작업물이 아니다.
        (dt.date(2026, 8, 20), {"own_title": "  ", "own_artwork_count": 0}, EditMode.LOCKED),
    ],
)
def test_edit_mode(day: dt.date, row: dict, expected: str) -> None:
    assert exhibition_admin_service.edit_mode_for(day, TODAY, row) == expected


# ── 달력 상태 (PRD §6.9) ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("day", "row", "expected"),
    [
        (TODAY, {"own_is_published": True}, ExhibitionDayStatus.PUBLISHED),
        # 숨긴 전시는 발행됨으로 표시하지 않는다.
        (
            TODAY,
            {"own_is_published": True, "own_is_hidden": True},
            ExhibitionDayStatus.EMPTY,
        ),
        # `↑`는 과거에만 나타난다.
        (
            dt.date(2026, 8, 26),
            {"hung_date": dt.date(2026, 8, 25)},
            ExhibitionDayStatus.CARRIED_OVER,
        ),
        # 오늘·미래는 아직 준비되지 않았다는 뜻의 `N`이다.
        (TODAY, {"hung_date": dt.date(2026, 8, 25)}, ExhibitionDayStatus.EMPTY),
        (dt.date(2026, 9, 1), {"hung_date": dt.date(2026, 8, 25)}, ExhibitionDayStatus.EMPTY),
        # 개관 전 과거에는 걸릴 전시 자체가 없었다.
        (dt.date(2026, 8, 20), {}, ExhibitionDayStatus.EMPTY),
    ],
)
def test_day_status(day: dt.date, row: dict, expected: str) -> None:
    assert exhibition_admin_service._day_status(day, row, TODAY) == expected


# ── 발행 조건 (PRD 부록 B) ─────────────────────────────────────────────────


class _FakeExhibition:
    def __init__(self, title: str | None, theme: str | None) -> None:
        self.title = title
        self.theme = theme


@pytest.mark.parametrize(
    ("title", "theme", "expected"),
    [
        ("제목", "테마", []),
        (None, "테마", [publishing.MISSING_TITLE]),
        ("제목", None, [publishing.MISSING_THEME]),
        (None, None, [publishing.MISSING_TITLE, publishing.MISSING_THEME]),
        ("   ", "테마", [publishing.MISSING_TITLE]),
    ],
)
def test_publish_blockers(title: str | None, theme: str | None, expected: list[str]) -> None:
    assert publishing.blockers_for(_FakeExhibition(title, theme)) == expected  # type: ignore[arg-type]


# ── 알림 키 (DB 문서 §4.10) ────────────────────────────────────────────────


def test_dedupe_keys_express_the_frequency_rules() -> None:
    """`dedupe_key` 유니크가 "하루 1회"와 "연장 기간당 1회"를 DB 수준에서 보장한다."""
    import uuid

    from chalicelib.services import notification_service

    user = uuid.uuid4()
    # 같은 회원·같은 발행일이면 같은 키 → 하루 1회
    assert notification_service.morning_dedupe_key(user, TODAY) == notification_service.morning_dedupe_key(
        user, TODAY
    )
    assert notification_service.morning_dedupe_key(user, TODAY) != notification_service.morning_dedupe_key(
        user, dt.date(2026, 8, 28)
    )

    # 연장 키는 **연장 시작 전시의 발행일**이라 기간 내내 변하지 않는다 → 기간당 1회
    assert notification_service.curator_carryover_dedupe_key(
        dt.date(2026, 8, 25)
    ) == notification_service.curator_carryover_dedupe_key(dt.date(2026, 8, 25))


# ── 시도 제한의 두 가지 셈 (API 문서 §2.10) ────────────────────────────────


@pytest.mark.parametrize(
    ("scope", "expected_lock_at"),
    [
        # 연속 실패 — 5번째 실패에서 곧바로 잠근다
        ("login", 5),
        # 시간창 — 허용량을 다 쓴 다음 시도에서 잠근다
        ("signup", 11),
        ("password_reset", 6),
        ("upload_url", 61),
    ],
)
def test_throttle_lock_threshold(scope: str, expected_lock_at: int) -> None:
    from chalicelib.services.throttle_service import POLICIES

    assert POLICIES[scope].lock_at == expected_lock_at
