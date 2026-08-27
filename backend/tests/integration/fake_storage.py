"""메모리 S3 대역.

외부 어댑터는 `integrations/storage.py` 하나이므로, 그 모듈의 함수만 바꿔치면 위 계층
전부가 실제 코드 그대로 돈다 — 이것이 어댑터를 한 곳에 모아 둔 대가다.
"""

from __future__ import annotations

import hashlib
from typing import Any


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}
        self.deleted: list[str] = []

    # ── storage 모듈과 같은 시그니처 ──────────────────────────────────────
    def presigned_get(self, object_key: str, *, expires_in: int) -> str:
        token = hashlib.sha256(object_key.encode()).hexdigest()[:16]
        return f"https://media.test/{object_key}?X-Amz-Signature={token}&X-Amz-Expires={expires_in}"

    def presigned_post(
        self, object_key: str, *, content_type: str, max_bytes: int, expires_in: int
    ) -> dict[str, Any]:
        return {
            "url": "https://media.test/upload",
            "fields": {
                "key": object_key,
                "Content-Type": content_type,
                "policy": "signed-policy",
                "x-amz-signature": "signature",
            },
        }

    def get_object(self, object_key: str) -> bytes:
        if object_key not in self.objects:
            raise FileNotFoundError(object_key)
        return self.objects[object_key]

    def put_object(self, object_key: str, *, data: bytes, content_type: str) -> None:
        self.objects[object_key] = data
        self.content_types[object_key] = content_type

    def delete_objects(self, object_keys: list[str]) -> int:
        for key in object_keys:
            self.objects.pop(key, None)
            self.deleted.append(key)
        return len(object_keys)

    def list_object_keys(self, prefix: str) -> list[str]:
        return [key for key in self.objects if key.startswith(prefix)]

    def is_available(self) -> bool:
        return True


def install(monkeypatch: Any) -> FakeStorage:
    from chalicelib.integrations import storage

    fake = FakeStorage()
    for name in (
        "presigned_get",
        "presigned_post",
        "get_object",
        "put_object",
        "delete_objects",
        "list_object_keys",
        "is_available",
    ):
        monkeypatch.setattr(storage, name, getattr(fake, name))
    return fake
