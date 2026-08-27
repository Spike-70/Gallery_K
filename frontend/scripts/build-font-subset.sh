#!/usr/bin/env bash
#
# 본문 폰트 서브셋 생성 — 디자인 시스템 문서 §4.1
#
#   bash scripts/build-font-subset.sh
#
# Pretendard 가변 폰트(2.0MB)를 **Pretendard가 공식으로 쓰는 서브셋 글리프 목록**
# (라틴 + 한글 2,780자 + 숫자 + 문장부호, `subset_glyphs.txt`)으로 잘라
# `public/fonts/PretendardVariable.subset.woff2` 하나를 만든다.
#
# 왜 자체 호스팅인가 — 폐쇄형 서비스는 외부 CDN에 요청을 남기지 않는다(PRD §8.4, DS S-7).
# 왜 가변 폰트 1개인가 — 이 제품이 쓰는 굵기는 400·500·600 셋이다. 정적 서브셋은
#   굵기마다 약 261KB이므로 셋을 합치면 가변 1개보다 무겁다.
#
# 산출물은 저장소에 커밋한다. 이 스크립트는 그것을 **되살리는 방법**이지
# 빌드 파이프라인의 일부가 아니다(설치 조건이 무겁다).
#
# 필요한 것
#   - node_modules/pretendard  (devDependency. `npm install`로 들어온다)
#   - python3 + fonttools + brotli
#       python3 -m venv .venv-font && .venv-font/bin/pip install fonttools brotli
#
set -euo pipefail

cd "$(dirname "$0")/.."

SOURCE="node_modules/pretendard/dist/web/variable/woff2/PretendardVariable.woff2"
GLYPHS="node_modules/pretendard/subset_glyphs.txt"
LICENSE_SRC="node_modules/pretendard/dist/LICENSE.txt"
OUT_DIR="public/fonts"
OUT="$OUT_DIR/PretendardVariable.subset.woff2"

PYFTSUBSET="${PYFTSUBSET:-pyftsubset}"

for path in "$SOURCE" "$GLYPHS"; do
  [ -f "$path" ] || { echo "없음: $path — 먼저 npm install 을 실행하세요." >&2; exit 1; }
done
command -v "$PYFTSUBSET" >/dev/null || {
  echo "pyftsubset 을 찾을 수 없습니다. PYFTSUBSET=/경로/pyftsubset 로 지정하거나 fonttools 를 설치하세요." >&2
  exit 1
}

mkdir -p "$OUT_DIR"

"$PYFTSUBSET" "$SOURCE" \
  --text-file="$GLYPHS" \
  `# 글리프 목록에 없을 수 있는 기본 문장부호·통화기호를 명시적으로 더한다` \
  --unicodes="U+0020-007E,U+00A0,U+2018-201D,U+2026,U+00B7,U+20A9" \
  `# 한글 조판에 필요한 것만 남긴다. 미사용 OpenType 기능은 용량이다` \
  --layout-features="kern,liga,calt,ccmp,locl,mark,mkmk" \
  --flavor=woff2 \
  --no-hinting \
  --desubroutinize \
  --output-file="$OUT"

cp "$LICENSE_SRC" "$OUT_DIR/LICENSE.txt"

printf '생성 완료  %s  (%s KB)\n' "$OUT" "$(( $(stat -c%s "$OUT") / 1024 ))"
printf '라이선스   %s/LICENSE.txt (SIL Open Font License 1.1)\n' "$OUT_DIR"
