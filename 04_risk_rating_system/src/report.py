"""Render a step-04 security-event payload as a standalone HTML report.

The report is generated from the same dict that ``write_event_result()``
writes to JSON, so both artifacts always describe the same event.
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
_STATUS = {
    "open": ("warn", "미처리"),
    "acknowledged": ("ok", "확인됨"),
    "resolved": ("ok", "해결됨"),
}


def _pre(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    return f'<pre class="json">{escape(text)}</pre>'


def _badge(mapping: dict[str, tuple[str, str]], value: Any) -> str:
    key = str(value)
    cls, ko = mapping.get(key, mapping.get(key.capitalize(), ("warn", key)))
    label = key.upper() if (key.islower() or key.capitalize() in mapping) else key
    return f'<span class="verdict {cls}"><span class="dot"></span>{escape(label)} · {ko}</span>'


def render_html(payload: dict[str, Any]) -> str:
    """Return a self-contained HTML document for one security event."""
    decision = str(payload.get("decision", ""))
    risk = str(payload.get("risk", ""))
    status = str(payload.get("status", "open"))

    info_rows = [
        ("스키마 버전", payload.get("schema_version", "—")),
        ("이벤트 ID", payload.get("event_id", "—")),
        ("추적 ID", payload.get("trace_id", "—")),
        ("발생 시각", payload.get("timestamp", "—")),
        ("정책 버전", payload.get("policy_version", "—")),
        ("모델", payload.get("model_name") or "—"),
        ("단계", f"{payload.get('source_stage', '—')} → {payload.get('next', '—')}"),
    ]
    info = "".join(
        f'<tr><th>{escape(str(k))}</th><td>{escape(str(v))}</td></tr>'
        for k, v in info_rows
    )

    detail_rows = [
        ("카테고리", payload.get("category", "—")),
        ("상세", payload.get("detail") or "—"),
        ("처리 상태", payload.get("status", "—")),
        ("확인 시각", payload.get("acknowledged_at") or "—"),
    ]
    detail = "".join(
        f'<tr><th>{escape(str(k))}</th><td>{escape(str(v))}</td></tr>'
        for k, v in detail_rows
    )

    summary = []
    if risk == "Critical":
        summary.append("Critical 등급 — 즉시 알림·에스컬레이션 대상입니다.")
    elif risk == "High":
        summary.append("High 등급 — 담당자 검토·차단 조치가 필요한 수준입니다.")
    elif risk == "Medium":
        summary.append("Medium 등급 — 일상 모니터링 대상입니다.")
    else:
        summary.append("Low 등급 — 추세 관찰 수준입니다.")
    if status == "open":
        summary.append("아직 확인(acknowledge)되지 않은 open 상태입니다.")
    summary.append("대시보드 표시·알림 발송·지표 집계는 5단계 API의 책임입니다.")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>4단계 위험 등급·보안 이벤트 보고서</title>
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
    <div class="eyebrow">Step 04 · 실행 보고서</div>
    <h1>위험 등급·보안 이벤트 보고서</h1>
    <div class="doc-sub">3단계 판정 → 4단계 위험 분류·이벤트화 — {escape(str(payload.get("event_id", "")))}</div>
  </div>

  <h2><span class="no">1.</span>보고서 정보</h2>
  <table>{info}</table>

  <h2><span class="no">2.</span>판정 요약</h2>
  <div class="verdict-row">
    {_badge(_DECISION, decision)}
    {_badge(_RISK, risk)}
    {_badge(_STATUS, status)}
    <span class="summary">{"<br>".join(escape(s) for s in summary)}</span>
  </div>

  <h2><span class="no">3.</span>이벤트 상세</h2>
  <table>{detail}</table>

  <h2><span class="no">4.</span>결과 규약 원본 <span class="tag">5단계 API 입력 필드</span></h2>
  {_pre(payload)}

  <h2><span class="no">5.</span>결론 및 다음 단계</h2>
  <div class="conclusion">
    이 이벤트는 <b>4단계 위험 등급 분류의 산출물</b>입니다.<br>
    대시보드 등록·Critical 알림·지표 집계는 5단계 API(<code>POST /events</code>)에서 수행하며,<br>
    이 JSON은 <code>{escape(str(payload.get("next", "")))}</code> 단계로 전달됩니다.
  </div>

  <p class="note">원본 데이터: 같은 이름의 <code>.json</code> 파일 · schema_version {escape(str(payload.get("schema_version", "")))}</p>
</div>
<footer>4단계 · 위험 등급·보안 이벤트 실습 — ai-guardrails-ops</footer>
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
