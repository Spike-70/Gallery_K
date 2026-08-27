"""그림 단건 조회 (API 문서 §7.5).

`db/queries/`가 아니라 서비스에 두는 이유 — 공용 헬퍼로 표현되는 질의이고, 여기 있는 것은
질의가 아니라 **"관람자에게 보이는 그림"의 정의**다.
"""

from __future__ import annotations

import datetime as _dt
import uuid

from sqlalchemy.orm import Session

from chalicelib.db import query as q
from chalicelib.db.models import Artwork, Exhibition
from chalicelib.services.exhibition_service import VISIBLE


def find_visible_artwork(
    session: Session, artwork_id: uuid.UUID, *, today: _dt.date
) -> tuple[Artwork, Exhibition] | None:
    """미발행·숨김·미래 발행일 전시의 그림은 전부 부재로 취급한다.

    관계 경로 필터가 조인을 자동 구성하므로 그림과 전시를 한 번에 확인한다.
    """
    artwork = q.fetch_one(session, Artwork, where={"id": artwork_id})
    if artwork is None:
        return None

    exhibition = q.fetch_one(
        session,
        Exhibition,
        where={**VISIBLE, "id": artwork.exhibition_id, "exhibition_date__lte": today},
    )
    if exhibition is None:
        return None
    return artwork, exhibition
