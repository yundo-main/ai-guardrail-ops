# 5단계 · 보안 대시보드 및 알림 구축

## 이론적 배경

가드레일이 요청을 차단해도 운영자가 방어 상태와 반복되는 공격 양상을 볼 수 없다면 시스템은 개선되지 않는다. 보안 관제는 개별 이벤트를 기록하는 데서 끝나지 않고, 이벤트를 지표·화면·알림으로 변환해 운영자의 판단을 지원해야 한다.

대시보드는 추세와 분포를 보여 주고, 알림은 즉시 조치가 필요한 사건을 전달한다. 두 채널의 목적을 구분해야 정보 과부하를 줄이면서 Critical 사건의 대응 속도를 높일 수 있다.

## 학습 목표

보안 이벤트를 운영 지표로 집계하고 Critical 이벤트를 알림으로 연결한다.

## 핵심 내용

- 전체 이벤트·차단·검토 건수
- 공격 유형과 위험 등급 분포
- 차단율과 미대응 이슈
- Critical 이벤트의 Slack·이메일 연동 payload

## 이론 보강

대시보드는 단순한 이벤트 개수보다 의사결정에 필요한 추세를 보여 줘야 한다. 전체 요청 수 대비 차단율, 위험 등급별 변화, 카테고리별 집중도, 미대응 건수를 함께 봐야 정책 효과를 해석할 수 있다.

알림은 모든 이벤트를 전달하는 채널이 아니다. Critical 조건, 중복 알림 억제, 담당자 라우팅, 재시도, 확인(acknowledgement) 상태를 설계해야 알림 피로를 줄이고 실제 대응률을 높일 수 있다.

대시보드와 알림에는 비밀정보 원문을 넣지 않는다. 이벤트 ID와 마스킹된 증거를 사용하고, 상세 원문은 별도 권한 영역에서만 조회하도록 분리한다.

## 실습

1. `dashboard_metrics()`로 이벤트를 집계한다.
2. 위험 등급별·카테고리별 분포를 확인한다.
3. `critical_alert()`가 Critical 이벤트에만 payload를 생성하는지 검증한다.

### API 중심 구현

`src/api.py`는 대시보드용 집계 결과를 HTTP API로 제공한다. 이벤트는 기본 SQLite 저장소에 기록하며, 실제 운영 환경에서는 PostgreSQL이나 이벤트 스트림으로 교체할 수 있다.

| 메서드 | 경로 | 역할 |
| --- | --- | --- |
| `GET` | `/health` | 서비스 상태 확인 |
| `POST` | `/guardrail/chat` | 실제 NeMo Guardrails·Llama Guard 호출 및 결과 저장 |
| `POST` | `/events` | 보안 이벤트 등록 |
| `GET` | `/events` | 이벤트 목록 조회 |
| `GET` | `/metrics` | 대시보드 지표 조회 |
| `GET` | `/alerts/critical` | Critical 알림 목록 조회 |
| `DELETE` | `/events` | 실습용 이벤트 초기화 |
| `GET` | `/dashboard` | 웹 기반 지표 화면 |
| `POST` | `/events/{event_id}/acknowledge` | 운영자 확인 상태 기록 |

실행:

```bash
python3 -m pip install -r 05_security_dashboard_alerts/requirements.txt
uvicorn api:app --app-dir 05_security_dashboard_alerts/src --reload --port 8000

# 단위 테스트 (선택)
python3 -m unittest discover -s 05_security_dashboard_alerts/tests -v

# 결과 리포트 생성 — DB 이벤트를 step05-metrics.json + .html로 저장
python3 05_security_dashboard_alerts/src/report.py
```

기본 API 키는 `dev-only-key`이며 요청 헤더에 `X-API-Key`를 넣는다. 배포 전에는 `GUARDRAIL_API_KEY`를 변경한다. API 문서는 서버 실행 후 `http://127.0.0.1:8000/docs`, 웹 화면은 `http://127.0.0.1:8000/dashboard`에서 확인한다. 이벤트는 기본적으로 `results/security_events.db`에 저장된다.

