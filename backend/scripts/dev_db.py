"""로컬 개발·마이그레이션 검증용 PostgreSQL 기동 스크립트.

`pgserver`가 담고 있는 PostgreSQL 16 바이너리로 임시 인스턴스를 띄우고 접속 URL을
표준출력에 찍는다. 프로세스가 끝나도 서버는 남는다(`cleanup_mode=None`).

    $ .venv/bin/python scripts/dev_db.py start   # URL 출력
    $ .venv/bin/python scripts/dev_db.py stop

이미 PostgreSQL이 있는 환경이라면 이 스크립트가 필요 없다. `.env`의 DATABASE_URL을
그쪽으로 두면 된다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pgserver
from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_ROOT / ".pgdata"
DATABASE = "gallery_k"
EXTENSIONS = ("pg_trgm", "btree_gist")


def _uri(server: pgserver.PostgresServer) -> str:
    return server.get_uri(database=DATABASE).replace("postgresql://", "postgresql+psycopg://")


def start(*, reset: bool = False) -> str:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    server = pgserver.get_server(DATA_DIR, cleanup_mode=None)
    if reset:
        server.psql(f"DROP DATABASE IF EXISTS {DATABASE};")
    server.psql(
        f"SELECT 'CREATE DATABASE {DATABASE}' "
        f"WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '{DATABASE}')\\gexec"
    )
    uri = _uri(server)
    engine = create_engine(uri)
    with engine.begin() as connection:
        for extension in EXTENSIONS:
            connection.execute(text(f"CREATE EXTENSION IF NOT EXISTS {extension}"))
    engine.dispose()
    return uri


def stop() -> None:
    server = pgserver.get_server(DATA_DIR, cleanup_mode=None)
    server.cleanup()


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "start"
    if command == "start":
        print(start())
    elif command == "reset":
        print(start(reset=True))
    elif command == "stop":
        stop()
    else:
        print(f"알 수 없는 명령입니다: {command}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
