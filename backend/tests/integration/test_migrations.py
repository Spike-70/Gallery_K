"""마이그레이션 (DB 문서 §9).

가장 중요한 검사는 **적용 결과와 모델 metadata의 대조**다. autogenerate 결과를 손으로
고치는 순간부터 둘은 갈라질 수 있고, 갈라진 것을 배포 후에 발견하면 늦다.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, text

pytestmark = pytest.mark.integration

BACKEND_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def alembic_config(migration_database_url: str, migration_engine: Engine) -> Iterator[Config]:
    """마이그레이션은 빈 DB에서 시작한다. 전용 DB를 쓰므로 다른 테스트와 섞이지 않는다."""
    from chalicelib.db.models import metadata

    metadata.drop_all(migration_engine)
    with migration_engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    previous = os.environ.get("ALEMBIC_DATABASE_URL")
    os.environ["ALEMBIC_DATABASE_URL"] = migration_database_url
    try:
        yield config
    finally:
        # 되돌린 뒤에 환경변수를 복원한다 — 순서가 바뀌면 env.py가 엉뚱한 DB를 본다.
        command.downgrade(config, "base")
        if previous is None:
            os.environ.pop("ALEMBIC_DATABASE_URL", None)
        else:
            os.environ["ALEMBIC_DATABASE_URL"] = previous


def test_history_is_a_single_line() -> None:
    """단일 선형. 브랜치를 쓰지 않는다."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    assert len(heads) == 1, f"머리가 여럿입니다: {heads}"
    for revision in script.walk_revisions():
        assert revision.module.__doc__, f"{revision.revision}: 문서화 문자열이 없습니다"


def test_upgrade_head_matches_the_models(alembic_config: Config, migration_engine: Engine) -> None:
    """적용 결과에서 모델과의 차이가 나오면 실패한다."""
    command.upgrade(alembic_config, "head")

    from chalicelib.db.models import metadata

    with migration_engine.connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={"compare_type": True, "compare_server_default": True},
        )
        diff = compare_metadata(context, metadata)

    # alembic_version 테이블은 모델에 없다. 그것만 예외로 둔다.
    meaningful = [entry for entry in diff if "alembic_version" not in str(entry)]
    assert meaningful == [], f"마이그레이션과 모델이 어긋납니다: {meaningful}"


def test_required_extensions_are_created(alembic_config: Config, migration_engine: Engine) -> None:
    """autogenerate가 감지하지 못하는 부분. 없으면 EXCLUDE와 이름 검색이 성립하지 않는다."""
    command.upgrade(alembic_config, "head")
    with migration_engine.connect() as connection:
        installed = set(connection.execute(text("SELECT extname FROM pg_extension")).scalars())
    assert {"pg_trgm", "btree_gist"} <= installed


def test_seed_is_idempotent(alembic_config: Config, migration_engine: Engine) -> None:
    """몇 번을 다시 돌려도 같다 — 배포 재시도가 계정을 늘리지 않는다."""
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "0001")
    command.upgrade(alembic_config, "head")

    with migration_engine.connect() as connection:
        curators = connection.execute(
            text("SELECT count(*) FROM app_user WHERE role = 'curator'")
        ).scalar_one()
        settings_count = connection.execute(text("SELECT count(*) FROM app_setting")).scalar_one()
    assert curators == 1
    assert settings_count == 10


def test_seeded_curator_must_change_password(alembic_config: Config, migration_engine: Engine) -> None:
    command.upgrade(alembic_config, "head")
    with migration_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT must_change_password, created_via, token_version FROM app_user WHERE role = 'curator'"
            )
        ).one()
    assert row.must_change_password is True
    assert row.created_via == "curator"
    assert row.token_version == 0


def test_seeded_settings_cover_the_documented_keys(alembic_config: Config, migration_engine: Engine) -> None:
    """DB 문서 §4.9의 시드 키 10종."""
    command.upgrade(alembic_config, "head")
    expected = {
        "signup_open",
        "notify_default_time",
        "notify_cutoff_hour",
        "carryover_alert_days",
        "archive_size",
        "admin_calendar_days",
        "log_retention_days",
        "media_url_ttl_seconds",
        "maintenance_mode",
        "session_ttl_days",
    }
    with migration_engine.connect() as connection:
        keys = set(connection.execute(text("SELECT key FROM app_setting")).scalars())
    assert keys == expected


def test_downgrade_removes_everything(alembic_config: Config, migration_engine: Engine) -> None:
    """`downgrade()`는 반드시 구현한다 — 되돌릴 수 없는 배포를 만들지 않는다."""
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")
    with migration_engine.connect() as connection:
        tables = set(
            connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars()
        )
    assert tables <= {"alembic_version"}
