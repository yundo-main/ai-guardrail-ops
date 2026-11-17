"""Render a real-integration JSON payload as a standalone HTML report.

The report is generated from the same dict that ``run()`` writes to JSON, so
both artifacts always describe the same run.
"""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Any


def _pre(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    return f'<pre class="json">{escape(text)}</pre>'


def _summary(llama: dict, nemo: dict) -> list[str]:
    """Compose summary sentences for the report (one per line)."""
    safe = llama.get("safe")
    category = llama.get("category")
    if safe is True:
        cls = "Llama Guard가 해당 입력을 safe로 분류했습니다."
    elif safe is False:
        cls = f"Llama Guard가 해당 입력을 unsafe로 분류했습니다 (범주: {category or 'unknown'})."
    else:
        cls = "Llama Guard 분류 결과를 확인할 수 없습니다."
    nemo_txt = "NeMo Guardrails가 대화 레일을 통과한 응답을 반환했습니다." if nemo else "NeMo Guardrails 응답이 비어 있습니다."
    return [cls, nemo_txt, "최종 허용·차단·검토 결정은 3단계 정책 엔진의 책임입니다."]


def render_html(payload: dict[str, Any]) -> str:
    """Return a self-contained HTML document for one integration result."""
    llama = payload.get("llama_guard") or {}
    nemo = payload.get("nemo_guardrails") or {}
    safe = llama.get("safe")
    verdict = "SAFE" if safe is True else ("UNSAFE" if safe is False else "UNKNOWN")
    vc = "ok" if safe is True else ("bad" if safe is False else "warn")
    verdict_ko = {"ok": "안전", "bad": "위험", "warn": "확인 불가"}[vc]
    verdict_label = f"{verdict} · {verdict_ko}"

    category = llama.get("category")
    provider = llama.get("provider") or ""
    model = llama.get("model") or ""
    backend = "Ollama" if provider.startswith("ollama") else ("Transformers" if "transformers" in provider else provider or "—")

    info_rows = [
        ("실행 일시", payload.get("generated_at", "—")),
        ("스키마 버전", payload.get("schema_version", "—")),
        ("분류 모델", f"{model} ({backend})" if model != "—" else "—"),
        ("위험 범주", category or "—"),
    ]
    info = "".join(
        f'<tr><th>{escape(str(k))}</th><td>{escape(str(v))}</td></tr>'
        for k, v in info_rows
    )
    raw = llama.get("raw") or ""
    raw_lines = [l for l in str(raw).splitlines() if l.strip()]
    raw_status = raw_lines[0].strip() if raw_lines else ""
    raw_status_class = "ok" if raw_status.lower() == "safe" else ("bad" if raw_status.lower() == "unsafe" else "warn")
    prompt = str(payload.get("prompt", ""))
    prompt_short = prompt if len(prompt) <= 80 else prompt[:77] + "…"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>2단계 Guardrail 실행 보고서</title>
<style>
  :root {{
    --bg: #f4f6f9; --card: #ffffff; --ink: #17202e; --muted: #66707f;
    --line: #e3e8ef; --accent: #2f6fed; --ok: #1a7f4b; --ok-bg: #e7f6ee;
    --bad: #c93a3a; --bad-bg: #fdecec; --warn: #9a6b12; --warn-bg: #fdf3e0;
    --code-bg: #eef1f6; --code-ink: #1d2735;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #0d1420; --card: #141d2e; --ink: #e8edf5; --muted: #9aa7b8;
      --line: #26334a; --accent: #6ea0ff; --ok: #5fd39a; --ok-bg: #14301f;
      --bad: #ff7b72; --bad-bg: #3a1c1c; --warn: #f0b95a; --warn-bg: #33270f;
      --code-bg: #0b1220; --code-ink: #d7e0ee;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, "Segoe UI", "Noto Sans KR", sans-serif;
    background: var(--bg); color: var(--ink); margin: 0;
    line-height: 1.6; padding: 2.2rem 1rem 3rem;
  }}
  .wrap {{ max-width: 860px; margin: 0 auto; }}
  .doc {{ background: var(--card); border: 1px solid var(--line); border-radius: 16px;
          padding: 2rem 2.2rem; box-shadow: 0 1px 3px rgba(15,23,42,.06); }}
  .doc-head {{ border-bottom: 2px solid var(--ink); padding-bottom: 1rem; margin-bottom: 1.2rem; }}
  .eyebrow {{ font-size: .75rem; font-weight: 800; letter-spacing: .12em;
              color: var(--accent); text-transform: uppercase; }}
  h1 {{ font-size: 1.45rem; margin: .25rem 0 .3rem; }}
  .doc-sub {{ color: var(--muted); font-size: .85rem; }}
  h2 {{ font-size: 1.02rem; margin: 1.6rem 0 .6rem; display: flex; align-items: baseline; gap: .55rem; }}
  h2 .no {{ color: var(--accent); font-size: .8rem; font-weight: 800; letter-spacing: .05em; }}
  h2 .tag {{ font-size: .68rem; font-weight: 700; padding: .12rem .5rem;
             border-radius: 6px; background: var(--bg); color: var(--muted);
             border: 1px solid var(--line); }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ text-align: left; padding: .4rem .9rem .4rem 0; vertical-align: top;
           border-bottom: 1px solid var(--line); }}
  th {{ color: var(--muted); font-weight: 600; width: 7.5rem; white-space: nowrap; }}
  tr:last-child th, tr:last-child td {{ border-bottom: none; }}
  .verdict-row {{ display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;
                 padding: .9rem 1.1rem; border-radius: 12px; margin: .4rem 0 0;
                 border: 1px solid var(--line); }}
  .verdict {{
    display: inline-flex; align-items: center; gap: .45rem;
    padding: .3rem .95rem; border-radius: 999px; font-weight: 800;
    font-size: .95rem; letter-spacing: .04em;
  }}
  .verdict .dot {{ width: .6rem; height: .6rem; border-radius: 50%; background: currentColor; }}
  .ok {{ background: var(--ok-bg); color: var(--ok); }}
  .bad {{ background: var(--bad-bg); color: var(--bad); }}
  .warn {{ background: var(--warn-bg); color: var(--warn); }}
  .summary {{ color: var(--muted); font-size: .92rem; line-height: 1.7; }}
  pre.json {{
    background: var(--code-bg); color: var(--code-ink); border: 1px solid var(--line);
    border-radius: 10px;
    padding: .9rem 1rem; overflow-x: auto; white-space: pre-wrap;
    word-break: break-word; font-size: .84rem; margin: .5rem 0 0;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
  }}
  .raw-status {{ font-family: ui-monospace, Menlo, monospace; font-weight: 700; }}
  .conclusion {{
    background: var(--bg); border: 1px solid var(--line); border-radius: 12px;
    padding: .9rem 1.1rem; font-size: .92rem;
  }}
  .note {{ color: var(--muted); font-size: .85rem; margin-top: 1.6rem;
          padding-top: 1rem; border-top: 1px solid var(--line); }}
  footer {{ color: var(--muted); font-size: .78rem; text-align: center; margin-top: 1.4rem; }}