Critical 이벤트가 등록되면 `critical_alert()` payload가 생성되고, `src/discord.py`의 `WEBHOOK_URL`이 설정된 경우 Discord 웹훅으로 알림을 발송한다. 비어 있으면 발송은 건너뛰고 API는 그대로 동작한다.

### Discord 웹훅 알림 연결

1. Discord에서 알림을 받을 채널을 연다.
2. 채널 설정 → **연동(Integrations)** → **웹후크(Webhooks)** → **새 웹후크**를 만든다.
3. 웹후크 이름(예: `AI Guardrail 알림`)을 지정하고 **웹후크 URL을 복사**한다.
4. `src/discord.py` 상단의 `WEBHOOK_URL`에 복사한 URL을 직접 붙여넣는다. 비워 두면 발송은 건너뛴다.

```python
# src/discord.py
WEBHOOK_URL = "https://discord.com/api/webhooks/1234.../xxxx..."
```

```bash
uvicorn api:app --app-dir 05_security_dashboard_alerts/src --reload --port 8000
```

5. Critical 이벤트를 등록하면 채널에 embed 알림이 도착한다.

```bash
curl -X POST http://127.0.0.1:8000/events \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-only-key' \
  -d '{"event_id":"step04-security-event","decision":"block","risk":"Critical","category":"prompt_injection","detail":"ignore previous instructions","trace_id":"demo-1"}'
```

동작 특성:

- 발송 임계값은 `GUARDRAIL_ALERT_MIN_RISK` 환경변수로 조정한다 — `Low`/`Medium`/`High`/`Critical` (기본 `Critical`, 잘못된 값은 `Critical`로 복귀). 예: `export GUARDRAIL_ALERT_MIN_RISK=High`이면 High 이상 이벤트도 발송된다.
- 임계값 이상의 이벤트는 `risk_alert()`이 payload를 만들고 `notify_async()`가 백그라운드 스레드로 전송한다 — 웹훅 지연이 API 응답을 블록하지 않는다.
- `WEBHOOK_URL`이 비어 있으면 발송은 건너뛰고 API는 정상 동작한다.
- 웹훅 URL은 비밀값이지만 실습 편의상 `discord.py`에 직접 넣는 방식을 택했다 — 실제 URL을 커밋하기 전에 GitHub 저장소 공개 여부를 확인한다.

### 실제 Guardrail 서비스 호출

`POST /guardrail/chat`은 더미 응답을 사용하지 않는다. 요청은 3단계 입력 정책을 먼저 통과한 뒤 NeMo Guardrails와 Llama Guard를 호출하고, 출력 마스킹과 최종 이벤트 저장을 수행한다.

```bash
curl -X POST http://127.0.0.1:8000/guardrail/chat \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-only-key' \
  -d '{"message":"회사 비밀번호 재설정 절차를 요약해줘","conversation_id":"demo-1"}'
```

선택 의존성 설치, Meta 모델 권한 승인, Ollama 실행이 준비되지 않으면 API는 `503`을 반환한다. 이는 실제 호출 실패를 성공으로 위장하지 않기 위한 동작이다. 성공 시 `trace_id`로 `/events`, `/metrics`, `/alerts/critical`에서 결과를 확인한다.

대시보드 payload와 주간·월간 리포트 envelope 조합 예제는 `src/report.py`에서 제공한다. Critical 알림을 확인한 뒤에는 다음 API로 상태를 남긴다.

```bash
curl -X POST http://127.0.0.1:8000/events/step03-guardrail-result/acknowledge \
  -H 'X-API-Key: dev-only-key'
```

## 산출물

- 대시보드 지표 정의서
- 집계 결과 JSON
- Critical 알림 payload
- FastAPI OpenAPI 문서와 API 테스트 결과
- `results/step05-metrics.json` 6단계 리포트 입력 파일

