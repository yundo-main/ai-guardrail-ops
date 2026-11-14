# 2단계 슬라이드

| 순서 | 슬라이드 주제 | 산출물 |
| --- | --- | --- |
| s01 | Llama Guard·NeMo Guardrails 적용 | 위험 분류와 대화 정책 흐름 |
| s02 | 두 Guardrails의 역할 이론 | 안전성 분류와 대화 흐름 제어 |
| s03 | 2단계 소스코드 관계도 | 규약·실행 진입점·provider·설정·결과 연결 |
| s04 | Llama Guard 역할 상세 | 분류·범주·정책 변환 |
| s05 | NeMo Guardrails 역할 상세 | 대화 흐름·주제·응답 경로 |
| s06 | 실행 백엔드 선택 | 기본 Ollama·심화 Transformers 경로 |
| s07 | 복습 체크리스트 | 분류·대화 정책·적용 확인 |
| s08 | 핵심 요약과 실습 질문 | 학습 내용과 완료 확인 |

기술 사양: [s00-tech-spec.svg](s00-tech-spec.svg)

실제 슬라이드: [s01-guard-models.svg](s01-guard-models.svg), [s02-guardrail-theory.svg](s02-guardrail-theory.svg), [s03-adapters-source.svg](s03-adapters-source.svg), [s04-llama-guard-detail.svg](s04-llama-guard-detail.svg), [s05-nemo-guardrails-detail.svg](s05-nemo-guardrails-detail.svg), [s06-runtime-choice.svg](s06-runtime-choice.svg), [s07-guardrail-checklist.svg](s07-guardrail-checklist.svg), [s08-summary.svg](s08-summary.svg)

`s00-tech-spec.svg`는 2단계 필수 기술과 실제 모델 연동 범위를 설명하는 참고 슬라이드다. `s01`~`s08`은 발표용 SVG이며, `s03-adapters-source.svg`는 2단계 소스 전체의 호출 방향과 설정·결과 관계를 보여준다. `s04`와 `s05`에서는 두 가드레일의 역할을 각각 분리해 설명한다.

실제 호출 실습은 `python3.12 src/main.py real --prompt "..."`로 수행하고, 결과는 `results/step02-real-guardrails.json`에서 확인한다.