</style>
</head>
<body>
<div class="wrap">
<div class="doc">
  <div class="doc-head">
    <div class="eyebrow">Step 02 · 실행 보고서</div>
    <h1>가드레일 실추론 결과 보고서</h1>
    <div class="doc-sub">Llama Guard 안전성 분류 + NeMo Guardrails 대화 레일 — {escape(prompt_short)}</div>
  </div>

  <h2><span class="no">1.</span>보고서 정보</h2>
  <table>{info}</table>

  <h2><span class="no">2.</span>판정 요약</h2>
  <div class="verdict-row">
    <span class="verdict {vc}"><span class="dot"></span>{verdict_label}</span>
    <span class="summary">{"<br>".join(escape(s) for s in _summary(llama, nemo))}</span>
  </div>

  <h2><span class="no">3.</span>입력 프롬프트</h2>
  {_pre(prompt)}

  <h2><span class="no">4.</span>Llama Guard 분류 결과 <span class="tag">분류기 — 최종 결정 아님</span></h2>
  <table>
    <tr><th>모델</th><td>{escape(model)}</td></tr>
    <tr><th>백엔드</th><td>{escape(backend)}</td></tr>
    <tr><th>Provider</th><td>{escape(provider or "—")}</td></tr>
  </table>
  <h2 style="font-size:.92rem;margin-top:1rem">Raw 출력 <span class="raw-status {raw_status_class}">→ {escape(raw_status)}</span></h2>
  {_pre(raw)}

  <h2><span class="no">5.</span>NeMo Guardrails 응답 <span class="tag">대화 흐름 제어</span></h2>
  {_pre(nemo)}

  <h2><span class="no">6.</span>결론 및 다음 단계</h2>
  <div class="conclusion">
    {escape(str(payload.get("note", "")))}<br>
    이 결과는 <b>2단계 분류·대화 레일의 관측 산출물</b>입니다.<br>
    허용·차단·검토의 최종 결정과 운영 이벤트 기록은 3단계 정책 엔진 이후 단계에서 수행합니다.
  </div>

  <p class="note">원본 데이터: 같은 이름의 <code>.json</code> 파일 · schema_version {escape(str(payload.get("schema_version", "")))}</p>
</div>
<footer>2단계 · Llama Guard·NeMo Guardrails 실습 — ai-guardrails-ops</footer>
</div>
</body>
</html>
"""


def write_report(payload: dict[str, Any], path: str | Path) -> Path:
    """Write the HTML report for ``payload`` and return the written path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_html(payload), encoding="utf-8")
    return target
