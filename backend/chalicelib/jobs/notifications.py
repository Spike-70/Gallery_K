"""알림 발송 루틴 (백엔드 문서 §11).

발송 예정 시각이 지난 대기 행을 배치 처리한다.

  * 4xx 응답이면 구독을 비활성화한다 (구독이 사라진 것이다)
  * 5xx면 재시도를 누적하고 상한을 넘기면 실패로 종료한다
  * 컷오프 초과분은 발송하지 않고 스킵으로 기록한다

**중복 기동은 무해하다** — `dedupe_key` 유니크와 조건부 상태 갱신이 함께 막는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from chalicelib.config.constants import NOTIFICATION_SEND_BATCH_SIZE
from chalicelib.core.logging import get_logger, log_event
from chalicelib.core.timeutil import now_utc
from chalicelib.db.models.enums import NotificationSkipReason
from chalicelib.integrations import webpush
from chalicelib.services import notification_service, push_service

logger = get_logger("job.notifications")


@dataclass(frozen=True, slots=True)
class DispatchReport:
    considered: int = 0
    sent: int = 0
    skipped: int = 0
    failed: int = 0
    deactivated: int = 0


def dispatch_due_notifications(session_factory: object | None = None) -> DispatchReport:
    from chalicelib.db import engine as engine_module

    factory = session_factory or engine_module.open_session
    session = factory()  # type: ignore[operator]
    now = now_utc()
    considered = sent = skipped = failed = deactivated = 0

    try:
        pending = notification_service.due_notifications(session, now=now, limit=NOTIFICATION_SEND_BATCH_SIZE)
        considered = len(pending)
        # 배치 전원의 구독을 **한 번에** 가져온다. 알림마다 조회하면 회원 수만큼
        # 질의가 늘어나고, 그 질의는 발송 지연으로 그대로 드러난다.
        subscriptions_by_user = push_service.active_subscriptions_for(
            session, [row.user_id for row in pending]
        )

        for notification in pending:
            if not notification_service.claim(session, notification.id):
                # 다른 인스턴스가 먼저 집었다. 무해하게 넘어간다.
                continue

            if notification_service.is_past_cutoff(session, notification, now=now):
                notification_service.mark_skipped(
                    session, notification.id, reason=NotificationSkipReason.CUTOFF_PASSED
                )
                skipped += 1
                continue

            subscriptions = subscriptions_by_user.get(notification.user_id, [])
            if not subscriptions:
                notification_service.mark_skipped(
                    session, notification.id, reason=NotificationSkipReason.NO_SUBSCRIPTION
                )
                skipped += 1
                continue

            title, body, tag = notification_service.notification_content(session, notification)
            payload = webpush.build_payload(title=title, body=body, tag=tag)

            delivered = False
            last_error = ""
            for subscription in subscriptions:
                result = webpush.send(
                    webpush.Subscription(
                        endpoint=subscription.endpoint,
                        p256dh=subscription.p256dh,
                        auth=subscription.auth,
                    ),
                    payload,
                )
                if result.outcome == "sent":
                    push_service.register_success(session, subscription.id)
                    delivered = True
                elif result.is_permanent_failure:
                    push_service.register_failure(session, subscription.id, permanent=True)
                    deactivated += 1
                    last_error = result.detail or "gone"
                elif result.outcome == "disabled":
                    last_error = result.detail or "disabled"
                else:
                    push_service.register_failure(session, subscription.id, permanent=False)
                    last_error = result.detail or "retryable"

            if delivered:
                notification_service.mark_sent(session, notification.id)
                sent += 1
            elif last_error in {"disabled", "VAPID 키가 설정되지 않았습니다"}:
                notification_service.mark_skipped(
                    session, notification.id, reason=NotificationSkipReason.NO_SUBSCRIPTION
                )
                skipped += 1
            else:
                notification_service.release(session, notification.id, error=last_error)
                failed += 1

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    report = DispatchReport(
        considered=considered,
        sent=sent,
        skipped=skipped,
        failed=failed,
        deactivated=deactivated,
    )
    # 처리 0건도 남긴다 — 잡이 죽었는지 알 수 있어야 한다.
    log_event(
        logger,
        "job.notifications.finished",
        considered=report.considered,
        sent=report.sent,
        skipped=report.skipped,
        failed=report.failed,
        deactivated=report.deactivated,
    )
    return report
