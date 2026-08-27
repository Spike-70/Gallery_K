"""CloudFormation 템플릿의 Lambda 함수에 ARM64를 박는다 (백엔드 문서 §2).

Chalice 1.33에는 아키텍처 지정 설정이 없다. 산출물을 고치는 것이 유일한 경로이므로,
그 수정을 손이 아니라 스크립트로 두어 배포마다 같은 결과가 나오게 한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ARCHITECTURE = "arm64"


def patch(out_dir: Path) -> int:
    template_path = out_dir / "sam.json"
    if not template_path.is_file():
        print(f"[arm64] 템플릿을 찾지 못했습니다: {template_path}", file=sys.stderr)
        return 1

    template = json.loads(template_path.read_text())
    functions = [
        (name, resource)
        for name, resource in template.get("Resources", {}).items()
        if resource.get("Type") == "AWS::Serverless::Function"
    ]
    if not functions:
        print("[arm64] 템플릿에 Lambda 함수가 없습니다", file=sys.stderr)
        return 1

    for name, resource in functions:
        resource.setdefault("Properties", {})["Architectures"] = [ARCHITECTURE]
        print(f"[arm64] {name} → {ARCHITECTURE}")

    template_path.write_text(json.dumps(template, indent=2) + "\n")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("사용법: patch_architecture.py <산출물 디렉터리>", file=sys.stderr)
        return 2
    return patch(Path(sys.argv[1]))


if __name__ == "__main__":
    raise SystemExit(main())
