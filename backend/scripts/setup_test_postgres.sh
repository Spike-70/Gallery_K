#!/usr/bin/env bash
# 통합 테스트용 PostgreSQL 준비 스크립트 (DB 문서 §9, 백엔드 문서 §12)
#
# `pgserver` 휠은 PostgreSQL 16 바이너리를 담고 있으나 contrib 확장을 담지 않는다.
# 초기 마이그레이션이 `pg_trgm`·`btree_gist`를 요구하므로 동일 마이너 버전의
# 소스에서 두 확장만 PGXS로 빌드해 pgserver 설치 경로에 얹는다.
#
# 이미 PostgreSQL이 있는 환경이라면 이 스크립트 대신 TEST_DATABASE_URL을 설정한다.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-$HERE/.venv/bin/python}"
PG_CONFIG="$("$PYTHON" -c 'import os, pgserver; print(os.path.join(os.path.dirname(pgserver.__file__), "pginstall", "bin", "pg_config"))')"
PG_VERSION="$("$PG_CONFIG" --version | awk '{print $2}')"
EXT_DIR="$("$PG_CONFIG" --sharedir)/extension"

if [[ -f "$EXT_DIR/pg_trgm.control" && -f "$EXT_DIR/btree_gist.control" ]]; then
  echo "[setup] pg_trgm·btree_gist 이미 설치됨 ($EXT_DIR)"
  exit 0
fi

WORK="${TMPDIR:-/tmp}/gallery-k-pgext"
mkdir -p "$WORK"
cd "$WORK"

TARBALL="postgresql-${PG_VERSION}.tar.bz2"
if [[ ! -d "postgresql-${PG_VERSION}" ]]; then
  echo "[setup] PostgreSQL ${PG_VERSION} 소스 내려받는 중"
  curl -sSL -o "$TARBALL" "https://ftp.postgresql.org/pub/source/v${PG_VERSION}/${TARBALL}"
  tar xf "$TARBALL"
fi

for module in pg_trgm btree_gist; do
  echo "[setup] $module 빌드"
  make -s -C "postgresql-${PG_VERSION}/contrib/$module" USE_PGXS=1 PG_CONFIG="$PG_CONFIG"
  make -s -C "postgresql-${PG_VERSION}/contrib/$module" USE_PGXS=1 PG_CONFIG="$PG_CONFIG" install
done

echo "[setup] 완료 — $EXT_DIR"
