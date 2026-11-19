"""Weekly/monthly operations report (step06 capability)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
import json

from observe.metrics import metrics

PERIOD_DAYS = {"weekly": 7, "monthly": 30}
RECENT_EVENTS_LIMIT = 20


def period_report(events, period: str = "weekly", now: datetime | None = None) -> dict:
    if period not in PERIOD_DAYS:
        raise ValueError("period must be weekly or monthly")
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=PERIOD_DAYS[period])
    recent = [e for e in events
              if datetime.fromisoformat(e.timestamp) >= cutoff]
    m = metrics(list(recent))
    actions = ["반복 카테고리의 정책 오탐·미탐을 재평가"]
    if m["by_risk"].get("Critical"):
        actions.insert(0, "Critical 이벤트의 담당자와 대응 기한을 확인")
    if m["open_events"]:
        actions.append(f"미확인 이벤트 {m['open_events']}건 확인(acknowledge)")
    recent_sorted = sorted(recent, key=lambda e: e.timestamp, reverse=True)
    return {"period": period, "period_days": PERIOD_DAYS[period],
            "generated_at": now.isoformat(), "events_in_period": len(recent),
            "metrics": m, "next_actions": actions,
            "recent_events": [e.as_dict() for e in recent_sorted[:RECENT_EVENTS_LIMIT]]}


def _esc(value) -> str:
    return escape(str(value if value is not None else "-"))


def _badge(label: str, value, cls: str = "") -> str:
    return f'<span class="badge {cls}">{_esc(label)} <b>{_esc(value)}</b></span>'


def _dist_table(title: str, dist: dict) -> str:
    if not dist:
        return ""
    rows = "".join(f"<tr><td>{_esc(k)}</td><td class='num'>{_esc(v)}</td></tr>"
                   for k, v in sorted(dist.items(), key=lambda kv: -kv[1]))
    return (f"<h3>{_esc(title)}</h3><table><tr><th>구분</th><th>건수</th></tr>"
            f"{rows}</table>")


def _event_rows(events: list[dict]) -> str:
    if not events:
        return "<p class='muted'>기간 내 이벤트가 없습니다.</p>"
    rows = []
    for e in events:
        detail = (e.get("detail") or "")[:120]
        rows.append(
            "<tr>"
            f"<td class='mono'>{_esc(e.get('event_id', '')[:18])}</td>"
            f"<td>{_esc((e.get('timestamp') or '')[:19].replace('T', ' '))}</td>"
            f"<td>{_esc(e.get('decision'))}</td>"
            f"<td>{_esc(e.get('risk'))}</td>"
            f"<td>{_esc(e.get('category'))}</td>"
            f"<td>{_esc(e.get('status'))}</td>"
            f"<td>{_esc(detail)}</td>"
            "</tr>")
    return ("<table><tr><th>이벤트 ID</th><th>시각</th><th>판정</th><th>위험</th>"
            "<th>카테고리</th><th>상태</th><th>상세</th></tr>" + "".join(rows) + "</table>")


def render_html(payload: dict) -> str:
    """Render a period_report payload as a standalone printable HTML document."""
    m = payload.get("metrics", {})
    actions = payload.get("next_actions", [])
    events = payload.get("recent_events", [])
    period_label = {"weekly": "주간", "monthly": "월간"}.get(payload.get("period"), payload.get("period"))
    action_items = "".join(f"<li>{_esc(a)}</li>" for a in actions) or "<li class='muted'>없음</li>"
    metric_rows = "".join(
        f"<tr><td>{_esc(k)}</td><td class='num'>{_esc(v)}</td></tr>"
        for k, v in m.items() if k not in ("by_risk", "by_category", "schema_version"))
    dist = (_dist_table("위험 등급 분포", m.get("by_risk", {}))
            + _dist_table("카테고리 분포", m.get("by_category", {})))
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Guardrail 운영 리포트 — {period_label}</title>
<style>
body{{font-family:-apple-system,'Segoe UI',sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;color:#1f2937;line-height:1.5}}
h1{{font-size:1.5rem}} h2{{font-size:1.1rem;margin-top:2rem;border-bottom:2px solid #e5e7eb;padding-bottom:.3rem}}
h3{{font-size:.95rem;margin:.8rem 0 .3rem}}
table{{border-collapse:collapse;width:100%;font-size:.85rem;margin:.5rem 0}}
th,td{{border:1px solid #e5e7eb;padding:.35rem .6rem;text-align:left}}
th{{background:#f3f4f6}} td.num{{text-align:right;font-variant-numeric:tabular-nums}}
.mono{{font-family:ui-monospace,monospace;font-size:.78rem}}
.badge{{display:inline-block;background:#eff6ff;border:1px solid #bfdbfe;border-radius:999px;padding:.25rem .8rem;margin:.15rem .3rem .15rem 0;font-size:.85rem}}
.badge b{{color:#1d4ed8}}
.badges{{margin:.8rem 0}}
.muted{{color:#6b7280}} .meta{{color:#6b7280;font-size:.85rem}}
details{{margin:.8rem 0}} summary{{cursor:pointer;font-weight:600;color:#374151}}
pre{{background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:.8rem;overflow:auto;font-size:.78rem}}
@media print{{body{{margin:0}} details{{display:block}} details>*{{display:block}}}}
@media (prefers-color-scheme:dark){{body{{background:#111827;color:#e5e7eb}} th{{background:#1f2937}} td,th{{border-color:#374151}} pre{{background:#0b1220}} .badge{{background:#172554;border-color:#1e3a8a}} .badge b{{color:#93c5fd}} h2{{border-color:#374151}} summary{{color:#d1d5db}}}}
</style></head><body>
<h1>AI Guardrail 운영 리포트 — {period_label}({payload.get('period_days')}일)</h1>
<p class="meta">생성: {_esc(payload.get('generated_at'))} · 기간 내 이벤트: <b>{_esc(payload.get('events_in_period'))}건</b></p>
<div class="badges">
{_badge('전체 이벤트', m.get('total_events'))}
{_badge('차단', m.get('blocked_events'))}
{_badge('검토', m.get('review_events'))}
{_badge('차단율', (str(round(m.get('block_rate', 0) * 100, 1)) + '%') if isinstance(m.get('block_rate'), (int, float)) else m.get('block_rate'))}
{_badge('미확인', m.get('open_events'))}
{_badge('확인됨', m.get('acknowledged_events'))}
</div>
<h2>지표 상세</h2>
<details><summary>지표 표·분포 보기</summary>
<table><tr><th>지표</th><th>값</th></tr>{metric_rows}</table>
{dist}</details>
<h2>다음 조치</h2>
<ul>{action_items}</ul>
<h2>최근 이벤트 (최대 {RECENT_EVENTS_LIMIT}건)</h2>
{_event_rows(events)}
<p class="muted">원문 프롬프트는 저장·표시하지 않습니다(프라이버시 원칙).</p>
<h2>원본 JSON</h2>
<details><summary>규약 데이터 보기</summary><pre>{escape(json.dumps(payload, ensure_ascii=False, indent=2))}</pre></details>
</body></html>"""
