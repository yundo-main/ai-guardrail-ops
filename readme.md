# 7장. AI 가드레일과 보안 관제 운영

## SVG 슬라이드 보기

각 `slides/*.svg` 파일을 브라우저로 바로 열면 된다(Finder에서 더블클릭 또는 `open <파일>.svg`). 전체 슬라이드 목록은 각 단계의 `slides/readme.md`에 있다.

강의 진행 순서와 강사 시연·수강생 실습·결과 확인 기준은 [teaching-guide.md](99_ref/docs/teaching-guide.md)를 참고한다.

AI 서비스 운영 단계에서 입력·출력 가드레일, 위험 분류, 보안 이벤트 관제, 알림, 운영 리포트를 연결하는 실습 과정이다.

### 루트 SVG 권장 열람 순서

1. [99_ref/docs/slides/00-course-flow.svg](99_ref/docs/slides/00-course-flow.svg) — 전체 학습 지도
2. [99_ref/docs/slides/01-practice-guide.svg](99_ref/docs/slides/01-practice-guide.svg) — 실제 강의·실습 진행 순서
3. [99_ref/docs/slides/02-technology-stack.svg](99_ref/docs/slides/02-technology-stack.svg) — 설치·실행에 필요한 기술
4. [99_ref/docs/slides/03-integration-flow.svg](99_ref/docs/slides/03-integration-flow.svg) — 단계별 독립성과 점층 통합 관계
5. [99_ref/docs/slides/04-result-check.svg](99_ref/docs/slides/04-result-check.svg) — 실행 결과·API·대시보드 확인 방법

학습에 필요한 런타임·API·선택적 LLM·SVG·검증 도구는 [99_ref/docs/slides/02-technology-stack.svg](99_ref/docs/slides/02-technology-stack.svg)에서 한눈에 확인할 수 있다.

각 단계에 필요한 기술만 정리한 기술 사양 SVG는 각 폴더의 `slides/s00-tech-spec.svg`에서 확인한다.

독립 단계 실습은 기존 01~06단계 폴더에서 진행하고, 점층적인 실제형 통합 실습은 [99_ref/integration/README.md](99_ref/integration/README.md)를 따른다. 결과 계약과 품질 평가 기준은 [99_ref/contracts/README.md](99_ref/contracts/README.md)에서 확인한다.

## 전체 목표

- AI 서비스의 입력과 출력을 정책에 따라 검사한다.
- 위험 요청을 차단하고 안전한 대체 응답을 반환한다.
- PII·기밀정보·API 키 등 민감한 출력을 마스킹한다.
- 보안 이벤트를 Critical/High/Medium/Low로 분류한다.
- 차단 건수·공격 유형·위험 등급을 대시보드 지표로 집계한다.
- Critical 이벤트 알림과 주간·월간 운영 리포트를 구성한다.

## 챕터 목록

| 단계 | 챕터 | 학습 목표 | 학습 자료 |
| --- | --- | --- | --- |
| 1단계 | Guardrail 개념과 아키텍처 | Guardrail의 개념과 입력·출력 통제 구조를 이해한다. | [01_guardrail_concept_architecture](01_guardrail_concept_architecture/readme.md) |
| 2단계 | Llama Guard·NeMo Guardrails 적용 | 위험 분류와 대화 정책의 역할을 이해한다. | [02_llama_guard_nemo_guardrails](02_llama_guard_nemo_guardrails/readme.md) |
| 3단계 | 정책 기반 차단 및 출력 검열 구현 | 정책 차단과 출력 마스킹을 구현한다. | [03_policy_blocking_output_filtering](03_policy_blocking_output_filtering/readme.md) |
| 4단계 | 위험 등급 체계 설계 | 보안 이벤트를 위험 등급으로 분류한다. | [04_risk_rating_system](04_risk_rating_system/readme.md) |
| 5단계 | 보안 대시보드 및 알림 구축 | 보안 지표를 집계하고 Critical 알림을 구성한다. | [05_security_dashboard_alerts](05_security_dashboard_alerts/readme.md) |
| 6단계 | 운영 리포트 작성 및 통합 실습 | 운영 지표를 리포트로 정리하고 전체 흐름을 통합한다. | [06_operations_report_integrated_lab](06_operations_report_integrated_lab/readme.md) |

## 처리 흐름

