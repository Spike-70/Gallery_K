"""통합 테스트용 데이터 생성기.

전시 한 건을 12점 완성 상태로 만드는 일이 여러 테스트에 반복되므로 한 곳에 모은다.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy.orm import Session

from chalicelib.config.constants import ARTWORK_COUNT
from chalicelib.db import query as q
from chalicelib.db.models import Artwork, Exhibition
from chalicelib.db.models.enums import ImageStatus


def make_exhibition(
    session: Session,
    day: dt.date,
    *,
    title: str = "빛을 등진 사람들",
    theme: str = "테마 본문",
    published: bool = True,
    hidden: bool = False,
    artwork_count: int = ARTWORK_COUNT,
    artists: list[str] | None = None,
) -> Exhibition:
    published_at = dt.datetime.combine(day, dt.time(7, 0), tzinfo=dt.UTC) if published else None
    exhibition = q.insert(
        session,
        Exhibition,
        {
            "exhibition_date": day,
            "title": title,
            "theme": theme,
            "is_published": published,
            "published_at": published_at,
            "is_hidden": hidden,
            "hidden_at": published_at if hidden else None,
            "artwork_count": artwork_count,
            "complete_artwork_count": artwork_count if published else 0,
        },
    )
    for position in range(1, artwork_count + 1):
        make_artwork(
            session,
            exhibition,
            position,
            artist=(artists[(position - 1) % len(artists)] if artists else f"작가{position}"),
        )
    session.flush()
    return exhibition


def make_artwork(
    session: Session,
    exhibition: Exhibition,
    position: int,
    *,
    artist: str = "요하네스 페르메이르",
    ready: bool = True,
    **extra: Any,
) -> Artwork:
    image_fields: dict[str, Any] = {}
    if ready:
        key = f"artworks/{exhibition.exhibition_date}/{position}"
        image_fields = {
            "image_status": ImageStatus.READY,
            "image_origin_key": f"{key}/origin.jpg",
            "image_display_key": f"{key}/display.webp",
            "image_thumb_key": f"{key}/thumb.webp",
            "image_lqip": "data:image/webp;base64,AAAA",
            "image_width": 1600,
            "image_height": 1200,
            "image_bytes": 123456,
            "image_mime": "image/jpeg",
        }
    return q.insert(
        session,
        Artwork,
        {
            "exhibition_id": exhibition.id,
            "position": position,
            "title": f"그림 {position}",
            "artist": artist,
            "year_text": "1665년경",
            "description": "큐레이터가 쓴 설명입니다.",
            "collection": "마우리츠하위스 미술관",
            "source_url": "https://example.org/artwork",
            **image_fields,
            **extra,
        },
    )
