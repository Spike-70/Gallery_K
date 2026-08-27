"""웹 푸시 어댑터 (백엔드 문서 §11).

외부 HTTP는 **여기서만** 나간다. 발송 결과를 상태 코드가 아니라 **의미**로 돌려주는 것이
이 어댑터의 역할이다 — 상위 계층이 404/410/5xx를 해석하고 있으면 그 지식이 두 곳에 생긴다.

알림 문구는 전시 제목까지만 담고 클릭 시 첫 화면으로 보낸다. 같은 날 배너가 쌓이지
않도록 태그를 지정한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from chalicelib.config.constants import PUSH_TTL_SECONDS
from chalicelib.config.settings import settings
from chalicelib.core.logging import get_logger, log_event

logger = get_logger("webpush")

DeliveryOutcome = Literal["sent", "gone", "retryable", "disabled"]


@dataclass(frozen=True, slots=True)
class Subscription:
    endpoint: str
    p256dh: str
    auth: str


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    outcome: DeliveryOutcome
    detail: str | None = None

    @property
    def is_permanent_failure(self) -> bool:
        """4xx는 구독이 사라졌다는 뜻이다 — 즉시 비활성화한다."""
        return self.outcome == "gone"

    @property
    def should_retry(self) -> bool:
        return self.outcome == "retryable"


def build_payload(*, title: str, body: str, tag: str) -> str:
    return json.dumps(
        {
            "title": title,
            "body": body,
            "tag": tag,
            # 모든 진입이 첫 화면을 거친다 (PRD §6.12).
            "url": "/",
        },
        ensure_ascii=False,
    )


def send(subscription: Subscription, payload: str) -> DeliveryResult:
    if not settings.push_enabled:
        # VAPID 키가 없으면 발송을 시도하지 않는다. 로컬 개발에서 조용히 건너뛴다.
        return DeliveryResult("disabled", "VAPID 키가 설정되지 않았습니다")

    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=payload,
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
            ttl=PUSH_TTL_SECONDS,
        )
        return DeliveryResult("sent")
    except WebPushException as exc:
        return _classify(exc)
    except Exception as exc:
        log_event(logger, "push.unexpected_error", message=str(exc))
        return DeliveryResult("retryable", str(exc))


def _classify(exc: Any) -> DeliveryResult:
    """404·410은 구독 소멸, 그 밖의 4xx도 재시도해봐야 같다. 5xx만 재시도한다."""
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status is None:
        return DeliveryResult("retryable", str(exc))
    if status in {404, 410}:
        return DeliveryResult("gone", f"HTTP {status}")
    if 400 <= status < 500:
        return DeliveryResult("gone", f"HTTP {status}")
    return DeliveryResult("retryable", f"HTTP {status}")
