# 4단계 슬라이드

| 순서 | 슬라이드 주제 | 산출물 |
| --- | --- | --- |
| s01 | 위험 등급 체계 설계 | 이벤트 분류와 대응 구조 |
| s02 | 위험 등급 설계 이론 | 영향·악용 가능성과 네 단계 등급 |
| s03 | 위험 등급 소스코드 | `risk.py` 점수와 이벤트 변환 |
| s04 | 코드 실행 흐름도 | risk.py 호출 순서·classify_risk 점수 규칙 |
| s05 | 보안 이벤트 산출물 형식 | step04-security-event.json 필드·생성 흐름 |
| s06 | 실습 순서 | 03 선행 → risk.py 변환·결과 확인 |
| s07 | 실습 Flow 도식 | 3단계 JSON → SecurityEvent 변환·5단계 전달 전체 절차 (1920×1080) |
| s08 | 복습 체크리스트 | 등급·대응·이벤트 확인 |
| s09 | 핵심 요약과 실습 질문 | 학습 내용과 완료 확인 |

기술 사양: [s00-tech-spec.svg](s00-tech-spec.svg)

실제 슬라이드: [s01-risk-rating.svg](s01-risk-rating.svg), [s02-risk-theory.svg](s02-risk-theory.svg), [s03-risk-source.svg](s03-risk-source.svg), [s04-runtime-flow.svg](s04-runtime-flow.svg), [s05-event-format.svg](s05-event-format.svg), [s06-practice-order.svg](s06-practice-order.svg), [s07-flow.svg](s07-flow.svg), [s08-risk-checklist.svg](s08-risk-checklist.svg), [s09-summary.svg](s09-summary.svg)

`s00-tech-spec.svg`는 위험 점수·이벤트·JSON 전달의 기술 사양 참고 자료다. `s01`~`s09`은 발표용 SVG이며, `s07-flow.svg`는 실습 절차 Flow 도식(1920×1080)이다., `s03-risk-source.svg`는 `src/risk.py` 실행과 변환 규약을, `s04-runtime-flow.svg`는 `risk.py`의 호출 순서와 `classify_risk` 점수 규칙을, `s05-event-format.svg`는 `step04-security-event.json`의 필드 구성과 생성 흐름을 설명한다.
