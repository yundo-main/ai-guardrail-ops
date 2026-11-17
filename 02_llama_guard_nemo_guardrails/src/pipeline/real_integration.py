"""Run the two real step-02 guardrail calls and save JSON (+ optional HTML).

Normally invoked through ``src/main.py real``; kept importable so the entry
point and tests share one implementation.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

SRC = Path(__file__).resolve().parents[1]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "results" / "step02-real-guardrails.json"


def run(
    prompt: str,
    output: Path,
    nemo_config: str | None = None,
    backend: str | None = None,
    html_output: Path | None = None,
) -> dict:
    # Lazy imports keep `main.py compare` runnable without torch/NeMo installed.
    from classifier.llama_guard import get_llama_guard_client
    from dialogue.nemo_guardrails_client import NemoGuardrailsClient

    llama_result = get_llama_guard_client(backend).classify(prompt)
    nemo_result = NemoGuardrailsClient(nemo_config).generate(prompt)
    payload = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prompt": prompt,
        "llama_guard": llama_result.as_dict(),
        "nemo_guardrails": nemo_result,
        "note": "Llama Guard classifies; NeMo Guardrails controls dialogue flow; application policy makes the final decision.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if html_output is not None:
        from pipeline.report import write_report

        write_report(payload, html_output)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Call Llama Guard and NeMo Guardrails.")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--nemo-config", default=None)
    parser.add_argument(
        "--backend",
        default=None,
        choices=["ollama", "transformers"],
        help="Llama Guard backend (default: $LLAMA_GUARD_BACKEND or ollama)",
    )
    parser.add_argument(
        "--html",
        nargs="?",
        const="",
        default=None,
        metavar="PATH",
        help="HTML 보고서 경로 (생략 시 --output과 같은 이름의 .html). 기본: 항상 생성",
    )
    parser.add_argument("--no-html", action="store_true", help="HTML 보고서 생성을 끈다")
    args = parser.parse_args(argv)
    output = Path(args.output)
    if args.no_html:
        html_output = None
    elif args.html:
        html_output = Path(args.html)
    else:
        html_output = output.with_suffix(".html")
    payload = run(
        args.prompt,
        output,
        args.nemo_config,
        backend=args.backend,
        html_output=html_output,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
