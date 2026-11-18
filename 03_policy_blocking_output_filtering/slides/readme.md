# 3단계 슬라이드

| 순서 | 슬라이드 주제 | 산출물 |
| --- | --- | --- |
| s01 | 정책 기반 차단 및 출력 검열 | 입력 판정과 출력 마스킹 흐름 |
| s02 | 정책 차단과 출력 검열 이론 | 판정 기준과 마스킹 원칙 |
| s03 | 정책과 가드레일 소스코드 | `policy.py`·`guardrail.py` 실행 |
| s04 | 코드 실행 흐름도 | guardrail.py 호출 순서·판정 분기 |
| s05 | 정책 규칙 구조 | policy-rules.json 필드와 매칭 흐름 |
| s06 | 실습 순서 | guardrail.py 실행·결과 확인 명령 |
| s07 | 실습 Flow 도식 | guardrail.py 실행부터 결과 JSON·4단계 전달까지의 전체 절차 (1920×1080) |
| s08 | 복습 체크리스트 | 정책·검열·테스트 확인 |
| s09 | LLM 없이 가능한 실습 | 결정론적 정책·마스킹 vs 모델 판정 단계 구분 |
| s10 | 핵심 요약과 실습 질문 | 학습 내용과 완료 확인 |

기술 사양: [s00-tech-spec.svg](s00-tech-spec.svg)

실제 슬라이드: [s01-policy-filtering.svg](s01-policy-filtering.svg), [s02-policy-theory.svg](s02-policy-theory.svg), [s03-policy-source.svg](s03-policy-source.svg), [s04-runtime-flow.svg](s04-runtime-flow.svg), [s05-policy-structure.svg](s05-policy-structure.svg), [s06-practice-order.svg](s06-practice-order.svg), [s07-flow.svg](s07-flow.svg), [s08-policy-checklist.svg](s08-policy-checklist.svg), [s09-no-llm.svg](s09-no-llm.svg), [s10-summary.svg](s10-summary.svg)

`s00-tech-spec.svg`는 정책 파일·결과 규약을 포함한 기술 사양 참고 자료다. `s01`~`s10`은 발표용 SVG이며, `s07-flow.svg`는 실습 절차 Flow 도식(1920×1080)이다., `s03-policy-source.svg`는 `src/policy.py`와 `src/guardrail.py`를 설명한다. `s04-runtime-flow.svg`는 `guardrail.py`의 함수 호출 순서와 판정 분기를, `s05-policy-structure.svg`는 `policy-rules.json`의 규칙 필드와 매칭 흐름을, `s09-no-llm.svg`는 이 단계가 LLM 없이 실행 가능함을 설명한다.
