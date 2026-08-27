"""로그 마스킹은 로거 필터가 자동 수행한다 (백엔드 문서 §8.3).

`caplog`를 쓰지 않는다 — `configure_logging()`이 `gallery_k` 로거의 전파를 끊기 때문에
루트로 올라오지 않는다. 대신 필터·포매터를 직접 통과시켜 결과 한 줄을 본다.
"""

from __future__ import annotations

import json
import logging

from chalicelib.core.logging import JsonFormatter, SensitiveDataFilter


def _emit(event: str, **fields: object) -> dict:
    record = logging.LogRecord(
        name="gallery_k.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=str(fields.pop("message", event)),
        args=(),
        exc_info=None,
    )
    record.event = event
    record.fields = fields
    SensitiveDataFilter().filter(record)
    return json.loads(JsonFormatter().format(record))


def test_phone_is_masked_as_a_field_and_inside_free_text() -> None:
    payload = _emit("auth.login.failed", message="01012345678 로 시도했습니다", phone="01012345678")
    assert payload["phone"] == "010-****-5678"
    assert "01012345678" not in json.dumps(payload, ensure_ascii=False)


def test_hyphenated_phone_in_text_is_masked_too() -> None:
    payload = _emit("member.note", memo="연락처는 010-1234-5678 입니다")
    assert "010-1234-5678" not in payload["memo"]
    assert "010-****-5678" in payload["memo"]


def test_credentials_are_removed_not_masked() -> None:
    payload = _emit(
        "auth.signup",
        password="hunter2",
        password_hash="$2b$12$abcdef",
        keys={"p256dh": "public", "auth": "secret"},
        endpoint="https://fcm.googleapis.com/very/long/token",
    )
    assert payload["password"] == "[redacted]"
    assert payload["password_hash"] == "[redacted]"
    assert payload["keys"] == {"p256dh": "[redacted]", "auth": "[redacted]"}
    assert payload["endpoint"] == "[redacted]"


def test_binary_is_summarised_not_written() -> None:
    payload = _emit("image.process", blob=b"\x00" * 2048)
    assert payload["blob"] == "[binary 2048 bytes]"


def test_output_carries_the_required_fields() -> None:
    payload = _emit("request.end", status=200, duration_ms=12)
    for required in ("time", "level", "event", "request_id", "method", "path", "actor_id", "status"):
        assert required in payload


def test_output_is_a_single_line() -> None:
    record = logging.LogRecord(
        name="gallery_k.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="여러 줄이\n들어와도",
        args=(),
        exc_info=None,
    )
    SensitiveDataFilter().filter(record)
    assert "\n" not in JsonFormatter().format(record)
