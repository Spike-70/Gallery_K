"""Alembic 실행 환경 (DB 문서 §9).

**Alembic이 유일한 스키마 변경 수단이다.** 애플리케이션 기동 시 자동 실행하지 않는다 —
Lambda 동시 실행이 곧 동시 마이그레이션이 된다. 배포 파이프라인의 독립 단계에서
`alembic upgrade head`로 실행한다.

접속 정보는 `config/settings.py` 하나에서만 온다. `alembic.ini`에 URL을 적지 않는다.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from chalicelib.config.settings import settings
from chalicelib.db.models import metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 테스트는 임시 인스턴스를 가리킨다. 그 외에는 배포 환경의 DATABASE_URL이다.
database_url = os.environ.get("ALEMBIC_DATABASE_URL") or settings.database_url
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

target_metadata = metadata


def include_object(obj: object, name: str | None, type_: str, reflected: bool, compare_to: object) -> bool:
    """확장이 만든 객체를 마이그레이션 대상에서 제외한다."""
    return not (type_ == "table" and name in {"spatial_ref_sys"})


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
