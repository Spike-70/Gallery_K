"""초기 스키마 — 테이블 11종 (DB 문서 §4)

리비전 ID: 0001
이전 리비전: 없음 (히스토리의 시작)

`--autogenerate` 결과를 그대로 쓰지 않는다(DB 문서 §9). 수기로 보정한 것:

  * **확장 생성** — `pg_trgm`(이름 부분 검색), `btree_gist`(공지 기간 중첩 EXCLUDE).
    autogenerate가 감지하지 못하며, 없으면 이 리비전 자체가 실패한다.

나머지(부분 인덱스 5종 · EXCLUDE 제약 · 생성 컬럼 `artwork.is_complete` ·
DEFERRABLE 슬롯 유니크)는 생성 결과를 검토해 그대로 채택했다. 검증은
`tests/integration/test_migrations.py`가 마이그레이션 적용 결과와 모델 metadata를
대조하는 방식으로 한다 — 차이가 있으면 실패한다.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 확장이 먼저다 — 아래 인덱스·제약이 이 둘에 의존한다.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table('app_user',
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('phone', sa.String(length=11), nullable=False),
    sa.Column('password_hash', sa.String(length=72), nullable=False),
    sa.Column('name', sa.String(length=20), nullable=False),
    sa.Column('role', sa.String(length=10), server_default=sa.text("'viewer'"), nullable=False),
    sa.Column('token_version', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('must_change_password', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('notify_enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('notify_at', sa.Time(), server_default=sa.text("'07:30'"), nullable=False),
    sa.Column('font_scale', sa.String(length=10), server_default=sa.text("'normal'"), nullable=False),
    sa.Column('is_blocked', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('blocked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('blocked_reason', sa.String(length=200), nullable=True),
    sa.Column('created_via', sa.String(length=10), server_default=sa.text("'self'"), nullable=False),
    sa.CheckConstraint("created_via IN ('self', 'curator')", name=op.f('ck_app_user_created_via')),
    sa.CheckConstraint("font_scale IN ('normal', 'large')", name=op.f('ck_app_user_font_scale')),
    sa.CheckConstraint("phone ~ '^01[0-9]{8,9}$'", name=op.f('ck_app_user_phone_format')),
    sa.CheckConstraint("role IN ('viewer', 'curator')", name=op.f('ck_app_user_role')),
    sa.CheckConstraint('(is_blocked AND blocked_at IS NOT NULL) OR (NOT is_blocked AND blocked_at IS NULL)', name=op.f('ck_app_user_blocked_consistency')),
    sa.CheckConstraint('token_version >= 0', name=op.f('ck_app_user_token_version')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_app_user')),
    sa.UniqueConstraint('phone', name='uq_app_user_phone')
    )
    op.create_index('ix_app_user_created_at', 'app_user', [sa.literal_column('created_at DESC')], unique=False)
    op.create_index('ix_app_user_name_trgm', 'app_user', ['name'], unique=False, postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.create_index('ix_app_user_notify_target', 'app_user', ['notify_at'], unique=False, postgresql_where=sa.text('notify_enabled AND NOT is_blocked'))
    op.create_index('uq_app_user_single_curator', 'app_user', ['role'], unique=True, postgresql_where=sa.text("role = 'curator'"))
    op.create_table('auth_throttle',
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('throttle_key', sa.String(length=120), nullable=False),
    sa.Column('scope', sa.String(length=20), nullable=False),
    sa.Column('fail_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('first_failed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_failed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("scope IN ('login', 'signup', 'password_reset', 'upload_url')", name=op.f('ck_auth_throttle_scope')),
    sa.CheckConstraint('fail_count >= 0', name=op.f('ck_auth_throttle_fail_count')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_auth_throttle')),
    sa.UniqueConstraint('throttle_key', name='uq_auth_throttle_throttle_key')
    )
    op.create_index('ix_auth_throttle_locked_until', 'auth_throttle', ['locked_until'], unique=False)
    op.create_table('app_setting',
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('key', sa.String(length=60), nullable=False),
    sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('value_type', sa.String(length=10), nullable=False),
    sa.Column('description', sa.String(length=200), server_default=sa.text("''"), nullable=False),
    sa.Column('is_mutable', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.CheckConstraint("value_type IN ('string', 'number', 'boolean')", name=op.f('ck_app_setting_value_type')),
    sa.ForeignKeyConstraint(['updated_by'], ['app_user.id'], name='fk_app_setting_updated_by', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('key', name=op.f('pk_app_setting'))
    )
    op.create_table('audit_log',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('actor_id', sa.Uuid(), nullable=True),
    sa.Column('actor_role', sa.String(length=10), nullable=True),
    sa.Column('action', sa.String(length=60), nullable=False),
    sa.Column('target_type', sa.String(length=40), nullable=True),
    sa.Column('target_id', sa.String(length=64), nullable=True),
    sa.Column('summary', sa.String(length=300), nullable=True),
    sa.Column('changes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('request_id', sa.String(length=26), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['app_user.id'], name='fk_audit_log_actor_id', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_log'))
    )
    op.create_index('ix_audit_log_created_at', 'audit_log', [sa.literal_column('created_at DESC')], unique=False)
    op.create_index('ix_audit_log_target', 'audit_log', ['target_type', 'target_id'], unique=False)
    op.create_table('exhibition',
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('exhibition_date', sa.Date(), nullable=False),
    sa.Column('title', sa.String(length=20), nullable=True),
    sa.Column('theme', sa.String(length=500), nullable=True),
    sa.Column('is_published', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_hidden', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('hidden_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('hidden_reason', sa.String(length=200), nullable=True),
    sa.Column('draft_updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('artwork_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('complete_artwork_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.CheckConstraint('(is_hidden AND hidden_at IS NOT NULL) OR (NOT is_hidden AND hidden_at IS NULL)', name=op.f('ck_exhibition_hidden_consistency')),
    sa.CheckConstraint('(is_published AND published_at IS NOT NULL) OR (NOT is_published AND published_at IS NULL)', name=op.f('ck_exhibition_published_consistency')),
    sa.CheckConstraint('artwork_count BETWEEN 0 AND 12', name=op.f('ck_exhibition_artwork_count_range')),
    sa.CheckConstraint('complete_artwork_count <= artwork_count', name=op.f('ck_exhibition_complete_not_over_total')),
    sa.CheckConstraint('complete_artwork_count BETWEEN 0 AND 12', name=op.f('ck_exhibition_complete_artwork_count_range')),
    sa.ForeignKeyConstraint(['created_by'], ['app_user.id'], name='fk_exhibition_created_by', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_exhibition')),
    sa.UniqueConstraint('exhibition_date', name='uq_exhibition_date')
    )
    op.create_index('ix_exhibition_visible', 'exhibition', [sa.literal_column('exhibition_date DESC')], unique=False, postgresql_where=sa.text('is_published AND NOT is_hidden'))
    op.create_table('notice',
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('starts_on', sa.Date(), nullable=False),
    sa.Column('ends_on', sa.Date(), nullable=False),
    sa.Column('body', sa.String(length=300), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    postgresql.ExcludeConstraint((sa.text("daterange(starts_on, ends_on, '[]')"), '&&'), where=sa.text('is_active'), using='gist', name='ex_notice_active_period'),
    sa.CheckConstraint('ends_on >= starts_on', name=op.f('ck_notice_period_order')),
    sa.ForeignKeyConstraint(['created_by'], ['app_user.id'], name='fk_notice_created_by', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notice'))
    )
    op.create_index('ix_notice_period', 'notice', ['starts_on', 'ends_on'], unique=False, postgresql_where=sa.text('is_active'))
    op.create_table('push_subscription',
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('endpoint', sa.String(length=2048), nullable=False),
    sa.Column('endpoint_hash', sa.String(length=64), nullable=False),
    sa.Column('p256dh', sa.String(length=255), nullable=False),
    sa.Column('auth', sa.String(length=255), nullable=False),
    sa.Column('platform', sa.String(length=10), server_default=sa.text("'unknown'"), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('failure_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("platform IN ('ios', 'android', 'desktop', 'unknown')", name=op.f('ck_push_subscription_platform')),
    sa.CheckConstraint('failure_count >= 0', name=op.f('ck_push_subscription_failure_count')),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name='fk_push_subscription_user_id', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_push_subscription')),
    sa.UniqueConstraint('endpoint_hash', name='uq_push_subscription_endpoint_hash')
    )
    op.create_index('ix_push_subscription_user_active', 'push_subscription', ['user_id'], unique=False, postgresql_where=sa.text('is_active'))
    op.create_table('artwork',
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('exhibition_id', sa.Uuid(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=20), nullable=True),
    sa.Column('artist', sa.String(length=40), nullable=True),
    sa.Column('year_text', sa.String(length=20), nullable=True),
    sa.Column('description', sa.String(length=300), nullable=True),
    sa.Column('collection', sa.String(length=60), nullable=True),
    sa.Column('source_url', sa.String(length=500), nullable=True),
    sa.Column('image_status', sa.String(length=10), server_default=sa.text("'empty'"), nullable=False),
    sa.Column('image_origin_key', sa.String(length=255), nullable=True),
    sa.Column('image_display_key', sa.String(length=255), nullable=True),
    sa.Column('image_thumb_key', sa.String(length=255), nullable=True),
    sa.Column('image_lqip', sa.String(length=4000), nullable=True),
    sa.Column('image_width', sa.Integer(), nullable=True),
    sa.Column('image_height', sa.Integer(), nullable=True),
    sa.Column('image_bytes', sa.Integer(), nullable=True),
    sa.Column('image_mime', sa.String(length=30), nullable=True),
    sa.Column('image_error_code', sa.String(length=40), nullable=True),
    sa.Column('image_uploaded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('image_ready_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('image_pending_key', sa.String(length=255), nullable=True),
    sa.Column('is_complete', sa.Boolean(), sa.Computed("title IS NOT NULL AND btrim(title) <> '' AND artist IS NOT NULL AND btrim(artist) <> '' AND year_text IS NOT NULL AND btrim(year_text) <> '' AND description IS NOT NULL AND btrim(description) <> '' AND image_status = 'ready'", persisted=True), nullable=False),
    sa.CheckConstraint("image_status <> 'ready' OR (image_origin_key IS NOT NULL AND image_display_key IS NOT NULL AND image_thumb_key IS NOT NULL)", name=op.f('ck_artwork_ready_requires_keys')),
    sa.CheckConstraint("image_status IN ('empty', 'uploading', 'ready', 'failed')", name=op.f('ck_artwork_image_status')),
    sa.CheckConstraint("source_url IS NULL OR source_url LIKE 'https://%%'", name=op.f('ck_artwork_source_url_https')),
    sa.CheckConstraint('position BETWEEN 1 AND 12', name=op.f('ck_artwork_position_range')),
    sa.ForeignKeyConstraint(['exhibition_id'], ['exhibition.id'], name='fk_artwork_exhibition_id', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_artwork')),
    sa.UniqueConstraint('exhibition_id', 'position', deferrable=True, initially='DEFERRED', name='uq_artwork_exhibition_position')
    )
    op.create_index('ix_artwork_exhibition_id_position', 'artwork', ['exhibition_id', 'position'], unique=False)
    op.create_table('notification_log',
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('kind', sa.String(length=30), nullable=False),
    sa.Column('dedupe_key', sa.String(length=160), nullable=False),
    sa.Column('exhibition_id', sa.Uuid(), nullable=True),
    sa.Column('status', sa.String(length=10), server_default=sa.text("'pending'"), nullable=False),
    sa.Column('skip_reason', sa.String(length=40), nullable=True),
    sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('attempt_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('last_error', sa.String(length=300), nullable=True),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.CheckConstraint("kind IN ('morning_exhibition', 'late_publish', 'curator_carryover', 'curator_signup')", name=op.f('ck_notification_log_kind')),
    sa.CheckConstraint("status IN ('pending', 'sent', 'skipped', 'failed')", name=op.f('ck_notification_log_status')),
    sa.CheckConstraint('attempt_count >= 0', name=op.f('ck_notification_log_attempt_count')),
    sa.ForeignKeyConstraint(['exhibition_id'], ['exhibition.id'], name='fk_notification_log_exhibition_id', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name='fk_notification_log_user_id', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notification_log')),
    sa.UniqueConstraint('dedupe_key', name='uq_notification_log_dedupe_key')
    )
    op.create_index('ix_notification_log_created_at', 'notification_log', [sa.literal_column('created_at DESC')], unique=False)
    op.create_index('ix_notification_log_due', 'notification_log', ['scheduled_for'], unique=False, postgresql_where=sa.text("status = 'pending'"))
    op.create_table('view_log',
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('viewed_on', sa.Date(), nullable=False),
    sa.Column('exhibition_id', sa.Uuid(), nullable=True),
    sa.Column('first_entered_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_entered_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('entry_count', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('is_anonymized', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint('entry_count >= 1', name=op.f('ck_view_log_entry_count_positive')),
    sa.ForeignKeyConstraint(['exhibition_id'], ['exhibition.id'], name='fk_view_log_exhibition_id', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name='fk_view_log_user_id', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_view_log')),
    sa.UniqueConstraint('user_id', 'viewed_on', name='uq_view_log_user_id_viewed_on')
    )
    op.create_index('ix_view_log_exhibition_id', 'view_log', ['exhibition_id'], unique=False)
    op.create_index('ix_view_log_viewed_on', 'view_log', [sa.literal_column('viewed_on DESC')], unique=False)
    op.create_table('artwork_view_log',
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('artwork_id', sa.Uuid(), nullable=False),
    sa.Column('exhibition_id', sa.Uuid(), nullable=False),
    sa.Column('first_viewed_on', sa.Date(), nullable=False),
    sa.Column('first_viewed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_viewed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('view_count', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('is_anonymized', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint('view_count >= 1', name=op.f('ck_artwork_view_log_view_count_positive')),
    sa.ForeignKeyConstraint(['artwork_id'], ['artwork.id'], name='fk_artwork_view_log_artwork_id', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['exhibition_id'], ['exhibition.id'], name='fk_artwork_view_log_exhibition_id', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name='fk_artwork_view_log_user_id', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_artwork_view_log')),
    sa.UniqueConstraint('user_id', 'artwork_id', name='uq_artwork_view_log_user_id_artwork_id')
    )
    op.create_index('ix_artwork_view_log_first_viewed_on', 'artwork_view_log', [sa.literal_column('first_viewed_on DESC')], unique=False)
    op.create_index('ix_artwork_view_log_user_id_exhibition_id', 'artwork_view_log', ['user_id', 'exhibition_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_artwork_view_log_user_id_exhibition_id', table_name='artwork_view_log')
    op.drop_index('ix_artwork_view_log_first_viewed_on', table_name='artwork_view_log')
    op.drop_table('artwork_view_log')
    op.drop_index('ix_view_log_viewed_on', table_name='view_log')
    op.drop_index('ix_view_log_exhibition_id', table_name='view_log')
    op.drop_table('view_log')
    op.drop_index('ix_notification_log_due', table_name='notification_log', postgresql_where=sa.text("status = 'pending'"))
    op.drop_index('ix_notification_log_created_at', table_name='notification_log')
    op.drop_table('notification_log')
    op.drop_index('ix_artwork_exhibition_id_position', table_name='artwork')
    op.drop_table('artwork')
    op.drop_index('ix_push_subscription_user_active', table_name='push_subscription', postgresql_where=sa.text('is_active'))
    op.drop_table('push_subscription')
    op.drop_index('ix_notice_period', table_name='notice', postgresql_where=sa.text('is_active'))
    op.drop_table('notice')
    op.drop_index('ix_exhibition_visible', table_name='exhibition', postgresql_where=sa.text('is_published AND NOT is_hidden'))
    op.drop_table('exhibition')
    op.drop_index('ix_audit_log_target', table_name='audit_log')
    op.drop_index('ix_audit_log_created_at', table_name='audit_log')
    op.drop_table('audit_log')
    op.drop_table('app_setting')
    op.drop_index('ix_auth_throttle_locked_until', table_name='auth_throttle')
    op.drop_table('auth_throttle')
    op.drop_index('uq_app_user_single_curator', table_name='app_user', postgresql_where=sa.text("role = 'curator'"))
    op.drop_index('ix_app_user_notify_target', table_name='app_user', postgresql_where=sa.text('notify_enabled AND NOT is_blocked'))
    op.drop_index('ix_app_user_name_trgm', table_name='app_user', postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.drop_index('ix_app_user_created_at', table_name='app_user')
    op.drop_table('app_user')

    # 확장은 마지막에 내린다. 이 스키마 외에 쓰는 곳이 없다.
    op.execute("DROP EXTENSION IF EXISTS btree_gist")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
