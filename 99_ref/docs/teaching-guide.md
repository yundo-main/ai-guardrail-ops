# 강의자용 진행 가이드

## 강의 운영 원칙

각 단계는 다음 순서로 진행한다.

```text
배경 설명 → 개념 → 강사 시연 → 따라하기 → 독립 실습 → 결과 확인 → 정리
```

단계별 폴더는 독립 실행을 유지하고, 수업의 점층성은 이전 단계의 구조와 결과를 다음 단계에서 확장하는 방식으로 설명한다. 실제 provider 호출은 기본 Ollama 경로를 먼저 사용하고, Transformers 기반 Llama Guard는 2단계 심화 실습으로 분리한다.

## 단계별 진행표

| 단계 | 강의 핵심 | 강사 시연 | 수강생 실습 | 결과 확인 |
| --- | --- | --- | --- | --- |
| 01 | 입력·모델·출력·관제 위치 | `architecture.py` 실행 | 빈 입력·정상 입력·빈 응답 비교 | `PipelineResult` 출력 |
| 02 | 분류와 대화 정책 분리 | `adapters.py`와 Ollama 경로 설명 | 역할·handoff 표 작성 | 결과 JSON과 관계 SVG |
| 03 | 정책 판정과 출력 마스킹 | `guardrail.py` 실행 | 인젝션·PII·정상 사례 테스트 | `step03-guardrail-result.json` |
| 04 | 위험 등급과 이벤트 | `risk.py` 실행 | 같은 결과의 등급 변환 | `step04-security-event.json` |
| 05 | API·SQLite·관제 | `/events`, `/metrics` 호출 | 실제 이벤트 등록·acknowledge | Dashboard·Critical 알림 |
| 06 | 운영 리포트와 피드백 | `app.py` 실행 | 기간별 지표·개선안 작성 | `step06-report.json` |

## 단계별 강의 포인트

### 01단계

모델 호출 자체보다 통제 지점의 위치를 먼저 이해시킨다. `run_pipeline()`의 더미 모델은 이후 모델 교체를 위한 자리표시자다.

### 02단계

Llama Guard는 안전성 분류, NeMo Guardrails는 대화 흐름 제어라는 차이를 먼저 설명한다. 기본 실습은 Ollama, Transformers는 별도 심화 경로로 진행한다.

### 03단계

provider의 탐지 결과와 애플리케이션의 최종 결정이 다르다는 점을 확인한다. `safe_response()`가 입력 차단 후 출력 마스킹 순서를 보장하는지 검증한다.

### 04단계

위험 등급은 모델의 원시 결과가 아니라 조직의 대응 우선순위로 변환된 결과임을 설명한다.

### 05단계

보안 이벤트를 저장하는 것에서 끝내지 않고 지표·알림·확인 상태까지 운영 흐름으로 연결한다.

### 06단계

리포트는 실행 로그의 복사가 아니라 기준선·변화·원인·다음 개선 과제를 포함한 운영 의사결정 자료임을 강조한다.

## 강의 전 점검

- Python 3.12 환경과 루트 `requirements.txt` 설치
- `python3 -m unittest discover -s tests -v` 통과
- 각 `slides/*.svg`를 브라우저로 직접 열어 SVG 열람 확인
- 5단계 API 포트와 API 키 확인
- 기본 Ollama 경로를 사용할 경우 `ollama serve`와 모델 준비
- Transformers 심화 실습을 사용할 경우 별도 모델 권한·가중치·GPU 확인

## 수업 후 산출물

| 평가 범주 | 제출 내용 |
| --- | --- |
| 이론 | 주요 위협과 각 가드레일 기술의 역할 설명 |
| 코드 | 입력 차단·출력 검열·위험 등급 분류의 정상 동작 |
| 관제 | 이벤트 집계·Critical 알림·운영 리포트 생성 |
| 시각화 | 보안 처리 흐름을 이해하기 쉬운 SVG 슬라이드 |
| 제출물 | 파이썬 소스·SVG 슬라이드·실행 결과 JSON·캡처 이미지 |

수강생이 제출하는 JSON 산출물 경로:

- `99_ref/results/step03-guardrail-result.json` — 정책 판단 근거
- `99_ref/results/step04-security-event.json` — 위험 등급 이유
- `99_ref/results/step05-metrics.json` — 대시보드 지표
- `99_ref/results/step06-report.json` — 최종 운영 리포트와 개선안
