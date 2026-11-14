"""Run the two real Day 2 guardrail calls and save a JSON result.

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
ROOT = SRC.parents[1]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DEFAULT_OUTPUT = ROOT / "99_ref/results/step02-real-guardrails.json"


def run(prompt: str, output: Path, nemo_config: str | None = None) -> dict:
    # Lazy imports keep `main.py compare` runnable without torch/NeMo installed.
    from classifier.llama_guard import LlamaGuardClient
    from dialogue.nemo_guardrails_client import NemoGuardrailsClient

    llama_result = LlamaGuardClient().classify(prompt)
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
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Call Llama Guard 3 and NeMo Guardrails.")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--nemo-config", default=None)
    args = parser.parse_args(argv)
    payload = run(args.prompt, Path(args.output), args.nemo_config)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
