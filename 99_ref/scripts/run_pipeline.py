"""Run the file-based day 3 → day 4 → day 6 learning pipeline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def run(*args: str, env: dict[str, str] | None = None) -> None:
    """Run one documented command from the project root."""
    command_env = None
    if env:
        import os

        command_env = os.environ.copy()
        command_env.update(env)
    # check=True로 중간 단계 실패를 숨기지 않고 즉시 파이프라인을 중단한다.
    subprocess.run([sys.executable, *args], cwd=ROOT, env=command_env, check=True)


def main() -> None:
    """Generate the short file-based handoff used by the learning README."""
    # 중간 결과 파일을 사람이 직접 복사하지 않아도 점층적 흐름을 재현한다.
    run("03_policy_blocking_output_filtering/src/guardrail.py")
    run("04_risk_rating_system/src/risk.py", env={"PYTHONPATH": str(ROOT / "04_risk_rating_system" / "src")})
    run("06_operations_report_integrated_lab/src/app.py")
    print("Pipeline complete: results/step03 → step04 → step06")


if __name__ == "__main__":
    main()