```text
사용자 입력
  → 입력 가드레일: 허용 / 차단 / 검토
  → 모델 호출
  → 출력 검열: PII·기밀 키워드·API 키 마스킹
  → 보안 이벤트 생성
  → 위험 등급 분류
  → 대시보드 집계 및 Critical 알림
  → 주간·월간 운영 리포트
```

## 로컬 구현 예제

외부 API나 LLM 없이 핵심 흐름을 재현하는 교육용 예제다.

권장 실행 환경은 Python 3.12 이상이다. 현재 코드와 테스트는 Python 3.9 호환성을 유지하며, Python 3.12.16 격리 환경에서도 전체 테스트를 검증했다. API 실행에는 루트 `requirements.txt`의 FastAPI·Uvicorn·테스트 클라이언트 의존성이 필요하다.

| 파일 | 역할 |
| --- | --- |
| `03_policy_blocking_output_filtering/src/` | 입력 정책, 입력 차단, 출력 PII·비밀정보 마스킹 |
| `04_risk_rating_system/src/` | 보안 이벤트와 위험 등급 정의 |
| `05_security_dashboard_alerts/src/` | 지표 집계와 Critical 알림 |
| `06_operations_report_integrated_lab/src/app.py` | 정상·위험·민감 출력 통합 실행 |
| `06_operations_report_integrated_lab/src/llm.py` | 선택적 로컬 Ollama 호출 어댑터 |
| `99_ref/results/` | 단계 간 JSON 결과 전달과 실습 증거 |
| `01_guardrail_concept_architecture/src/` | Guardrail 파이프라인 단계 정의 |
| `02_llama_guard_nemo_guardrails/src/main.py` | 2단계 진입점 — `contracts/`·`classifier/`·`dialogue/`·`pipeline/` 하위 구조 |
| `99_ref/tests/test_guardrail.py` | 핵심 동작 단위 테스트 |
| `99_ref/docs/slides/00-course-flow.svg` | 1~6단계 학습 흐름도 |
| `01_guardrail_concept_architecture/slides/s01-guardrail-flow.svg` | 입력·출력 가드레일과 관제 흐름도 |

단계별 슬라이드 구성표는 각 단계 폴더의 `slides/readme.md`에 분리했다.

### 실행

```bash
# 최초 환경 구성
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt

# 전체 테스트
python3 -m unittest discover -s tests -v

# 1~4단계 단독 실행 및 결과 생성
python3 01_guardrail_concept_architecture/src/architecture.py
python3 02_llama_guard_nemo_guardrails/src/main.py
python3 03_policy_blocking_output_filtering/src/guardrail.py
PYTHONPATH=04_risk_rating_system/src python3 04_risk_rating_system/src/risk.py

# 5단계 API 서버 — 별도 터미널에서 계속 실행
python3 -m pip install -r 05_security_dashboard_alerts/requirements.txt
uvicorn api:app --app-dir 05_security_dashboard_alerts/src --reload --port 8000

# 5단계 API를 종료한 뒤 새 터미널에서 6단계 실행
python3 06_operations_report_integrated_lab/src/app.py

# 3~4~6단계 파일 흐름 자동 실행
python3 99_ref/scripts/run_pipeline.py
```

### 실행 결과 확인

1~2단계는 터미널에 구조 요약을 출력한다. 3~4단계와 6단계는 실행 후 `99_ref/results/`에 JSON 결과를 저장한다.

```bash
# JSON을 사람이 읽기 좋은 형식으로 확인
python3 -m json.tool 99_ref/results/step03-guardrail-result.json
python3 -m json.tool 99_ref/results/step04-security-event.json
python3 -m json.tool 99_ref/results/step05-metrics.json
python3 -m json.tool 99_ref/results/step06-report.json
```

5단계 API는 서버를 켠 별도 터미널에서 다음처럼 확인한다.

```bash
curl http://127.0.0.1:8000/health
curl -H 'X-API-Key: dev-only-key' http://127.0.0.1:8000/events
curl -H 'X-API-Key: dev-only-key' http://127.0.0.1:8000/metrics
curl -H 'X-API-Key: dev-only-key' http://127.0.0.1:8000/alerts/critical
```

