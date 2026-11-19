# 4단계 · 위험 등급 체계 설계

## 이론적 배경

모든 보안 이벤트를 같은 긴급도로 처리하면 운영팀은 중요한 사건을 놓치거나 불필요한 알림에 매몰될 수 있다. 이벤트의 영향과 악용 가능성, 노출 범위를 기준으로 우선순위를 정해야 제한된 대응 자원을 효과적으로 배분할 수 있다.

위험 등급은 단순한 라벨이 아니라 대응 규약이다. 등급이 올라갈수록 차단, 에스컬레이션, 즉시 알림, 사후 분석 같은 더 강한 조치를 연결해야 하므로 4단계에서는 등급과 운영 행동을 함께 설계한다.

## 학습 목표

보안 이벤트의 영향과 긴급도를 기준으로 위험 등급과 대응 절차를 설계한다.

## 핵심 내용

- Low, Medium, High, Critical의 의미
- 영향 범위·악용 가능성·민감도·긴급도 기준
- 등급별 차단, 검토, 에스컬레이션, 사후 분석
- 이벤트에 남겨야 할 ID·시각·카테고리·판정·상세 정보

## 이론 보강

위험 등급은 공격의 이름이 아니라 예상되는 영향과 대응 긴급도를 나타낸다. 같은 유형의 요청이라도 노출된 데이터의 민감도, 대상 시스템의 범위, 실제 악용 가능성에 따라 등급이 달라질 수 있다.

등급 기준은 숫자만으로 끝내지 않고 행동 기준과 연결해야 한다. 예를 들어 Low는 추세 관찰, High는 담당자 검토와 차단, Critical은 즉시 알림과 에스컬레이션을 요구한다.

등급 변경은 이벤트 원본을 덮어쓰지 말고 변경자·시각·사유를 별도 기록한다. 그래야 사후 분석에서 최초 판정과 최종 대응을 비교할 수 있다.

## 실습

1. 입력 차단과 출력 검열 사례를 등급별로 분류한다.
2. 등급별 대응 시간과 담당자를 정의한다.
3. `src/monitoring.py`의 `SecurityEvent` 구조로 이벤트를 생성한다.

점수 기반 분류 예제는 `src/risk.py`에서 실행한다.

> 저장소 루트에서 실행한다. LLM·Ollama 없이 동작한다. **3단계 결과 파일이 먼저 필요하다.**

```bash
# 0) 4단계 단위 테스트 (선택)
python -m unittest discover -s 04_risk_rating_system/tests -v

# 1) 3단계 결과 생성 (아직 없다면 먼저 실행)
python 03_policy_blocking_output_filtering/src/guardrail.py

# 2) 4단계 실행 — 03 결과를 읽어 이벤트로 변환
#    → 04_risk_rating_system/results/ 에 JSON + HTML 생성
PYTHONPATH=04_risk_rating_system/src python 04_risk_rating_system/src/risk.py

# 3) 결과 확인
python -m json.tool 04_risk_rating_system/results/step04-security-event.json
open 04_risk_rating_system/results/step04-security-event.html
```

3단계 결과 파일(`03_policy_blocking_output_filtering/results/step03-guardrail-result.json`)이 있으면 위 명령이 이를 읽어 `results/step04-security-event.json`과 같은 이름의 `.html` 보고서를 생성한다. 파일이 없으면 점수 분류 예시만 출력된다.

## 산출물

- 위험 등급 기준표
- 등급별 대응 절차
- 보안 이벤트 필드 정의서
- `results/step04-security-event.json` API 전달 파일
- `results/step04-security-event.html` 판정·등급·이벤트 상세 보고서

## 단계 간 연결

[← 3단계](../03_policy_blocking_output_filtering/readme.md) · [5단계 →](../05_security_dashboard_alerts/readme.md) · [전체 과정](../readme.md)

`src/risk.py`의 `event_from_guardrail_file()`이 3단계 결과 JSON을 읽고 `SecurityEvent`로 변환한다. `write_event_result()`의 출력은 5단계 `/events` API에 전달할 수 있다.

## 완료 기준

같은 규칙을 반복 적용해 이벤트 등급을 일관되게 부여하고, Critical 이벤트의 즉시 대응 조건을 설명할 수 있다.

## 파일·디렉터리 역할

| 경로 | 역할 |
| --- | --- |
| `src/policy.py` | 4단계 이벤트 판정용 `Decision`·`RiskLevel` 정의 |
| `src/monitoring.py` | `SecurityEvent` 생성과 API 전달 payload 직렬화 |
| `src/risk.py` | 점수 기반 위험 분류와 3단계 JSON→4단계 이벤트 변환·JSON+HTML 저장 |
| `src/report.py` | 보안 이벤트 JSON을 독립 HTML 보고서로 렌더링 |
| `slides/s00-tech-spec.svg` | 위험 점수·이벤트·JSON 연결 기술 사양 |
| `slides/s01-risk-rating.svg` | 위험 등급 체계 개요 |
| `slides/s02-risk-theory.svg` | 등급 기준과 대응 이론 |
| `slides/s03-risk-source.svg` | `risk.py` 소스 설명 |
| `slides/s04-runtime-flow.svg` | 코드 실행 흐름도 — risk.py 호출 순서·점수 규칙 |
| `slides/s05-event-format.svg` | 보안 이벤트 산출물 형식 — JSON 필드·생성 흐름 |
| `slides/s06-practice-order.svg` | 실습 순서 — 03 선행·risk.py 변환·결과 확인 |
| `slides/s07-flow.svg` | 실습 Flow 도식 — 3단계 JSON → 이벤트 변환·5단계 전달 전체 절차 |
| `slides/s08-risk-checklist.svg` | 등급·대응·이벤트 체크리스트 |
| `slides/s09-summary.svg` | 4단계 핵심 요약과 질문 |
| `slides/readme.md` | 슬라이드 순서·제목·산출물 목록 |
