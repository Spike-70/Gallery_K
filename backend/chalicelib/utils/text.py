"""문자열 정규화 — 도메인을 모르는 순수 함수."""

from __future__ import annotations

import hashlib
import re
import unicodedata

_NON_DIGIT = re.compile(r"\D")


def normalize_phone(value: str) -> str:
    """하이픈·공백을 제거해 저장 형식(숫자만)으로 만든다 (API 문서 §6.3)."""
    return _NON_DIGIT.sub("", value or "")


def mask_phone(value: str | None) -> str:
    """`010-****-5678`. 관람자 응답과 로그에 쓰는 유일한 전화번호 표현이다.

    관리자 응답(`MemberItem.phone`)만 전체 번호를 반환한다 (API 문서 §3.6·§3.8).
    """
    digits = normalize_phone(value or "")
    if len(digits) < 7:
        return "***"
    head, tail = digits[:3], digits[-4:]
    return f"{head}-****-{tail}"


def normalize_text(value: str | None) -> str | None:
    """유니코드 정규화 + 양끝 공백 제거. 빈 문자열은 None으로 접는다.

    "값 없음"의 표현을 하나로 모으는 것이 목적이다 — 빈 문자열과 NULL이 섞이면
    `has_title` 같은 파생 판정이 두 가지 방식으로 갈린다.
    """
    if value is None:
        return None
    normalized = unicodedata.normalize("NFC", value).strip()
    return normalized or None


def sha256_hex(value: str) -> str:
    """푸시 엔드포인트 해시 등. 엔드포인트 원문은 인덱스 상한을 넘길 수 있다 (DB 문서 §4.3)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def safe_extension(filename: str, fallback: str) -> str:
    """업로드 파일명에서 확장자만 뽑는다. 경로·제어문자를 신뢰하지 않는다."""
    base = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if "." not in base:
        return fallback
    ext = "." + base.rsplit(".", 1)[-1].lower()
    return ext if re.fullmatch(r"\.[a-z0-9]{1,8}", ext) else fallback
