"""Render the step-06 integrated report payload as a standalone HTML report.

The report is generated from the same dict that ``app.py`` writes to
``step06-report.json``, so both artifacts always describe the same run.
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
    key = str(value)
    cls, ko = mapping.get(key, mapping.get(key.capitalize(), ("warn", key)))
    label = key.upper() if (key.islower() or key.capitalize() in mapping) else key
    return f'<span class="verdict {cls}"><span class="dot"></span>{escape(label)} · {ko}</span>'


def _metric_rows(metrics: dict[str, Any]) -> str:
    rows = [
        ("전체 이벤트", metrics.get("total_events", 0)),
        ("차단", metrics.get("blocked_events", 0)),
        ("검토", metrics.get("review_events", 0)),
        ("차단율", f"{float(metrics.get('block_rate', 0.0)) * 100:.1f}%"),
        ("검토율", f"{float(metrics.get('review_rate', 0.0)) * 100:.1f}%"),
        ("미처리(open)", metrics.get("open_events", 0)),
        ("확인됨(ack)", metrics.get("acknowledged_events", 0)),
    ]
    return "".join(
        f'<tr><th>{escape(str(k))}</th><td>{escape(str(v))}</td></tr>' for k, v in rows
    )


def _event_rows(events: list[dict[str, Any]]) -> str:
    if not events:
        return '<p class="summary">실행된 이벤트가 없습니다.</p>'
    rows = []
    for event in events:
        rows.append(
            "<tr>"
            f'<td>{escape(str(event.get("event_id", "—")))}</td>'
            f'<td>{_badge(_DECISION, event.get("decision", ""))}</td>'
            f'<td>{_badge(_RISK, event.get("risk", ""))}</td>'
            f'<td>{escape(str(event.get("category", "—")))}</td>'
            f'<td>{escape(str(event.get("detail", "—"))[:100])}</td>'
            "</tr>"
        )
    return (
        '<table><tr><th>이벤트 ID</th><th>판정</th><th>위험</th><th>카테고리</th><th>상세</th></tr>'
        + "".join(rows) + "</table>"
    )


def render_html(payload: dict[str, Any]) -> str:
    """Return a self-contained HTML document for the step06 run."""
    metrics = payload.get("metrics") or {}
    events = payload.get("events") or []
    upstream = payload.get("upstream_metrics")
    total = len(events)
    critical = sum(1 for e in events if str(e.get("risk", "")) == "Critical")

    badges = (
        f'<span class="verdict warn"><span class="dot"></span>EVENTS · {total}</span>'
        f'<span class="verdict {"bad" if critical else "ok"}"><span class="dot"></span>CRITICAL · {critical}</span>'
        f'<span class="verdict ok"><span class="dot"></span>BLOCK RATE · {float(metrics.get("block_rate", 0.0)) * 100:.1f}%</span>'
        f'<span class="verdict warn"><span class="dot"></span>LLM · {escape(str(payload.get("llm_mode", "—")))}</span>'
    )
    summary = [
        f"통합 실습 {total}건의 대표 요청을 정책·가드레일·관제 경로로 실행했습니다.",
        ("5단계 지표(upstream_metrics)가 함께 기록되었습니다." if upstream else "5단계 지표 파일이 없어 upstream_metrics는 비어 있습니다 — 5단계 report.py 실행 후 재실행하면 채워집니다."),
        "LLM 모드는 " + str(payload.get("llm_mode", "—")) + " — 모델 응답도 동일한 입력·출력 가드레일을 통과합니다.",
    ]

    upstream_block = (
        f'<h2><span class="no">5.</span>5단계 지표 (upstream_metrics)</h2>\n{_pre(upstream)}'
        if upstream else
        '<h2><span class="no">5.</span>5단계 지표 (upstream_metrics)</h2>\n'
        '<p class="summary">5단계 <code>results/step05-metrics.json</code>이 없어 비어 있습니다.</p>'
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>6단계 운영 리포트·통합 실습 보고서</title>
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
  .verdict-row {{ display: flex; align-items: center; gap: .7rem; flex-wrap: wrap;
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
    <div class="eyebrow">Step 06 · 실행 보고서</div>
    <h1>운영 리포트·통합 실습 보고서</h1>
    <div class="doc-sub">정책 → 가드레일 → 관제 → 통합 실행 — 생성 {escape(str(payload.get("generated_at", "")))}</div>
  </div>

  <h2><span class="no">1.</span>보고서 정보</h2>
  <table>
    <tr><th>스키마 버전</th><td>{escape(str(payload.get("schema_version", "—")))}</td></tr>
    <tr><th>단계</th><td>{escape(str(payload.get("step", "—")))} · source_stage {escape(str(payload.get("source_stage", "—")))}</td></tr>
    <tr><th>생성 시각</th><td>{escape(str(payload.get("generated_at", "—")))}</td></tr>
    <tr><th>LLM 모드</th><td>{escape(str(payload.get("llm_mode", "—")))}</td></tr>
    <tr><th>이벤트 수</th><td>{total}건</td></tr>
  </table>

  <h2><span class="no">2.</span>실행 요약</h2>
  <div class="verdict-row">
    {badges}
    <span class="summary">{"<br>".join(escape(s) for s in summary)}</span>
  </div>

  <h2><span class="no">3.</span>집계 지표</h2>
  <table>{_metric_rows(metrics)}</table>

  <h2><span class="no">4.</span>이벤트 내역 <span class="tag">{total}건</span></h2>
  {_event_rows(events)}

  {upstream_block}

  <h2><span class="no">6.</span>결과 규약 원본</h2>
  {_pre(payload)}

  <h2><span class="no">7.</span>결론</h2>
  <div class="conclusion">
    이 보고서는 <b>1~6단계 전체 흐름의 통합 실행 증거</b>입니다.<br>
    입력 정책 차단·출력 마스킹·위험 등급·Critical 알림이 하나의 실행으로 연결되며,<br>
    운영 개선안은 이 지표와 이벤트 내역을 근거로 작성합니다.
  </div>

  <p class="note">원본 데이터: 같은 이름의 <code>.json</code> 파일 · schema_version {escape(str(payload.get("schema_version", "")))}</p>
</div>
<footer>6단계 · 운영 리포트·통합 실습 — ai-guardrails-ops</footer>
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
