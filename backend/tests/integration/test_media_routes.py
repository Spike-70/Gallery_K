"""업로드·이미지 처리 — 실제 DB + 메모리 S3 (API 문서 §9.8·§9.9, 백엔드 문서 §10)."""

from __future__ import annotations

import datetime as dt
import io
from typing import Any

import pytest
from PIL import Image
from sqlalchemy.orm import Session

from chalicelib.config.constants import UPLOAD_MAX_BYTES
from chalicelib.core.errors import ErrorCode
from chalicelib.core.timeutil import freeze_time
from chalicelib.db import query as q
from chalicelib.db.models import Artwork, Exhibition, NotificationLog
from chalicelib.schemas.admin import ImageCompleteOut, UploadUrlsOut

from .factories import make_exhibition
from .fake_storage import install as install_fake_storage
from .helpers import auth_headers, curator_token, json_body

pytestmark = pytest.mark.integration

AUG_27 = dt.datetime(2026, 8, 27, 3, 0, tzinfo=dt.UTC)
TODAY = dt.date(2026, 8, 27)


@pytest.fixture()
def storage(monkeypatch: pytest.MonkeyPatch) -> Any:
    return install_fake_storage(monkeypatch)


def _jpeg(width: int = 2000, height: int = 1500) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (30, 90, 160)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _draft(session: Session) -> Exhibition:
    exhibition = q.insert(
        session,
        Exhibition,
        {"exhibition_date": TODAY, "title": "전시", "theme": "테마"},
    )
    session.commit()
    return exhibition


def _issue(client: Any, token: str, *, position: int = 1, overwrite: bool = False) -> Any:
    return client.http.post(
        "/admin/exhibitions/2026-08-27/artworks/upload-urls",
        headers=auth_headers(token),
        body=json_body(
            {
                "files": [
                    {
                        "position": position,
                        "filename": "vermeer.jpg",
                        "content_type": "image/jpeg",
                        "size_bytes": 1_200_000,
                    }
                ],
                "overwrite": overwrite,
            }
        ),
    )


def test_upload_credentials_pin_the_policy(api_client: Any, write_session: Session, storage: Any) -> None:
    _draft(write_session)
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        response = _issue(api_client, token)

    assert response.status_code == 200
    data = UploadUrlsOut.model_validate(response.json_body["data"])
    upload = data.uploads[0]
    assert upload.method == "POST"
    assert upload.position == 1
    # 업로드 착지 경로는 확정 경로와 분리되어 있다.
    assert upload.object_key.startswith("uploads/2026-08-27/")
    assert upload.fields["Content-Type"] == "image/jpeg"
    assert upload.expires_at

    artwork = q.fetch_one(write_session, Artwork, where={"position": 1})
    assert artwork is not None
    write_session.refresh(artwork)
    assert artwork.image_status == "uploading"


def test_oversized_and_wrong_type_are_refused_before_signing(
    api_client: Any, write_session: Session, storage: Any
) -> None:
    _draft(write_session)
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        too_large = api_client.http.post(
            "/admin/exhibitions/2026-08-27/artworks/upload-urls",
            headers=auth_headers(token),
            body=json_body(
                {
                    "files": [
                        {
                            "position": 1,
                            "filename": "big.jpg",
                            "content_type": "image/jpeg",
                            "size_bytes": UPLOAD_MAX_BYTES + 1,
                        }
                    ]
                }
            ),
        )
        wrong_type = api_client.http.post(
            "/admin/exhibitions/2026-08-27/artworks/upload-urls",
            headers=auth_headers(token),
            body=json_body(
                {
                    "files": [
                        {
                            "position": 1,
                            "filename": "doc.pdf",
                            "content_type": "application/pdf",
                            "size_bytes": 1000,
                        }
                    ]
                }
            ),
        )
    # 크기 상한은 스키마가 먼저 잡는다.
    assert too_large.status_code == 422
    assert wrong_type.status_code == 422


def test_occupied_slot_needs_overwrite(api_client: Any, write_session: Session, storage: Any) -> None:
    make_exhibition(write_session, TODAY, artwork_count=1)
    write_session.commit()
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        refused = _issue(api_client, token)
    assert refused.status_code == 409
    assert refused.json_body["error"]["code"] == ErrorCode.ARTWORK_SLOT_OCCUPIED
    assert refused.json_body["error"]["details"]["position"] == 1

    with freeze_time(AUG_27):
        allowed = _issue(api_client, token, overwrite=True)
    assert allowed.status_code == 200


