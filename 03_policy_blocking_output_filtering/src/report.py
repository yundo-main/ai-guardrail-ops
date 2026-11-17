"""Render a step-03 guardrail result payload as a standalone HTML report.

The report is generated from the same dict that ``write_result()`` writes to
JSON, so both artifacts always describe the same run.
"""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Any

_DECISION = {
    "allow": ("ok", "허용"),
    "block": ("bad", "차단"),
    "review": ("warn", "검토"),
}
_RISK = {
    "Low": ("ok", "낮음"),
    "Medium": ("warn", "보통"),
    "High": ("bad", "높음"),
    "Critical": ("bad", "긴급"),
}


def _pre(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    return f'<pre class="json">{escape(text)}</pre>'


def _badge(mapping: dict[str, tuple[str, str]], value: Any) -> str:
    cls, ko = mapping.get(str(value), ("warn", str(value)))
    return f'<span class="verdict {cls}"><span class="dot"></span>{escape(str(value).upper() if cls != "warn" or str(value) in mapping else str(value))} · {ko}</span>'


def render_html(payload: dict[str, Any]) -> str:
    """Return a self-contained HTML document for one guardrail result."""
    decision = str(payload.get("decision", ""))
    risk = str(payload.get("risk", ""))
    masked = payload.get("masked_fields") or []
    matches = payload.get("matches") or []

    info_rows = [
        ("스키마 버전", payload.get("schema_version", "—")),
        ("결과 ID", payload.get("event_id", "—")),
        ("추적 ID", payload.get("trace_id", "—")),
        ("단계", f"{payload.get('source_stage', '—')} → {payload.get('next', '—')}"),
    ]
    info = "".join(
        f'<tr><th>{escape(str(k))}</th><td>{escape(str(v))}</td></tr>'
        for k, v in info_rows
    )

    if masked:
        chips = " ".join(f'<span class="chip">{escape(str(f))}</span>' for f in masked)
        masked_html = f'<div class="masked">마스킹된 필드: {chips}</div>'
    else:
        masked_html = '<div class="masked">마스킹된 필드 없음</div>'

    if matches:
        rows = "".join(
            "<tr>"
            f'<td><code>{escape(str(m.get("rule_id", "")))}</code></td>'
            f'<td>{escape(str(m.get("reason", "")))}</td>'
            f'<td>{escape(str(m.get("risk", "")))}</td>'
            f'<td>{escape(str(m.get("decision", "")))}</td>'
            "</tr>"
            for m in matches
        )
        match_table = (
            '<table class="matches"><thead><tr><th>규칙 ID</th><th>사유</th><th>위험</th><th>결정</th></tr></thead>'
            f"<tbody>{rows}</tbody></table>"
        )
    else:
        match_table = '<p class="muted-line">매칭된 입력 규칙 없음 — 출력 검열 결과로 판정했습니다.</p>'

    summary = []
    if decision == "block":
        summary.append("입력 프롬프트가 정책 규칙에 매칭되어 모델 호출 전에 차단되었습니다.")
    elif decision == "review":
        summary.append("응답에서 민감정보가 탐지되어 마스킹 후 검토 상태로 전환되었습니다." if masked else "정책 검토가 필요한 결과입니다.")
    else:
        summary.append("정책 위반이 탐지되지 않아 요청이 허용되었습니다.")
    if risk in ("High", "Critical"):
        summary.append(f"위험 등급이 {risk}이므로 4단계에서 상위 대응 등급으로 분류될 가능성이 높습니다.")
    summary.append("최종 운영 이벤트 기록과 알림은 4단계 이후 단계의 책임입니다.")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>3단계 정책·출력 필터링 보고서</title>
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
  table.matches th, table.matches td {{ padding: .45rem .8rem; }}
  table.matches thead th {{ border-bottom: 2px solid var(--line); white-space: normal; }}
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
  .chip {{ display: inline-block; padding: .1rem .55rem; border-radius: 999px;
          background: var(--warn-bg); color: var(--warn); font-size: .78rem; font-weight: 700; }}
  .masked {{ margin-top: .6rem; font-size: .88rem; color: var(--muted); }}
  .summary {{ color: var(--muted); font-size: .92rem; line-height: 1.7; }}
  .muted-line {{ color: var(--muted); font-size: .88rem; }}
  pre.json {{
    background: var(--code-bg); color: var(--code-ink); border: 1px solid var(--line);
    border-radius: 10px;
    padding: .9rem 1rem; overflow-x: auto; white-space: pre-wrap;
    word-break: break-word; font-size: .84rem; margin: .5rem 0 0;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
  }}
  code {{ font-family: ui-monospace, Menlo, monospace; font-size: .85em; }}
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
    <div class="eyebrow">Step 03 · 실행 보고서</div>
    <h1>정책 차단·출력 필터링 결과 보고서</h1>
    <div class="doc-sub">입력 차단 + 출력 검열 — {escape(str(payload.get("event_id", "")))}</div>
  </div>

  <h2><span class="no">1.</span>보고서 정보</h2>
  <table>{info}</table>

  <h2><span class="no">2.</span>판정 요약</h2>
  <div class="verdict-row">
    {_badge(_DECISION, decision)}
    {_badge(_RISK, risk)}
    <span class="summary">{"<br>".join(escape(s) for s in summary)}</span>
  </div>
  {masked_html}

  <h2><span class="no">3.</span>판정 결과 텍스트 <span class="tag">사용자에게 반환되는 값</span></h2>
  {_pre(payload.get("text", ""))}

  <h2><span class="no">4.</span>정책 매칭 내역 <span class="tag">설명 가능한 근거</span></h2>
  {match_table}

  <h2><span class="no">5.</span>결과 규약 원본 <span class="tag">JSON 계약 필드</span></h2>
  {_pre(payload)}

  <h2><span class="no">6.</span>결론 및 다음 단계</h2>
  <div class="conclusion">
    이 결과는 <b>3단계 정책 엔진의 관측 산출물</b>입니다.<br>
    위험 등급 분류·보안 이벤트 기록·알림은 4단계 이후 단계에서 수행하며,<br>
    이 JSON은 <code>{escape(str(payload.get("next", "")))}</code> 단계의 입력으로 전달됩니다.
  </div>

  <p class="note">원본 데이터: 같은 이름의 <code>.json</code> 파일 · schema_version {escape(str(payload.get("schema_version", "")))}</p>
</div>
<footer>3단계 · 정책 차단·출력 필터링 실습 — ai-guardrails-ops</footer>
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