브라우저에서 `http://127.0.0.1:8000/docs`를 열면 Swagger UI로 요청을 직접 실행할 수 있다. 5단계 지표를 파일로 보관하려면 `/metrics` 응답을 `99_ref/results/step05-metrics.json`으로 저장한다.

```bash
curl -H 'X-API-Key: dev-only-key' http://127.0.0.1:8000/metrics > 99_ref/results/step05-metrics.json
```

각 단계의 실행 목적과 산출물은 해당 폴더의 `readme.md`, 슬라이드 목록은 `slides/readme.md`, 강의 진행표는 [teaching-guide.md](99_ref/docs/teaching-guide.md), 단계 간 JSON 계약은 `99_ref/results/README.md`에서 확인한다.

### 선택적 로컬 LLM 실행

기본 실행은 더미 응답을 사용한다. Ollama를 설치하고 서버와 모델을 준비한 뒤 `USE_LLM=1`을 지정하면 6단계 통합 실습이 로컬 모델 응답을 받아 출력 검열 단계로 전달한다.

```bash
ollama serve
ollama pull qwen2.5:3b
USE_LLM=1 OLLAMA_MODEL=qwen2.5:3b python3 06_operations_report_integrated_lab/src/app.py
```

### 5단계 웹 API·대시보드

API는 기본적으로 `dev-only-key`를 사용한다. 공유·배포 전에는 `GUARDRAIL_API_KEY`를 반드시 변경하고, 저장 위치는 `GUARDRAIL_DB_PATH`로 지정한다.

```bash
export GUARDRAIL_API_KEY='change-me'
uvicorn api:app --app-dir 05_security_dashboard_alerts/src --reload --port 8000
```

- Swagger: `http://127.0.0.1:8000/docs`
- 웹 대시보드: `http://127.0.0.1:8000/dashboard`
- 저장소: 기본 `99_ref/results/security_events.db` SQLite

대시보드 화면의 API Key 입력란에 동일한 키를 입력한다. 이벤트 등록 시에는 `X-API-Key` 헤더를 사용한다.

```bash
curl -X POST http://127.0.0.1:8000/events \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-only-key' \
  --data @99_ref/results/step04-security-event.json
```

`OLLAMA_BASE_URL`로 다른 로컬 Ollama 주소를 지정할 수 있다. 서버가 없거나 호출에 실패하면 더미 응답으로 자동 대체되며, 모델 응답도 동일하게 `safe_response()`의 입력·출력 가드레일을 통과한다.

실행 예제는 다음을 확인한다.

- 정상 요청은 허용된다.
- 프롬프트 인젝션·비밀정보 탈취 요청은 차단된다.
- 이메일·API 키 등 민감한 출력은 마스킹된다.
- Critical 이벤트는 알림 payload로 생성된다.
- 차단 건수와 위험 등급 분포가 리포트 지표로 집계된다.

## 단계별 학습 흐름

1단계에 개념과 아키텍처를 세우고, 2~5단계에 정책·검열·위험 분류·관제를 구현한 뒤, 6단계에 운영 리포트와 전체 흐름을 통합한다.

각 단계 README는 학습 목표보다 먼저 해당 주제를 배우는 이유와 앞뒤 단계와의 연결을 설명하는 `이론적 배경`으로 시작한다.

단계별 소스코드는 독립·중복 유지하고, 단계 간 연결은 [99_ref/results/README.md](99_ref/results/README.md)의 JSON 결과 파일과 5단계 API를 사용한다.

실제형 통합 트랙도 독립 트랙을 수정하지 않는다. `99_ref/integration/`은 단계별 실행 결과를 별도 저장해 01→06 점층 구조를 재현한다.

각 일자의 상세 안내는 다음 폴더에 분리했다.

- [01_guardrail_concept_architecture](01_guardrail_concept_architecture/readme.md)
- [02_llama_guard_nemo_guardrails](02_llama_guard_nemo_guardrails/readme.md)
- [03_policy_blocking_output_filtering](03_policy_blocking_output_filtering/readme.md)
- [04_risk_rating_system](04_risk_rating_system/readme.md)
- [05_security_dashboard_alerts](05_security_dashboard_alerts/readme.md)
- [06_operations_report_integrated_lab](06_operations_report_integrated_lab/readme.md)

## 단계별 실습 산출물

### 1단계 · Guardrail 개념과 아키텍처

입력 가드레일과 출력 가드레일의 위치, 모델 호출 전후의 통제 지점을 도식화한다.