## 단계 간 연결

[← 4단계](../04_risk_rating_system/readme.md) · [6단계 →](../06_operations_report_integrated_lab/readme.md) · [전체 과정](../readme.md)

4단계 `step04-security-event.json`을 `POST /events`로 등록하고, `GET /metrics` 결과를 `results/step05-metrics.json`으로 저장한다. 6단계는 이 지표를 운영 리포트의 입력으로 사용한다.

## 완료 기준

운영자가 차단량, 공격 유형, 위험 분포, 긴급 이벤트를 한눈에 확인할 수 있는 지표 구성을 설명할 수 있다.

## 파일·디렉터리 역할

| 경로 | 역할 |
| --- | --- |
| `src/api.py` | 인증된 이벤트 등록·조회·지표·알림·확인 API와 `/dashboard` 제공 |
| `src/guardrail_service.py` | 2단계 실제 provider 호출, 3단계 정책, 출력 마스킹을 연결하는 서비스 계층 |
| `src/store.py` | SQLite 초기화·저장·조회·초기화·acknowledgement 처리 |
| `src/event_model.py` | API·저장소·알림이 공유하는 이벤트 데이터 모델 |
| `src/policy.py` | API 입력의 `Decision`·`RiskLevel` enum |
| `src/monitoring.py` | 이벤트 생성·지표 집계·임계값 기반 알림 payload 생성 |
| `src/discord.py` | `WEBHOOK_URL` 상수로 임계값 이상 알림을 Discord 웹훅에 발송 (비어 있으면 no-op) |
| `src/report.py` | 대시보드 payload·주간/월간 envelope + `step05-metrics.json`/`.html` 결과 리포트 생성 |
| `src/step03_report.py` | 3단계 결과 HTML 렌더러의 로컬 복사본 — `report.py`와 이름 충돌 방지용 |
| `src/step03_policy.py` | 3단계 정책 규칙 로더의 로컬 복사본 — `guardrail_service` 전용 (`policy` 모듈명 충돌 회피) |
| `src/step03_guardrail.py` | 3단계 `check_input`·`redact_output`의 로컬 복사본 — 03 원본과 동기화 유지 |
| `src/llama_guard.py` | 2단계 Llama Guard 클라이언트 — 프롬프트·응답 안전성 분류 |
| `src/nemo_guardrails_client.py` | 2단계 NeMo Guardrails 클라이언트 — 대화 레일 응답 생성 |
| `src/dashboard.html` | API 지표와 Critical 알림을 보여주는 웹 화면 |
| `requirements.txt` | 5단계 FastAPI·Uvicorn 실행 의존성 |
| `slides/s00-tech-spec.svg` | FastAPI·SQLite·API Key 기술 사양 |
| `slides/s01-dashboard-alerts.svg` | 대시보드·알림 전체 구조 |
| `slides/s02-dashboard-theory.svg` | 운영 지표와 Critical 알림 이론 |
| `slides/s03-dashboard-source.svg` | API·저장·집계 소스 설명 |
| `slides/s04-practice-order.svg` | 실습 순서 — 서버·이벤트·리포트·Discord 명령 |
| `slides/s05-discord-setup.svg` | Discord 웹훅 알림 설정 — URL 발급·discord.py 입력·발송 확인 |
| `slides/s06-server-event-test.svg` | 서버 실행과 이벤트 테스트 — uvicorn·이벤트 등록·대시보드·Discord 확인 |
| `slides/s07-flow.svg` | 실행 흐름 Flow 도식 — api.py 호출 순서·모듈 역할·분기 규칙 |
| `slides/s08-dashboard-checklist.svg` | 관제 실습 체크리스트 |
| `slides/s09-summary.svg` | 5단계 핵심 요약과 질문 |
| `slides/readme.md` | 슬라이드 순서·제목·산출물 목록 |
