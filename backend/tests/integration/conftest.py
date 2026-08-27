"""통합 테스트용 실제 PostgreSQL (백엔드 문서 §12).

  * `TEST_DATABASE_URL`이 있으면 그 DB를 쓴다.
  * 없으면 dev 의존성 `pgserver`가 담고 있는 PostgreSQL 16 바이너리로 임시 인스턴스를
    띄운다. contrib 확장은 `scripts/setup_test_postgres.sh`가 미리 얹어 둔다.

스키마 검증을 SQLite로 대신하지 않는다 — 부분 인덱스·EXCLUDE·생성 컬럼·DEFERRABLE은
PostgreSQL에만 있고, 그것들이 이 제품의 무결성 분담에서 DB가 맡은 몫 전부다(DB 문서 §8).
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_EXTENSIONS = ("pg_trgm", "btree_gist")


def _ensure_contrib_extensions() -> None:
    subprocess.run(
        ["bash", str(BACKEND_ROOT / "scripts" / "setup_test_postgres.sh")],
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="session")
def database_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    external = os.environ.get("TEST_DATABASE_URL")
    if external:
        yield external
        return

    pgserver = pytest.importorskip("pgserver", reason="pgserver가 없으면 통합 테스트를 건너뛴다")
    _ensure_contrib_extensions()

    data_dir = tmp_path_factory.mktemp("pgdata")
    server = pgserver.get_server(data_dir)
    try:
        server.psql("CREATE DATABASE gallery_k_test;")
        uri = server.get_uri(database="gallery_k_test")
        yield uri.replace("postgresql://", "postgresql+psycopg://")
    finally:
        server.cleanup()


@pytest.fixture(scope="session")
def engine(database_url: str) -> Iterator[Engine]:
    from chalicelib.db.engine import create_db_engine

    created = create_db_engine(database_url)
    with created.begin() as connection:
        for extension in REQUIRED_EXTENSIONS:
            connection.execute(text(f"CREATE EXTENSION IF NOT EXISTS {extension}"))
    yield created
    created.dispose()


@pytest.fixture(scope="session")
def schema(engine: Engine) -> Iterator[None]:
    from chalicelib.db.models import metadata

    metadata.drop_all(engine)
    metadata.create_all(engine)
    yield
    metadata.drop_all(engine)


@pytest.fixture(scope="session")
def migration_database_url(database_url: str) -> str:
    """마이그레이션 테스트 전용 DB.

    `upgrade`/`downgrade`가 스키마를 통째로 만들고 지우므로, 다른 테스트가 쓰는 DB와
    같은 곳에서 돌리면 실행 순서에 따라 서로를 깨뜨린다.
    """
    from sqlalchemy import create_engine, make_url

    url = make_url(database_url)
    target = f"{url.database}_migrations"
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        exists_already = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": target}
        ).scalar()
        if not exists_already:
            connection.execute(text(f'CREATE DATABASE "{target}"'))
    admin.dispose()

    migration_url = str(url.set(database=target))
    created = create_engine(migration_url)
    with created.begin() as connection:
        for extension in REQUIRED_EXTENSIONS:
            connection.execute(text(f"CREATE EXTENSION IF NOT EXISTS {extension}"))
    created.dispose()
    return migration_url


@pytest.fixture(scope="session")
def migration_engine(migration_database_url: str) -> Iterator[Engine]:
    from chalicelib.db.engine import create_db_engine

    created = create_db_engine(migration_database_url)
    yield created
    created.dispose()


@pytest.fixture()
def session(engine: Engine, schema: None) -> Iterator[Session]:
    """테스트마다 트랜잭션을 열고 끝나면 되돌린다. 테스트 사이에 데이터가 새지 않는다."""
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False, autoflush=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture()
def db_session_factory(engine: Engine, schema: None) -> Iterator[Any]:
    """실제 커밋이 일어나는 세션 팩토리.

    라우트 테스트는 미들웨어가 커밋하는 것까지 확인해야 하므로 바깥 트랜잭션으로
    감싸지 않는다. 대신 테스트가 끝날 때 전 테이블을 비운다.
    """
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    yield factory

    from chalicelib.db.models import metadata

    names = ", ".join(f'"{table}"' for table in metadata.tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture()
def api_client(db_session_factory: Any, monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """실제 DB에 붙은 Chalice 테스트 클라이언트."""
    from chalice.test import Client

    from chalicelib.db import engine as engine_module
    from chalicelib.services import setting_service

    monkeypatch.setattr(engine_module, "open_session", db_session_factory)
    setting_service.invalidate_cache()

    import app as app_module

    with Client(app_module.app) as client:
        yield client

    setting_service.invalidate_cache()


@pytest.fixture()
def write_session(db_session_factory: Any) -> Iterator[Session]:
    """테스트가 사전 데이터를 심을 때 쓰는 세션. 커밋까지 한다."""
    db = db_session_factory()
    try:
        yield db
        db.commit()
    finally:
        db.close()