### 2단계 · Llama Guard·NeMo Guardrails 적용

Llama Guard의 위험 분류와 NeMo Guardrails의 대화 흐름 제어를 비교한다. 실제 운영 적용 시에는 사용 모델과 정책 범위를 별도로 검증한다.

### 3단계 · 정책 기반 차단 및 출력 검열 구현

허용·거부 규칙을 코드로 정의하고, 출력 단계에서 이메일·전화번호·API 키·비밀 키워드를 탐지해 마스킹한다.

### 4단계 · 위험 등급 체계 설계

위험도, 영향 범위, 노출 가능성, 대응 긴급도를 기준으로 등급을 부여하고 등급별 대응 절차를 정의한다.

### 5단계 · 보안 대시보드 및 알림 구축

차단 건수, 검토 건수, 공격 유형, 위험 등급 분포를 집계하고 Critical 이벤트용 Slack·이메일 연동 payload를 설계한다.

### 6단계 · 운영 리포트 작성 및 통합 실습

탐지 건수, 차단율, 검토 건수, 미대응 이슈를 주간·월간 리포트로 정리하고 전체 처리 흐름을 통합 실행한다.

## SVG 작성 및 검수 규칙

- 캔버스는 `viewBox="0 0 1280 720"`으로 작성한다.
- `<title>`, `<desc>`, `role="img"`, `aria-labelledby`를 포함한다.
- 색상은 CSS 클래스와 다크 모드 규칙으로 관리한다.
- 챕터 표시, 제목, 요약, 본문 도식, 우측 하단 페이지 푸터를 포함한다.
- 외부 폰트·이미지·스크립트·링크를 사용하지 않는다.
- 완성 후 XML 검증과 PNG 렌더링 확인을 수행한다.

```bash
xmllint --noout 99_ref/docs/slides/00-course-flow.svg 01_guardrail_concept_architecture/slides/s01-guardrail-flow.svg
qlmanage -t -s 1280 -o /tmp 99_ref/docs/slides/00-course-flow.svg
```

## SVG 메타프롬프트

슬라이드·도식 SVG를 만들 때 아래 프롬프트와 검수 기준을 사용한다. 슬라이드 원문이 별도로 있으면 원문을 먼저 제공하고, 결과 SVG는 원문에 없는 수치·사실·명령을 추가하지 않는다.

### 프롬프트

```text
너는 AI 가드레일 학습 자료의 SVG 슬라이드를 만드는 작성자다. 아래 원문을 슬라이드 {{N}}장으로 옮겨라.

[입력]
- 챕터: {{7-N 챕터 표시}} / 제목: {{슬라이드 제목}} / 한 줄 요약: {{요약}}
- 원문(변환 대상): {{readme의 해당 절 본문}}
- 기준 파일: 기존 슬라이드의 스타일과 공통 배치를 따른다.

[캔버스와 구성]
- viewBox 0 0 1280 720 (16:9)을 사용한다.
- 위에서 아래로 챕터 chip(7-N, 빨강), 큰 제목, 한 줄 요약, 본문 도식, 우측 하단 푸터(n / 총장수)를 둔다.
- 본문 좌우 여백은 60px 이상으로 하고 푸터와 겹치지 않게 한다.
- <svg>에 role="img", aria-labelledby, <title>, <desc>를 넣는다.
- 글꼴은 -apple-system, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif를 사용한다.
- 외부 폰트·이미지·스크립트·링크는 사용하지 않는다.

[색과 다크 모드]
- 파랑은 기본, 주황은 핵심·전제, 초록은 방어·통제, 빨강은 챕터 표시와 경고에 사용한다.
- 색상은 CSS 클래스에서만 지정하고 인라인 fill·stroke는 사용하지 않는다.
- .bg 배경 사각형을 항상 둔다.
- 모든 색상 클래스에 prefers-color-scheme: dark 대응을 둔다.
- 색만으로 의미를 전달하지 말고 라벨·번호·아이콘 문자를 함께 사용한다.

[내용 규칙]
- 도식은 실제 흐름·구조·관계·판정 기준을 보여 준다.
- 한 슬라이드에는 한 메시지만 담는다.
- 원문에 없는 수치·사실·명령을 만들지 않는다.
- 명령어와 출력은 고정폭 코드 블록으로 표시한다.
- 용어는 "탈옥(Jailbreak)"처럼 일관되게 표기한다.
- 공격 예시는 중립적인 더미 문구와 예약 도메인(.invalid)만 사용한다.
- 실제 자격증명·개인정보·실행 가능한 유해 페이로드는 넣지 않는다.

[글자와 줄바꿈]
- 본문 16px 이상, 제목 40px 안팎, 요약 20px, 표 17px, 각주 14px 이상을 사용한다.
- SVG는 자동 줄바꿈을 하지 않으므로 줄마다 <text>를 따로 둔다.
- 박스 안 텍스트가 넘치면 글자 크기를 줄이지 말고 줄바꿈하거나 슬라이드를 나눈다.
- 한글 폭을 영문 폭으로 계산하지 않는다.

[파일 이름]
- 슬라이드는 단계 폴더의 slides/sNN-이름.svg로 저장한다.
- 이름은 소문자와 하이픈을 사용한다.
- 장수가 바뀌면 모든 슬라이드의 푸터 n / 총장수와 slides/readme.md를 함께 갱신한다.

[출력 전 자체 점검]
1) XML이 유효한가
2) 모든 글자가 박스와 캔버스 안에 있는가
3) 글자와 박스가 서로 겹치지 않는가
4) 푸터 번호가 맞는가
5) 숫자와 명령이 원문과 같은가
6) 다크 모드에서도 읽을 수 있는가
```

