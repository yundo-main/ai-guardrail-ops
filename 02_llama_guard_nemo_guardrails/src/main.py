"""Day 2 entry point.

  python3 02_llama_guard_nemo_guardrails/src/main.py             # compare (default)
  python3.12 02_llama_guard_nemo_guardrails/src/main.py real --prompt "..."

Layout (each subpackage owns one responsibility):
  contracts/  SDK-independent responsibility / handoff contract
  classifier/ Llama Guard 3 (safety classification, Transformers)
  dialogue/   NeMo Guardrails (dialogue flow control, Ollama)
  pipeline/   orchestration that calls both and stores the JSON result
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contracts.adapters import compare_adapters  # noqa: E402


def cmd_compare(_: argparse.Namespace) -> int:
    for item in compare_adapters():
        print(
            f"{item['name']}: {item['purpose']} / "
            f"입력={item['receives']} / 출력={item['produces']} / "
            f"다음={item['handoff_to']}"
        )
    return 0


def cmd_real(args: argparse.Namespace) -> int:
    from pipeline.real_integration import main as real_main

    argv = ["--prompt", args.prompt]
    if args.output:
        argv += ["--output", args.output]
    if args.nemo_config:
        argv += ["--nemo-config", args.nemo_config]
    return real_main(argv)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Day 2: Llama Guard · NeMo Guardrails")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("compare", help="역할·handoff 비교 (기본, 외부 의존성 없음)").set_defaults(func=cmd_compare)
    real = sub.add_parser("real", help="Llama Guard + NeMo 실제 호출")
    real.add_argument("--prompt", required=True)
    real.add_argument("--output", default=None)
    real.add_argument("--nemo-config", default=None)
    real.set_defaults(func=cmd_real)
    args = parser.parse_args(argv)
    return (args.func or cmd_compare)(args) if args.command else cmd_compare(args)


if __name__ == "__main__":
    raise SystemExit(main())