def test_completion_processes_synchronously_and_returns_the_images(
    api_client: Any, write_session: Session, storage: Any
) -> None:
    """응답이 곧 처리 완료 통지다. 폴링하지 않는다 (API 문서 §9.9)."""
    _draft(write_session)
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        issued = _issue(api_client, token).json_body["data"]["uploads"][0]
    storage.objects[issued["object_key"]] = _jpeg()

    with freeze_time(AUG_27):
        response = api_client.http.post(
            f"/admin/artworks/{issued['artwork_id']}/image/complete",
            headers=auth_headers(token),
            body=json_body({"object_key": issued["object_key"]}),
        )

    assert response.status_code == 200
    data = ImageCompleteOut.model_validate(response.json_body["data"])
    assert data.image_status == "ready"
    assert data.images is not None
    assert data.images.width == 2000
    assert data.images.aspect_ratio == round(2000 / 1500, 4)
    assert data.images.lqip is not None and data.images.lqip.startswith("data:image/webp")

    # 확정 경로에 3종이 놓인다.
    stored = sorted(key for key in storage.objects if key.startswith("artworks/"))
    assert [key.rsplit("/", 1)[-1] for key in stored] == ["display.webp", "origin.jpg", "thumb.webp"]


def test_completion_is_idempotent(api_client: Any, write_session: Session, storage: Any) -> None:
    _draft(write_session)
    token = curator_token(api_client, write_session)
    with freeze_time(AUG_27):
        issued = _issue(api_client, token).json_body["data"]["uploads"][0]
    storage.objects[issued["object_key"]] = _jpeg()

    with freeze_time(AUG_27):
        first = api_client.http.post(
            f"/admin/artworks/{issued['artwork_id']}/image/complete",
            headers=auth_headers(token),
            body=json_body({"object_key": issued["object_key"]}),
        )
        second = api_client.http.post(
            f"/admin/artworks/{issued['artwork_id']}/image/complete",
            headers=auth_headers(token),
            body=json_body({"object_key": issued["object_key"]}),
        )
    assert first.json_body["data"]["image_status"] == "ready"
    assert second.json_body["data"]["image_status"] == "ready"


def test_a_broken_file_fails_with_a_reason_code(
    api_client: Any, write_session: Session, storage: Any
) -> None:
    """실패는 상태와 사유 코드로 돌아오며 재업로드로만 복구한다."""
    _draft(write_session)
    token = curator_token(api_client, write_session)
    with freeze_time(AUG_27):
        issued = _issue(api_client, token).json_body["data"]["uploads"][0]
    storage.objects[issued["object_key"]] = b"this is definitely not an image"

    with freeze_time(AUG_27):
        response = api_client.http.post(
            f"/admin/artworks/{issued['artwork_id']}/image/complete",
            headers=auth_headers(token),
            body=json_body({"object_key": issued["object_key"]}),
        )
    data = ImageCompleteOut.model_validate(response.json_body["data"])
    assert response.status_code == 200
    assert data.image_status == "failed"
    assert data.image_error_code == "not_an_image"
    assert data.images is None


def test_missing_origin_is_recorded_not_crashed(
    api_client: Any, write_session: Session, storage: Any
) -> None:
    _draft(write_session)
    token = curator_token(api_client, write_session)
    with freeze_time(AUG_27):
        issued = _issue(api_client, token).json_body["data"]["uploads"][0]
    # S3에 올리지 않은 채 완료를 통지한다.

    with freeze_time(AUG_27):
        response = api_client.http.post(
            f"/admin/artworks/{issued['artwork_id']}/image/complete",
            headers=auth_headers(token),
            body=json_body({"object_key": issued["object_key"]}),
        )
    assert response.json_body["data"]["image_status"] == "failed"
    assert response.json_body["data"]["image_error_code"] == "object_missing"


def test_unknown_object_key_is_refused(api_client: Any, write_session: Session, storage: Any) -> None:
    _draft(write_session)
    token = curator_token(api_client, write_session)
    with freeze_time(AUG_27):
        issued = _issue(api_client, token).json_body["data"]["uploads"][0]

    with freeze_time(AUG_27):
        response = api_client.http.post(
            f"/admin/artworks/{issued['artwork_id']}/image/complete",
            headers=auth_headers(token),
            body=json_body({"object_key": "uploads/someone-elses/key.jpg"}),
        )
    assert response.status_code == 409
    assert response.json_body["error"]["code"] == ErrorCode.UPLOAD_EXPIRED


def test_failed_image_never_counts_toward_publication(
    api_client: Any, write_session: Session, storage: Any
) -> None:
    """`ready`가 아니면 `is_complete`가 거짓이므로 발행 카운트에 잡히지 않는다 (DB 문서 §6)."""
    _draft(write_session)
    token = curator_token(api_client, write_session)
    with freeze_time(AUG_27):
        issued = _issue(api_client, token).json_body["data"]["uploads"][0]
    storage.objects[issued["object_key"]] = b"broken"
    with freeze_time(AUG_27):
        api_client.http.post(
            f"/admin/artworks/{issued['artwork_id']}/image/complete",
            headers=auth_headers(token),
            body=json_body({"object_key": issued["object_key"]}),
        )

    artwork = q.fetch_one(write_session, Artwork, where={"position": 1})
    assert artwork is not None
    write_session.refresh(artwork)
    assert artwork.is_complete is False