### 검수 명령

사람이 렌더링 결과를 눈으로 확인한다. XML 검증만으로 글자 잘림과 겹침을 확인할 수 없다.

```bash
xmllint --noout 99_ref/docs/slides/00-course-flow.svg
find 0[1-6]_*/slides -name '*.svg' -print0 | xargs -0 -n1 xmllint --noout
qlmanage -t -s 1280 -o /tmp 99_ref/docs/slides/00-course-flow.svg
```

검수 항목:

- 글자가 박스·캔버스·푸터를 넘지 않는가
- 카드와 화살표가 겹치지 않는가
- 오른쪽·왼쪽 여백이 60px 이상인가
- 푸터의 `n / 총장수`가 맞는가
- 원문과 숫자·명령이 같은가
- 다크 모드에서 텍스트 대비가 충분한가

## 주의사항

각 단계 폴더의 `src/` 구현은 학습용 휴리스틱이다. 5단계는 SQLite·API Key·웹 대시보드까지 포함하지만, 실제 운영 환경에서는 PostgreSQL 또는 이벤트 스트림, 강한 인증·권한 관리, 감사 로그 보존, 정책 버전 관리, 오탐·미탐 평가를 별도로 검증해야 한다.

## 최상위 파일·디렉터리 역할

| 경로 | 역할 |
| --- | --- |
| `01_...` ~ `06_...` | 서로 독립적인 단계별 학습 코드·문서·SVG |
| `99_ref/integration/` | 단계별 코드를 침범하지 않는 01→06 점층 통합 실습 |
| `99_ref/contracts/` | 단계 간 JSON 결과 형식·버전 기준 · 품질 평가 기준 |
| `99_ref/results/` | 독립 단계 실습의 JSON 결과와 전달 규칙 |
| `99_ref/tests/` | 공통 회귀·API·계약 테스트 |
| `99_ref/scripts/` | 빠른 파일 기반 파이프라인 보조 실행 |
| `99_ref/logs/` | 작업·검증·재구성 이력 |
| `readme.md` | 전체 학습 목표·구조·실행·결과 확인·SVG 규칙 |
| `requirements.txt` | 루트 공통 실행 의존성 |
| `.env.example` | API 키·DB·Ollama 환경 변수 예시 |
| `99_ref/docs/slides/00-course-flow.svg` | 1~6단계 전체 학습 흐름도 |
| `99_ref/docs/slides/01-practice-guide.svg` | 단계별 실습 실행 순서와 통합 실습 안내 |
| `99_ref/docs/slides/02-technology-stack.svg` | 전체 기술 스택과 실행 도구 요약 |
| `99_ref/docs/slides/03-integration-flow.svg` | 독립 단계 실습과 점층 통합 트랙의 관계 |
| `99_ref/docs/slides/04-result-check.svg` | JSON·API·웹 화면·계약 결과 확인 방법 |


