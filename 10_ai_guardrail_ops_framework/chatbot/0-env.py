# 0-env.py
# =============================================================================
# 0단계 — .env 파일을 환경 변수로 올린다
#
# 0번인 이유: 어떤 단계보다 먼저 실행되어야 하기 때문이다.
# 1단계가 문서를 읽기 전에 설정이 준비되어 있어야 한다.
# 파이프라인의 지식 처리 단계는 1번부터 시작한다.
#
# 왜 필요한가:
#   각 단계는 os.getenv() 로 설정을 읽는다. 그런데 .env 파일을 만들어 두어도
#   셸에 올리지 않으면 파이썬 프로세스는 그 값을 볼 수 없다.
#   매번 `set -a && source .env && set +a` 를 기억해야 하는 구조였고,
#   실제로 이 때문에 설정을 바꿔 두고도 기본값으로 동작하는 상황이 반복됐다.
#   그래서 코드가 직접 읽는다.
#
# 새 의존성은 없다. python-dotenv 를 쓰지 않고 표준 라이브러리만 쓴다.
# =============================================================================

from __future__ import annotations

import os
from pathlib import Path
from typing import List

ENV_PATH = Path(__file__).with_name(".env")


def load_env(path: Path | None = None) -> List[str]:
    """.env 를 읽어 환경 변수로 올리고, 새로 설정한 키 목록을 돌려준다.

    **이미 설정된 값은 덮지 않는다.** 셸에서 지정한 값이 항상 우선한다.
    그래서 일회성 지정이 그대로 통한다.

        RAG_MIN_SCORE=0.5 python 5-agent.py

    .env 가 없으면 아무것도 하지 않는다. 파일 없이도 동작해야 하기 때문이다.
    (환경 변수를 셸에서 직접 export 하는 방식도 그대로 유효하다.)
    """
    target = path or ENV_PATH
    if not target.exists():
        return []

    applied: List[str] = []
    for raw in target.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        # 빈 줄, 주석, KEY=VALUE 형태가 아닌 줄은 건너뛴다.
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        # 값 양쪽의 따옴표는 벗긴다. .env 에서는 흔한 표기다.
        value = value.strip().strip("\"'")
        if not key or key in os.environ:
            continue
        os.environ[key] = value
        applied.append(key)
    return applied


def main() -> None:
    """단독 실행: .env 를 읽어 어떤 키가 올라가는지 보여준다. 값은 출력하지 않는다."""
    print("=" * 60)
    print("0-env.py — .env 로딩 확인")
    print("=" * 60)
    print(f"[1] 파일 위치: {ENV_PATH}")
    print(f"    존재 여부: {'있음' if ENV_PATH.exists() else '없음'}")

    before = {k for k in os.environ}
    applied = load_env()

    print(f"[2] 새로 올린 키 {len(applied)}건")
    for key in applied:
        print(f"    - {key}")
    already = [
        k for k in ("GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_EMBED_MODEL", "RAG_MIN_SCORE")
        if k in before
    ]
    if already:
        print(f"[3] 셸에 이미 있어 건너뛴 키 {len(already)}건 (셸 값이 우선)")
        for key in already:
            print(f"    - {key}")


if __name__ == "__main__":
    main()