def test_upload_url_issuance_is_rate_limited(api_client: Any, write_session: Session, storage: Any) -> None:
    """60회 / 10분 (API 문서 §2.10)."""
    _draft(write_session)
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        for _ in range(60):
            response = _issue(api_client, token, overwrite=True)
        blocked = _issue(api_client, token, overwrite=True)

    assert response.status_code == 200
    assert blocked.status_code == 429
    assert blocked.json_body["error"]["code"] == ErrorCode.RATE_LIMITED


def test_completing_an_image_never_backfills_a_past_exhibition(
    api_client: Any, write_session: Session, storage: Any
) -> None:
    """마지막 한 점을 올려도 **과거 날짜는 발행되지 않는다** (PRD §4.3 백필 금지).

    발행 판정의 `today`가 전시의 발행일로 새면 이 경로가 백필 통로가 된다.
    """
    past = dt.date(2026, 8, 20)
    exhibition = q.insert(
        write_session,
        Exhibition,
        {"exhibition_date": past, "title": "지난 원고", "theme": "테마"},
    )
    # 11점은 이미 완성돼 있고 마지막 한 점만 이미지가 없는 상태를 만든다.
    for position in range(1, 12):
        q.insert(
            write_session,
            Artwork,
            {
                "exhibition_id": exhibition.id,
                "position": position,
                "title": f"그림 {position}",
                "artist": "작가",
                "year_text": "1665년경",
                "description": "설명",
                "image_status": "ready",
                "image_origin_key": "k/o.jpg",
                "image_display_key": "k/d.webp",
                "image_thumb_key": "k/t.webp",
                "image_width": 1600,
                "image_height": 1200,
            },
        )
    last = q.insert(
        write_session,
        Artwork,
        {
            "exhibition_id": exhibition.id,
            "position": 12,
            "title": "그림 12",
            "artist": "작가",
            "year_text": "1665년경",
            "description": "설명",
        },
    )
    write_session.commit()
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        issued = api_client.http.post(
            "/admin/exhibitions/2026-08-20/artworks/upload-urls",
            headers=auth_headers(token),
            body=json_body(
                {
                    "files": [
                        {
                            "position": 12,
                            "filename": "last.jpg",
                            "content_type": "image/jpeg",
                            "size_bytes": 1000,
                        }
                    ],
                    "overwrite": True,
                }
            ),
        ).json_body["data"]["uploads"][0]
    storage.objects[issued["object_key"]] = _jpeg()

    with freeze_time(AUG_27):
        response = api_client.http.post(
            f"/admin/artworks/{issued['artwork_id']}/image/complete",
            headers=auth_headers(token),
            body=json_body({"object_key": issued["object_key"]}),
        )

    assert response.json_body["data"]["image_status"] == "ready"
    assert issued["artwork_id"] == str(last.id)

    write_session.expire_all()
    refreshed = q.fetch_one(write_session, Exhibition, where={"id": exhibition.id})
    assert refreshed is not None
    assert refreshed.complete_artwork_count == 12
    # 조건은 모두 충족됐지만 지난 날짜이므로 발행되지 않는다.
    assert refreshed.is_published is False
    assert q.count(write_session, NotificationLog) == 0


def test_issuing_credentials_keeps_the_counter_honest(
    api_client: Any, write_session: Session, storage: Any
) -> None:
    """슬롯 행이 새로 생기면 카운터도 같은 트랜잭션에서 다시 센다 (DB 문서 §4.4).

    재계산이 빠지면 관리자 달력의 진행률이 실제 슬롯 수와 어긋난다.
    """
    exhibition = _draft(write_session)
    assert exhibition.artwork_count == 0
    token = curator_token(api_client, write_session)

    with freeze_time(AUG_27):
        api_client.http.post(
            "/admin/exhibitions/2026-08-27/artworks/upload-urls",
            headers=auth_headers(token),
            body=json_body(
                {
                    "files": [
                        {
                            "position": position,
                            "filename": f"{position}.jpg",
                            "content_type": "image/jpeg",
                            "size_bytes": 1000,
                        }
                        for position in (1, 2, 3)
                    ]
                }
            ),
        )

    write_session.expire_all()
    refreshed = q.fetch_one(write_session, Exhibition, where={"id": exhibition.id})
    assert refreshed is not None
    assert refreshed.artwork_count == 3
    assert refreshed.complete_artwork_count == 0
