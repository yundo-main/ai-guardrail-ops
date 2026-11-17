"""Run the progressive integration track without changing daily lab folders."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "99_ref" / "integration" / "results"
RESULTS.mkdir(parents=True, exist_ok=True)


def execute(*parts: str, extra_env: dict[str, str] | None = None) -> None:
    """Run a stage as a child process so its environment stays isolated."""
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    subprocess.run([sys.executable, *parts], cwd=ROOT, env=env, check=True)


def stage(number: str) -> None:
    """Execute one additive stage and keep its result in the integration track."""
    # 매핑을 명시적으로 유지하면 단계 번호와 실제 학습 폴더가 어긋나는 것을 막는다.
    commands = {
        "01": ("01_guardrail_concept_architecture/src/architecture.py", {}),
        "02": ("02_llama_guard_nemo_guardrails/src/contracts/adapters.py", {}),
        "03": ("03_policy_blocking_output_filtering/src/guardrail.py", {}),
        "04": ("04_risk_rating_system/src/risk.py", {"PYTHONPATH": str(ROOT / "04_risk_rating_system" / "src")}),
        "06": ("06_operations_report_integrated_lab/src/app.py", {}),
    }
    if number == "05":
        # 현재는 API 서버를 별도 실행하지 않고 계약 결과로 지표를 재현한다.
        # 실제형 통합 단계에서는 이 부분을 POST /events → GET /metrics로 교체한다.
        source = ROOT / "04_risk_rating_system" / "results" / "step04-security-event.json"
        target = RESULTS / "step04-security-event.json"
        if not source.exists():
            stage("03")
            stage("04")
        shutil.copy2(source, target)
        payload = json.loads(target.read_text(encoding="utf-8"))
        metrics = {
            "schema_version": "1.0",
            "source_stage": "integration-05",
            "total_events": 1,
            "blocked_events": int(payload.get("decision") == "block"),
            "review_events": int(payload.get("decision") == "review"),
            "block_rate": 1.0 if payload.get("decision") == "block" else 0.0,
            "review_rate": 1.0 if payload.get("decision") == "review" else 0.0,
            "open_events": int(payload.get("status", "open") == "open"),
            "acknowledged_events": int(payload.get("status") == "acknowledged"),
            "by_category": {payload.get("category", "guardrail"): 1},
            "by_risk": {payload.get("risk", "Low"): 1},
        }
        (RESULTS / "step05-metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
        return
    command, env = commands[number]
    execute(command, extra_env=env)
    if number == "03":
        shutil.copy2(ROOT / "03_policy_blocking_output_filtering" / "results" / "step03-guardrail-result.json", RESULTS / "step03-guardrail-result.json")
    elif number == "04":
        shutil.copy2(ROOT / "04_risk_rating_system" / "results" / "step04-security-event.json", RESULTS / "step04-security-event.json")
    elif number == "06":
        report = json.loads((ROOT / "06_operations_report_integrated_lab" / "results" / "step06-report.json").read_text(encoding="utf-8"))
        metrics_path = RESULTS / "step05-metrics.json"
        if metrics_path.exists():
            report["upstream_metrics"] = json.loads(metrics_path.read_text(encoding="utf-8"))
        report["integration_stage"] = "06"
        (RESULTS / "step06-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    """Expose one-stage and full progressive execution from the CLI."""
    parser = argparse.ArgumentParser(description="Run the progressive integration track")
    parser.add_argument("--stage", choices=["01", "02", "03", "04", "05", "06"])
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if args.all:
        for number in ["01", "02", "03", "04", "05", "06"]:
            stage(number)
        return
    if not args.stage:
        parser.error("--stage or --all is required")
    stage(args.stage)


if __name__ == "__main__":
    main()
