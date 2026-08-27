"""식별자 생성 — 도메인을 모르는 순수 함수.

  * PK는 애플리케이션이 만드는 **UUIDv7** (DB 문서 §2). 시간 정렬성이 있어 인덱스
    삽입이 말단에 몰리고, 생성 순서가 그대로 정렬 순서가 된다.
  * 요청 ID는 **26자 ULID** (API 문서 §2.3).

외부 라이브러리를 쓰지 않는다. 배포 패키지를 키우지 않으려는 것이고(백엔드 문서 §14),
두 형식 모두 표준 명세를 그대로 옮기면 되는 크기다.

`utils`가 아니라 `core`에 두는 이유 — 두 형식 모두 **시각 성분**을 담고, 시각은
`core.timeutil` 하나에서만 나와야 한다(문서 §8.4). 테스트가 시계를 고정하면 식별자의
시간 성분도 함께 고정되어 날짜 경계 검증이 성립한다.
"""

from __future__ import annotations

import os
import secrets
import uuid
from typing import Final

from chalicelib.core.timeutil import now_utc

#: Crockford Base32 — 사람이 옮겨 적을 때 헷갈리는 I·L·O·U를 뺀 배열
_CROCKFORD: Final = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

_ULID_TIME_CHARS: Final = 10
_ULID_RANDOM_CHARS: Final = 16
ULID_LENGTH: Final = _ULID_TIME_CHARS + _ULID_RANDOM_CHARS


def _now_ms() -> int:
    return int(now_utc().timestamp() * 1000)


def uuid7(*, timestamp_ms: int | None = None) -> uuid.UUID:
    """RFC 9562 UUID version 7.

    레이아웃: 48비트 밀리초 타임스탬프 · 4비트 버전 · 12비트 난수 · 2비트 변형 · 62비트 난수
    """
    ms = _now_ms() if timestamp_ms is None else timestamp_ms
    if not 0 <= ms < (1 << 48):
        raise ValueError("UUIDv7 타임스탬프가 48비트를 벗어납니다")

    rand = int.from_bytes(os.urandom(10), "big")
    rand_a = (rand >> 62) & 0x0FFF
    rand_b = rand & ((1 << 62) - 1)

    value = ms << 80
    value |= 0x7 << 76  # version
    value |= rand_a << 64
    value |= 0b10 << 62  # variant
    value |= rand_b
    return uuid.UUID(int=value)


def new_id() -> uuid.UUID:
    """모든 테이블 PK의 생성 지점."""
    return uuid7()


def _encode_crockford(value: int, length: int) -> str:
    chars = []
    for _ in range(length):
        chars.append(_CROCKFORD[value & 0x1F])
        value >>= 5
    return "".join(reversed(chars))


def new_request_id(*, timestamp_ms: int | None = None) -> str:
    """26자 ULID. 응답 `meta.request_id` 및 `X-Request-Id` 헤더에 그대로 실린다."""
    ms = _now_ms() if timestamp_ms is None else timestamp_ms
    return _encode_crockford(ms, _ULID_TIME_CHARS) + _encode_crockford(
        secrets.randbits(80), _ULID_RANDOM_CHARS
    )


def parse_uuid(value: str) -> uuid.UUID | None:
    """경로 변수 검증용. 형식이 아니면 예외 대신 None을 준다 — 부재로 응답하기 위함이다."""
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None
