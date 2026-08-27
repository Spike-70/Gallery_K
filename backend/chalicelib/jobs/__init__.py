"""스케줄 루틴 (백엔드 문서 §11).

스케줄 핸들러는 **하나**이며 두 가지 일을 한다 — 짧은 주기의 알림 발송과 하루 1회의
야간 정리. 여기 있는 함수들이 그 본문이고, `app.py`는 선언만 한다.

모든 루틴은 **멱등하며 처리 0건도 로그를 남긴다** — 잡이 죽었는지 알 수 있어야 한다.
"""

from chalicelib.jobs.nightly import run_nightly_maintenance
from chalicelib.jobs.notifications import dispatch_due_notifications

__all__ = ["dispatch_due_notifications", "run_nightly_maintenance"]
