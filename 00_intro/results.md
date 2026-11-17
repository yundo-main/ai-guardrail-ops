# 단계 간 실습 결과 전달

각 단계의 소스코드는 독립·중복 유지한다. 단계 간 연결은 공통 Python import가 아니라 JSON 결과 파일 또는 5단계 HTTP API로 전달한다.

```text
03단계 결과 → step03-guardrail-result.json
04단계 이벤트 → step04-security-event.json
05단계 지표 → step05-metrics.json
06단계 통합 리포트 → step06-report.json
```

| 파일 | 생성 단계 | 다음 사용 단계 |
| --- | --- | --- |
| `step03-guardrail-result.json` | 정책 차단·출력 검열 | 4단계 위험 등급 |
| `step04-security-event.json` | 위험 등급·이벤트 생성 | 5단계 API·대시보드 |
| `step05-metrics.json` | API 지표 집계 | 6단계 운영 리포트 |
| `step06-report.json` | 통합 실행 | 최종 제출·개선안 |

각 단계는 자기 폴더의 `results/`에 결과를 저장한다(예: `03_policy_blocking_output_filtering/results/`).

## 결과 확인 명령

```bash
python3 -m json.tool 03_policy_blocking_output_filtering/results/step03-guardrail-result.json
python3 -m json.tool 04_risk_rating_system/results/step04-security-event.json
python3 -m json.tool 05_security_dashboard_alerts/results/step05-metrics.json
python3 -m json.tool 06_operations_report_integrated_lab/results/step06-report.json
```

5단계 결과는 API 서버에서 `GET /metrics`로 조회하며, 응답을 `step05-metrics.json`으로 저장하면 6단계가 자동으로 읽는다. 각 JSON의 `schema_version`, `event_id`, `trace_id`, `decision`, `risk`, `category`, `metrics`, `upstream_metrics` 필드를 중심으로 단계별 결과를 확인한다.

## 파일 역할

| 파일 | 위치 | 역할 |
| --- | --- | --- |
| `step03-guardrail-result.json` | `03_policy_blocking_output_filtering/results/` | 정책 차단·출력 마스킹 결과 |
| `step04-security-event.json` | `04_risk_rating_system/results/` | 위험 등급이 부여된 보안 이벤트 |
| `step05-metrics.json` | `05_security_dashboard_alerts/results/` | API에서 조회·저장한 운영 지표 |
| `step06-report.json` | `06_operations_report_integrated_lab/results/` | 최종 통합 실행과 운영 리포트 |
