"""Step 05: dashboard metrics, alert payloads, and standalone HTML report."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
from typing import Any

from monitoring import critical_alert, dashboard_metrics


def dashboard_payload(events):
    """Build the minimal payload consumed by a dashboard or alert worker."""
    # 지표와 Critical 필터를 하나의 외부 연동용 payload로 묶는다.
    # 웹 대시보드나 알림 워커가 Python 내부 객체를 알 필요 없도록 JSON 경계를 만든다.
    # 실제 운영에서는 이 payload를 인증된 API 응답이나 메시지 큐로 전달한다.
    metrics = dashboard_metrics(list(events))
    return {"dashboard": metrics, "alert_filter": {"risk": "Critical"}}


def period_report(events, period: str = "weekly"):
    """Create a report envelope that can be used for weekly or monthly review."""
    # 기간을 데이터와 함께 남겨 같은 지표를 주간·월간으로 비교할 수 있게 한다.
    # 허용 기간을 제한해야 서로 다른 리포트의 지표 정의가 흔들리지 않는다.
    if period not in {"weekly", "monthly"}:
        raise ValueError("period must be weekly or monthly")
    return {
        "period": period,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": dashboard_metrics(list(events)),
        "next_actions": [
            "Critical 이벤트의 담당자와 대응 기한을 확인",
            "반복 카테고리의 정책 오탐·미탐을 재평가",
        ],
    }


def metrics_payload(events) -> dict[str, Any]:
    """Build the step05 result payload: flat metrics + critical alerts."""
    # metrics-v1 규약의 평면 필드를 최상위에 두고 Critical 알림 목록을 함께 담는다.
    # 6단계는 이 파일을 upstream_metrics로 읽어 운영 리포트에 반영한다.
    alerts = [alert for event in events if (alert := critical_alert(event))]
    return {
        "schema_version": "1.0",
        "source_stage": "step05",
        "next": "06_operations_report_integrated_lab",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **dashboard_metrics(list(events)),
        "critical_alerts": alerts,
    }


def _pre(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    return f'<pre class="json">{escape(text)}</pre>'


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


def _dist_table(title: str, data: dict[str, Any]) -> str:
    if not data:
        return f'<h3 style="font-size:.9rem;color:var(--muted);margin:.8rem 0 .2rem">{escape(title)} — 기록 없음</h3>'
    items = "".join(
        f'<tr><td>{escape(str(k))}</td><td style="text-align:right">{escape(str(v))}</td></tr>'
        for k, v in sorted(data.items(), key=lambda kv: -int(kv[1]))
    )
    return (
        f'<h3 style="font-size:.9rem;color:var(--muted);margin:.8rem 0 .2rem">{escape(title)}</h3>'
        f'<table><tr><th>항목</th><th style="text-align:right">건수</th></tr>{items}</table>'
    )


def _alert_rows(alerts: list[dict[str, Any]]) -> str:
    if not alerts:
        return '<p class="summary">Critical 알림이 없습니다.</p>'
    rows = []
    for alert in alerts:
        event = alert.get("event") or {}
        rows.append(
            "<tr>"
            f'<td>{escape(str(event.get("event_id", "—")))}</td>'
            f'<td>{escape(str(event.get("category", "—")))}</td>'
            f'<td>{escape(str(event.get("detail", "—"))[:120])}</td>'
            f'<td>{escape(str(event.get("timestamp", "—")))}</td>'
            "</tr>"
        )
    return (
        '<table><tr><th>이벤트 ID</th><th>카테고리</th><th>상세</th><th>시각</th></tr>'
        + "".join(rows) + "</table>"
    )


def render_html(payload: dict[str, Any]) -> str:
    """Return a self-contained HTML operations report for step05 metrics."""
    metrics = {k: v for k, v in payload.items() if k not in {
        "schema_version", "source_stage", "next", "generated_at", "critical_alerts"}}
    alerts = payload.get("critical_alerts") or []
    critical_count = len(alerts)
    total = int(metrics.get("total_events", 0))

    badges = (
        f'<span class="verdict warn"><span class="dot"></span>EVENTS · {total}</span>'
        f'<span class="verdict {"bad" if critical_count else "ok"}"><span class="dot"></span>'
        f'CRITICAL · {critical_count}</span>'
        f'<span class="verdict ok"><span class="dot"></span>'
        f'BLOCK RATE · {float(metrics.get("block_rate", 0.0)) * 100:.1f}%</span>'
    )
    summary = [
        f"저장된 보안 이벤트 {total}건을 집계했습니다.",
        f"Critical 알림 {critical_count}건" + (" — Discord 웹훅·대시보드 확인이 필요합니다." if critical_count else " — 즉시 대응이 필요한 이벤트는 없습니다."),
        "최종 운영 리포트는 6단계가 이 지표를 upstream_metrics로 읽어 작성합니다.",
    ]

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>5단계 보안 대시보드·알림 보고서</title>
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
    <div class="eyebrow">Step 05 · 실행 보고서</div>
    <h1>보안 대시보드·알림 운영 보고서</h1>
    <div class="doc-sub">SQLite 이벤트 저장소 → 지표 집계·Critical 알림 — 생성 {escape(str(payload.get("generated_at", "")))}</div>
  </div>

  <h2><span class="no">1.</span>보고서 정보</h2>
  <table>
    <tr><th>스키마 버전</th><td>{escape(str(payload.get("schema_version", "—")))}</td></tr>
    <tr><th>단계</th><td>{escape(str(payload.get("source_stage", "—")))} → {escape(str(payload.get("next", "—")))}</td></tr>
    <tr><th>생성 시각</th><td>{escape(str(payload.get("generated_at", "—")))}</td></tr>
    <tr><th>알림 채널</th><td>Discord webhook (<code>discord.py WEBHOOK_URL</code>) · 대시보드 <code>/dashboard</code></td></tr>
  </table>

  <h2><span class="no">2.</span>운영 지표 요약</h2>
  <div class="verdict-row">
    {badges}
    <span class="summary">{"<br>".join(escape(s) for s in summary)}</span>
  </div>

  <h2><span class="no">3.</span>지표 상세</h2>
  <table>{_metric_rows(metrics)}</table>
  {_dist_table("위험 등급 분포 (by_risk)", metrics.get("by_risk") or {})}
  {_dist_table("카테고리 분포 (by_category)", metrics.get("by_category") or {})}

  <h2><span class="no">4.</span>Critical 알림 목록 <span class="tag">{critical_count}건</span></h2>
  {_alert_rows(alerts)}

  <h2><span class="no">5.</span>결과 규약 원본</h2>
  {_pre(payload)}

  <h2><span class="no">6.</span>결론 및 다음 단계</h2>
  <div class="conclusion">
    이 보고서는 <b>5단계 관제 계층의 스냅샷</b>입니다.<br>
    Critical 이벤트는 등록 시점에 Discord 웹훅으로도 발송되며(<code>WEBHOOK_URL</code> 설정 시),<br>
    이 JSON은 <code>{escape(str(payload.get("next", "")))}</code> 단계가 <code>upstream_metrics</code>로 읽어 최종 운영 리포트를 작성합니다.
  </div>

  <p class="note">원본 데이터: 같은 이름의 <code>.json</code> 파일 · schema_version {escape(str(payload.get("schema_version", "")))}</p>
</div>
<footer>5단계 · 보안 대시보드·알림 실습 — ai-guardrails-ops</footer>
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


def write_metrics_result(events, directory: str | Path) -> tuple[Path, Path]:
    """Persist metrics JSON + HTML report under ``directory``; return both paths."""
    target_dir = Path(directory)
    target_dir.mkdir(parents=True, exist_ok=True)
    payload = metrics_payload(events)
    json_path = target_dir / "step05-metrics.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path = write_report(payload, json_path.with_suffix(".html"))
    return json_path, html_path


if __name__ == "__main__":
    import store

    store.initialize()
    json_path, html_path = write_metrics_result(
        store.list_events(),
        Path(__file__).resolve().parents[1] / "results",
    )
    print(f"metrics JSON: {json_path}")
    print(f"report HTML:  {html_path}")
