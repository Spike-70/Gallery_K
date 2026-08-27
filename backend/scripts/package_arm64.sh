#!/usr/bin/env bash
# ARM64 배포 패키지 빌드 (백엔드 문서 §2 "Lambda(ARM64)", §14 콜드 스타트)
#
# 왜 이 스크립트가 필요한가
# ─────────────────────────
# Chalice 1.33의 패키저는 의존성 휠을 받을 때 플랫폼 태그를 `x86_64`로 **하드코딩**한다
# (`chalice/deploy/packager.py::_get_pip_platforms`). 그래서 `chalice deploy`만으로는
# ARM64 Lambda가 나오지 않는다.
#
# 우회 경로는 셋으로 나뉜다.
#   1. 의존성 전체를 aarch64 휠로 받아 `vendor/`에 푼다.
#      Chalice는 `vendor/` 내용을 그대로 패키지에 담고, 자신의 런타임 파일은 직접
#      주입하므로(packager.py `_add_app_files`) requirements.txt를 비워도 안전하다.
#   2. `chalice package --pkg-format cloudformation`으로 산출물을 만든다.
#   3. 템플릿의 각 함수에 `Architectures: [arm64]`를 박는다.
#
# 순수 파이썬인데 휠이 없는 패키지(예: http-ece)는 먼저 로컬에서 휠로 만들어 둔다.
# 그 결과가 `py3-none-any`가 아니면 **중단한다** — C 확장을 호스트 아키텍처로 빌드한
# 것이므로 ARM64 패키지에 들어가면 안 된다.
#
#   $ bash scripts/package_arm64.sh [스테이지]        # 기본 prod
set -euo pipefail

STAGE="${1:-prod}"
BACKEND_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-$BACKEND_ROOT/.venv/bin/python}"
CHALICE="${CHALICE:-$BACKEND_ROOT/.venv/bin/chalice}"
OUT_DIR="$BACKEND_ROOT/dist/arm64"

# Lambda python3.12(ARM64)는 Amazon Linux 2023, glibc 2.34다.
PYTHON_VERSION=3.12
ABI=cp312
PLATFORM_TAGS=(
  manylinux_2_17_aarch64 manylinux_2_24_aarch64 manylinux_2_26_aarch64
  manylinux_2_27_aarch64 manylinux_2_28_aarch64 manylinux_2_31_aarch64
  manylinux_2_34_aarch64 manylinux2014_aarch64
)

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
WHEELHOUSE="$WORK/wheelhouse"
BUILD="$WORK/build"
mkdir -p "$WHEELHOUSE" "$BUILD/vendor"

say() { echo "[arm64] $*"; }

# `chalice package`는 라우트를 찾기 위해 app.py를 import 한다. 설정 객체가 기동 시점에
# 필수 값을 검증하므로(문서 §8.1) 빌드에도 값이 필요하다. **값의 내용은 무의미하며
# 산출물에 들어가지 않는다** — 배포된 함수는 스테이지 환경변수를 받는다.
# 빌드가 프로덕션 시크릿을 요구하지 않게 하는 것이 이 자리표시자의 목적이다.
export APP_ENV="${APP_ENV:-dev}"
export JWT_SECRET="${JWT_SECRET:-build-time-placeholder-not-shipped}"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://build:build@localhost:5432/build}"
export MEDIA_BUCKET="${MEDIA_BUCKET:-build-time-placeholder}"
# chalice가 템플릿의 ARN을 조립하는 데 리전이 필요하다. 배포 대상 리전과 맞춘다.
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-ap-northeast-2}"

# ── 1. 휠이 없는 순수 파이썬 패키지를 먼저 휠로 만든다 ──────────────────────
say "sdist 전용 의존성 확인"
HOST_CLOSURE="$WORK/host"
mkdir -p "$HOST_CLOSURE"
"$PYTHON" -m pip download -q -d "$HOST_CLOSURE" -r "$BACKEND_ROOT/requirements.txt"

shopt -s nullglob
for sdist in "$HOST_CLOSURE"/*.tar.gz "$HOST_CLOSURE"/*.zip; do
  name="$(basename "$sdist")"
  say "휠 없음 → 로컬 빌드: $name"
  "$PYTHON" -m pip wheel -q --no-deps -w "$WHEELHOUSE" "$sdist"
done
shopt -u nullglob

for built in "$WHEELHOUSE"/*.whl; do
  [[ -e "$built" ]] || continue
  case "$(basename "$built")" in
    *-none-any.whl) ;;
    *) echo "[arm64] 중단: 호스트 아키텍처로 빌드된 휠입니다 — $(basename "$built")" >&2; exit 1 ;;
  esac
done

# ── 2. aarch64 휠 전량 수집 ────────────────────────────────────────────────
say "aarch64 휠 수집"
platform_args=()
for tag in "${PLATFORM_TAGS[@]}"; do platform_args+=(--platform "$tag"); done

"$PYTHON" -m pip download -q -d "$WHEELHOUSE" \
  "${platform_args[@]}" \
  --python-version "$PYTHON_VERSION" --implementation cp --abi "$ABI" \
  --only-binary=:all: --find-links "$WHEELHOUSE" \
  -r "$BACKEND_ROOT/requirements.txt"

# x86 휠이 섞여 들어오면 즉시 드러나야 한다.
if ls "$WHEELHOUSE" | grep -q "x86_64"; then
  echo "[arm64] 중단: x86_64 휠이 섞였습니다" >&2
  ls "$WHEELHOUSE" | grep "x86_64" >&2
  exit 1
fi
say "휠 $(ls "$WHEELHOUSE"/*.whl | wc -l)개"

# ── 3. vendor/ 로 푼다 ────────────────────────────────────────────────────
say "vendor/ 구성"
for wheel in "$WHEELHOUSE"/*.whl; do
  # chalice 자신은 패키저가 직접 주입한다. 넣으면 중복된다.
  [[ "$(basename "$wheel")" == chalice-* ]] && continue
  "$PYTHON" -m zipfile -e "$wheel" "$BUILD/vendor"
done

# ── 4. 패키지 빌드 ────────────────────────────────────────────────────────
say "chalice package (requirements.txt는 비운다 — 의존성은 전부 vendor/에 있다)"
cp "$BACKEND_ROOT/app.py" "$BUILD/"
cp -r "$BACKEND_ROOT/chalicelib" "$BUILD/"
cp -r "$BACKEND_ROOT/.chalice" "$BUILD/"
rm -rf "$BUILD/.chalice/deployments"
: > "$BUILD/requirements.txt"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"
(cd "$BUILD" && "$CHALICE" package --pkg-format cloudformation --stage "$STAGE" "$OUT_DIR")

# ── 5. 템플릿에 아키텍처를 박는다 ─────────────────────────────────────────
say "템플릿에 Architectures: [arm64] 적용"
"$PYTHON" "$BACKEND_ROOT/scripts/patch_architecture.py" "$OUT_DIR"

say "완료 → $OUT_DIR"
ls -la "$OUT_DIR"
