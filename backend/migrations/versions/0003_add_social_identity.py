"""소셜 로그인 — `social_identity` 테이블과 비밀번호 선택화 (소셜 문서 §5.1)

리비전 ID: 0003
이전 리비전: 0002

바꾸는 것은 셋이다.

  1. **신규 `social_identity`** — DB 문서 §11이 예약해 둔 확장 훅 그대로다.
     신원은 `(provider, provider_uid)` 복합 UNIQUE 하나뿐이며, 이메일로 계정을
     병합하지 않는다 — 제공자가 이메일 소유를 검증하지 않으면 그 병합이 곧 계정
     탈취 경로가 된다.

  2. **`app_user.password_hash` NOT NULL 해제** — 소셜로만 가입한 회원은 비밀번호가
     없다. 기존 행은 전부 값이 있으므로 데이터 이전이 필요 없다.

  3. **`created_via` CHECK에 `social` 추가** — 값 추가가 마이그레이션 한 줄로 끝나도록
     네이티브 ENUM 대신 `text` + CHECK을 쓴 설계의 이점을 그대로 쓴다(DB 문서 §5).

`app_user.phone`은 **건드리지 않는다.** 소셜 가입도 A-4 연결 화면에서 전화번호를
받으므로 `NOT NULL`·UNIQUE가 그대로 성립한다(소셜 문서 SA-2).

다운그레이드는 비밀번호 없는 계정이 있으면 실패한다. 그것이 맞다 — 임의의 비밀번호를
채워 넣으면 로그인할 수 없는 계정이 조용히 생긴다.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "social_identity",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_uid", sa.String(length=191), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "provider IN ('kakao', 'google')", name=op.f("ck_social_identity_provider")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app_user.id"],
            name=op.f("fk_social_identity_user_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_social_identity")),
        sa.UniqueConstraint(
            "provider", "provider_uid", name=op.f("uq_social_identity_provider_uid")
        ),
    )
    op.create_index(
        op.f("ix_social_identity_user_id"), "social_identity", ["user_id"], unique=False
    )

    op.alter_column("app_user", "password_hash", existing_type=sa.String(length=72), nullable=True)

    op.drop_constraint(op.f("ck_app_user_created_via"), "app_user", type_="check")
    op.create_check_constraint(
        op.f("ck_app_user_created_via"),
        "app_user",
        "created_via IN ('self', 'curator', 'social')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_app_user_created_via"), "app_user", type_="check")
    op.execute("DELETE FROM social_identity")
    # 소셜 전용 계정이 남아 있으면 여기서 멈춘다. 비밀번호를 임의로 채우면
    # 로그인할 수 없는 계정이 조용히 생기므로, 운영자가 먼저 결정해야 한다.
    op.alter_column("app_user", "password_hash", existing_type=sa.String(length=72), nullable=False)
    op.create_check_constraint(
        op.f("ck_app_user_created_via"), "app_user", "created_via IN ('self', 'curator')"
    )
    op.drop_index(op.f("ix_social_identity_user_id"), table_name="social_identity")
    op.drop_table("social_identity")
