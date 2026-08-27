"""S3 어댑터 (백엔드 문서 §10).

boto3는 **여기서만** import 한다. 다른 계층에서의 import는 import-linter가 막는다.
클라이언트는 사용 시점에 만든다 — 콜드 스타트에 boto3 초기화를 얹지 않기 위해서다.

버킷은 비공개이며 접근 수단은 presigned URL 하나뿐이다. CloudFront 서명 쿠키·키페어를
쓰지 않는다.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from chalicelib.config.settings import settings
from chalicelib.core.logging import get_logger

logger = get_logger("storage")


@lru_cache(maxsize=1)
def _client() -> Any:
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        endpoint_url=settings.s3_endpoint_url,
        config=Config(signature_version="s3v4", retries={"max_attempts": 2, "mode": "standard"}),
    )


def presigned_get(object_key: str, *, expires_in: int) -> str:
    """다운로드용 서명 URL (백엔드 문서 §10.2).

    서명이 URL에 담기므로 이 URL을 담은 **응답 본문은 캐시하지 않는다.** 이미지 바이트만
    브라우저·CDN 캐시가 받는다. 만료된 URL은 화면을 다시 불러오면 그대로 해소된다.
    """
    return str(
        _client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.media_bucket, "Key": object_key},
            ExpiresIn=expires_in,
        )
    )


def presigned_post(
    object_key: str,
    *,
    content_type: str,
    max_bytes: int,
    expires_in: int,
) -> dict[str, Any]:
    """업로드 자격 (백엔드 문서 §10.1).

    **presigned POST를 쓰는 이유** — 크기 상한·콘텐츠 타입·키를 서버가 서명한 정책으로
    못박을 수 있다. PUT 방식은 이 조건을 강제할 수단이 제한적이다. 20MB 파일이 API
    Gateway를 통과할 수 없다는 제약도 함께 해결된다.
    """
    return dict(
        _client().generate_presigned_post(
            Bucket=settings.media_bucket,
            Key=object_key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", 1, max_bytes],
            ],
            ExpiresIn=expires_in,
        )
    )


def get_object(object_key: str) -> bytes:
    """원본을 읽어 온다. 동기 변환 파이프라인만 이 함수를 쓴다."""
    response = _client().get_object(Bucket=settings.media_bucket, Key=object_key)
    body: bytes = response["Body"].read()
    return body


def put_object(object_key: str, *, data: bytes, content_type: str) -> None:
    _client().put_object(
        Bucket=settings.media_bucket,
        Key=object_key,
        Body=data,
        ContentType=content_type,
        # 비공개 버킷이므로 ACL을 따로 주지 않는다.
        CacheControl="private, max-age=31536000, immutable",
    )


def delete_objects(object_keys: list[str]) -> int:
    """정리 배치가 미참조 오브젝트를 회수할 때 쓴다 (백엔드 문서 §11)."""
    if not object_keys:
        return 0
    _client().delete_objects(
        Bucket=settings.media_bucket,
        Delete={"Objects": [{"Key": key} for key in object_keys], "Quiet": True},
    )
    return len(object_keys)


def list_object_keys(prefix: str) -> list[str]:
    keys: list[str] = []
    paginator = _client().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.media_bucket, Prefix=prefix):
        keys.extend(item["Key"] for item in page.get("Contents", []))
    return keys


def is_available() -> bool:
    """헬스 체크용. 예외를 밖으로 내지 않는다 — `degraded`도 200이어야 한다(PRD §8.5)."""
    try:
        _client().head_bucket(Bucket=settings.media_bucket)
        return True
    except Exception:
        logger.warning("미디어 버킷에 닿지 못했습니다", extra={"event": "storage.unavailable"})
        return False
