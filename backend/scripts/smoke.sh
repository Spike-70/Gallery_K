#!/usr/bin/env bash
# 배포 후 스모크 (백엔드 문서 §14)
#
#   헬스 → 첫 화면 → 로그인 왕복
#
# 셋 중 하나라도 실패하면 0이 아닌 코드로 끝난다. 파이프라인은 이 결과를 보고
# 직전 버전으로 롤백한다.
#
#   BASE_URL=https://example.com/api SMOKE_PHONE=010... SMOKE_PASSWORD=... bash scripts/smoke.sh
#
# 로컬(`chalice local`)에는 API Gateway 스테이지 접두가 붙지 않는다. 그때의 기준 URL은
# `http://localhost:8000`이고, 배포 환경에서만 `/api`가 붙는다.
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
COOKIE_JAR="$(mktemp)"
trap 'rm -f "$COOKIE_JAR"' EXIT

fail() { echo "[smoke] 실패: $1" >&2; exit 1; }
ok() { echo "[smoke] ok: $1"; }

# 1. 헬스 — degraded여도 200이어야 한다(PRD §8.5).
health="$(curl -sS -o /dev/null -w '%{http_code}' "$BASE_URL/system/health")"
[[ "$health" == "200" ]] || fail "헬스 체크 상태 $health"
ok "헬스"

# 2. 첫 화면 — 장애 중에도 떠야 한다.
landing="$(curl -sS "$BASE_URL/public/landing")"
echo "$landing" | grep -q '"success":true' || fail "첫 화면 봉투가 성공이 아닙니다"
echo "$landing" | grep -q '"today"' || fail "첫 화면에 today가 없습니다"
ok "첫 화면"

# 3. 로그인 왕복 — 자격이 주어졌을 때만 수행한다.
if [[ -n "${SMOKE_PHONE:-}" && -n "${SMOKE_PASSWORD:-}" ]]; then
  login_status="$(curl -sS -o /dev/null -w '%{http_code}' -c "$COOKIE_JAR" \
    -H 'Content-Type: application/json' -H 'X-Requested-With: gallery-k' \
    -d "{\"phone\":\"$SMOKE_PHONE\",\"password\":\"$SMOKE_PASSWORD\"}" \
    "$BASE_URL/auth/login")"
  [[ "$login_status" == "200" ]] || fail "로그인 상태 $login_status"

  session="$(curl -sS -b "$COOKIE_JAR" "$BASE_URL/auth/session")"
  echo "$session" | grep -q '"is_authenticated":true' || fail "세션이 인증되지 않았습니다"
  ok "로그인 왕복"
else
  echo "[smoke] 건너뜀: SMOKE_PHONE/SMOKE_PASSWORD 미설정"
fi

echo "[smoke] 전부 통과"
