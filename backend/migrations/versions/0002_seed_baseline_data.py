"""기준 데이터 시드 — 큐레이터 계정과 전역 설정 (DB 문서 §9)

리비전 ID: 0002
이전 리비전: 0001

**멱등하다.** 이미 있으면 건드리지 않으므로 몇 번을 다시 돌려도 같다.

시드용 환경변수가 없으면 이 리비전은 **실패한다** — 큐레이터 없는 배포는 동작 불가
상태이고, 그것을 배포가 끝난 뒤에 발견하게 두지 않는다.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from chalicelib.config.settings import load_seed_settings
from chalicelib.core.ids import new_id
from chalicelib.core.security import hash_password
from chalicelib.core.timeutil import now_utc
from chalicelib.utils.text import normalize_phone

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


#: 전역 설정 시드 (DB 문서 §4.9). (키, 값, 타입, 설명, 변경 가능)
#: **배포로만 바뀌는 값은 환경변수, 운영 중 조정되는 값은 이 표다.**
SETTINGS: tuple[tuple[str, object, str, str, bool], ...] = (
    ("signup_open", True, "boolean", "신규 가입 허용 여부. B-3 화면의 스위치가 이 값을 바꾼다.", True),
    ("notify_default_time", "07:30", "string", "가입 시 기본 아침 알림 시각(KST).", True),
    ("notify_cutoff_hour", 21, "number", "이 시각(KST)을 넘긴 발행분은 알림을 보내지 않는다.", True),
    ("carryover_alert_days", 2, "number", "연장이 이만큼 연속되면 큐레이터에게 1회 알린다.", True),
    ("archive_size", 30, "number", "지난 전시 목록에 노출할 전시 수 상한.", True),
    ("admin_calendar_days", 7, "number", "관리자 달력의 기본 조회 일수.", True),
    ("log_retention_days", 180, "number", "관람 기록 보존 일수. 야간 배치가 초과분을 지운다.", True),
    ("media_url_ttl_seconds", 900, "number", "이미지 presigned GET URL의 유효 기간.", True),
    ("maintenance_mode", False, "boolean", "점검 모드. 공개·시스템 경로 외를 차단한다.", True),
    ("session_ttl_days", 90, "number", "세션 쿠키 유효 기간.", True),
)


def upgrade() -> None:
    seed = load_seed_settings()
    connection = op.get_bind()
    now = now_utc()

    for key, value, value_type, description, is_mutable in SETTINGS:
        connection.execute(
            sa.text(
                "INSERT INTO app_setting "
                "(key, value, value_type, description, is_mutable, created_at, updated_at) "
                "VALUES (:key, CAST(:value AS jsonb), :value_type, :description, :is_mutable, "
                ":now, :now) "
                "ON CONFLICT (key) DO NOTHING"
            ),
            {
                "key": key,
                "value": json.dumps(value),
                "value_type": value_type,
                "description": description,
                "is_mutable": is_mutable,
                "now": now,
            },
        )

    # 큐레이터는 1건뿐이다. 부분 유니크 인덱스가 두 번째를 막는다.
    connection.execute(
        sa.text(
            "INSERT INTO app_user "
            "(id, phone, password_hash, name, role, token_version, must_change_password, "
            " notify_enabled, notify_at, font_scale, is_blocked, created_via, created_at, updated_at) "
            "VALUES (:id, :phone, :password_hash, :name, 'curator', 0, true, "
            " true, '07:30', 'normal', false, 'curator', :now, :now) "
            "ON CONFLICT (phone) DO NOTHING"
        ),
        {
            "id": new_id(),
            "phone": normalize_phone(seed.curator_phone),
            "password_hash": hash_password(seed.curator_password),
            "name": seed.curator_name,
            "now": now,
        },
    )


def downgrade() -> None:
    seed = load_seed_settings()
    connection = op.get_bind()
    connection.execute(
        sa.text("DELETE FROM app_user WHERE phone = :phone AND role = 'curator'"),
        {"phone": normalize_phone(seed.curator_phone)},
    )
    connection.execute(
        sa.text("DELETE FROM app_setting WHERE key = ANY(:keys)"),
        {"keys": [key for key, *_ in SETTINGS]},
    )
