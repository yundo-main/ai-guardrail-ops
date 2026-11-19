# 개발 문서 — AI Guardrail Ops Framework

내부 구조·설계·확장 방법을 다룬다. 사용 방법은 [../readme.md](../readme.md)를 참고.

## 모듈 구성

3계층 구조 — `guardrail/`(판정)과 `guardrail-ops/`(관측·서빙)는 각각 독립 `src/`를 가지고, `main.py`·`serve/http.py`·테스트가 두 경로를 `sys.path`에 함께 등록해 사용한다(모듈명은 `core.*`, `guard.*` 등 동일).

```text
guardrail/src/               # 가드레일 엔진 (판정·분류·마스킹)
├── core/
│   ├── types.py       # Decision·RiskLevel·PolicyMatch·Span·SecurityEvent·RunRecord (schema v1.1)
│   └── pipeline.py    # 파이프라인 오케스트레이션 + 단계별 Span 계측
├── guard/
│   ├── policy.py      # 정책 규칙 로딩·입력 탐지 (fail-closed)
│   └── output.py      # 출력 마스킹 (email/phone/api_key/secret_keyword)
├── risk/
│   ├── classify.py    # RunRecord → SecurityEvent 변환 (원문 미포함)
│   └── score.py       # classify_risk(impact, exploitability, exposure) 점수 분류
└── providers/
    ├── model.py       # LLM_PROVIDER 선택: dummy / Ollama / DeepSeek
    ├── deepseek.py    # DeepSeek API (OpenAI 호환, lazy)
    ├── classifier.py  # Llama Guard 3 (Transformers, lazy)
    └── dialogue.py    # 토픽 레일: KeywordTopicRail / NemoGuardrailsRail(lazy)

guardrail/config/
├── policy-rules.json       # 정책 규칙 17개 (GUI/API 편집)
└── output-patterns.json    # 마스킹 패턴 4종 (GUI/API 편집)

guardrail-ops/src/          # 운영 계층 (관측·저장·서빙·CLI)
├── main.py            # CLI 진입점 (demo/run/metrics/events/report/ack/clear/serve)
├── observe/
│   ├── store.py       # SQLite 이벤트 저장 + audit 테이블 + alerts.jsonl
│   ├── runtime.py     # .env 설정 영속화 (load/save, 비밀키 포함)
│   ├── metrics.py     # 집계 지표·critical_alert·stage_latency
│   └── report.py      # weekly(7일)/monthly(30일) 기간 필터 리포트
└── serve/
    ├── http.py        # ThreadingHTTPServer, rate limit·body cap·openapi
    └── page.py        # 단일 HTML GUI (vanilla JS + canvas, 8개 탭)
```

## 파이프라인 단계

```text
input_guardrail → dialogue_rail → model → classifier → output_guardrail
```

- `input_guardrail`: 정책 규칙 매칭. `block` 규칙이 하나라도 있으면 모델 호출 없이 BLOCK. `review` 규칙만 있으면 진행하되 최종 결과가 ALLOW가 될 수 없다.
- `dialogue_rail`: `--rail` 지정 시에만 동작. 프롬프트가 허용 주제를 벗어나면 모델 호출 전에 REVIEW 반환 (LLM 비용 절약).
- `model`: Ollama 호출 실패 시 dummy로 폴백.
- `classifier`: `--classifier` 지정 시 Llama Guard. 호출 실패·파싱 불가 → unsafe(fail closed) → BLOCK.
- `output_guardrail`: 민감 필드 마스킹. 검출 시 REVIEW.

각 단계는 `Span(stage, outcome, ms)`으로 기록되고 `RunRecord.spans` → `SecurityEvent.spans_json`에 영속화된다.

## 정책 규칙 스키마 (`guardrail/config/policy-rules.json`)

```json
{
  "rule_id": "INJ-001",
  "pattern": "정규식",
  "reason": "차단 사유(=category)",
  "risk": "Low|Medium|High|Critical",
  "decision": "block|review",
  "flags": ["IGNORECASE", "DOTALL", "NORMALIZE"]
}
```

- `risk` 대신 `impact`·`exploitability`·`exposure`(각 0~3)를 주면 `classify_risk` 점수로 등급 결정 (≥8 Critical, ≥6 High, ≥3 Medium).
- `NORMALIZE`: 매칭 전 공백·줄바꿈을 단일 공백으로 정규화 — `ignore   all   previous` 같은 우회 차단.
- 잘못된 정책 파일은 예외로 중단한다(규칙 없이 실행되는 것을 방지).

## 이벤트·저장 스키마 (v1.1)

`SecurityEvent` 필드: `event_id, trace_id, decision, risk, category, detail, timestamp, schema_version, source_stage, policy_version, model_name, status, acknowledged_at, spans_json`.

- 프롬프트 원문은 저장하지 않는다(프라이버시 원칙). `detail`에는 매칭된 rule_id 목록이 들어간다.
- `status`: `open` → `acknowledge()` 시 `acknowledged` + `acknowledged_at`.
- `audit` 테이블: 상태·등급 변경 시 `actor, reason, old_value, new_value, timestamp`를 별도 기록(4단계 원칙 — 원본 덮어쓰기 금지).
- Critical 이벤트는 `guardrail-ops/results/alerts.jsonl`에도 JSONL로 추가된다.

## HTTP 계층 (`guardrail-ops/src/serve/http.py`)

- `ThreadingHTTPServer` + `threading.Lock`으로 sqlite 커넥션 직렬화(`check_same_thread=False`).
- 제한: 요청 본문 1MB(413), `POST /v1/check` IP당 60초 30회(429).
- `POST /clear`는 `{"confirm": true}` 필수.
- `GET /openapi.json`에 엔드포인트 명세.

## 테스트

`tests/test_framework.py` — 15개. 결정론을 위해 `Pipeline(model=dummy_model)`을 명시한다(기본은 Ollama라 네트워크 의존). 커버 범위: allow/block/review 분기, fail-closed, NORMALIZE 우회, 점수 분류, 기간 필터, spans/audit 영속화, dialogue_rail 단계.

```bash
python -m unittest discover -s 10_ai_guardrail_ops_framework/tests -v
```

## 설계 원칙

- 표준 라이브러리만 사용(무거운 의존성은 선택 사항: transformers/torch, nemoguardrails).
- 실패는 안전한 쪽으로: 분류기·레일 오류 → 차단/검토, 정책 파일 오류 → 중단.
- 이벤트에는 원문을 남기지 않는다.
- 단계 폴더(01~06)를 import하지 않는 독립 프레임워크.

## 개발 로그

### 2026-11 · 프레임워크 구축 ~ 운영 GUI 완성

**기반 구축**
- 01~06단계 기능을 독립 프레임워크로 통합: 파이프라인·정책·마스킹·이벤트 저장·지표·리포트
- SQLite 이벤트 저장소(`events.db`, schema v1.1) + Critical 알림(`alerts.jsonl`)
- `main.py` CLI: demo/run/metrics/events/report/ack/clear

**정책 강화**
- 정책 규칙 4개 → 13개 확장 (INJ/EXF/TOOL/ABUSE 카테고리)
- `NORMALIZE` 플래그 — 공백·줄바꿈 삽입 우회 차단
- 규칙별 `decision` 존중 — review 규칙은 모델까지 진행 후 최종 REVIEW 보장
- `risk` 대신 `impact`·`exploitability`·`exposure` 점수 지정 가능 (`classify_risk`)

**HTTP 서버 + GUI**
- 표준 라이브러리 `http.server` 기반 `serve` 명령 추가 → `src/serve/`로 분리
- 엔드포인트: `/v1/check` `/metrics` `/events` `/report` `/alerts` `/audit` `/policy` `/llm` `/settings` `/openapi.json`
- 보안 제한: 본문 1MB, `/v1/check` rate limit(30회/60초), `/clear` confirm 필수
- GUI 8개 탭: 검사·챗봇·대시보드·이벤트·LLM·정책·리포트·도움말
  - 차트(canvas): 일별 추이·카테고리·리스크·decision 분포·단계별 지연
  - 정책/마스킹 JSON 편집기 — 임시 파일 검증 후에만 저장, 즉시 핫 리로드
  - LLM 설정 — 프로바이더/모델/Base URL/키 런타임 변경
  - 도움말 — 용어 사전(ㄱㄴㄷ 인덱스)·동작 흐름도·단계별 모듈 매핑
- 라이트 테마 + 다크모드 토글, 토스트, 로딩 상태, 자동 새로고침, `Cache-Control: no-store`

**02·04단계 보강**
- `risk/score.py` — `classify_risk()` 3축 점수 분류 이식
- `audit` 테이블 — ack/변경 시 actor·reason·변경 전후 값 별도 기록
- `providers/dialogue.py` — 토픽 레일(Keyword 기본, NeMo lazy), `--rail` 옵션

**모델 프로바이더**
- 기본값 dummy → Ollama(`qwen2.5:3b`)로 변경, `USE_LLM=0`으로 더미 전환
- `LLM_PROVIDER` 환경변수: `ollama` / `deepseek` / `dummy`
- `providers/deepseek.py` — DeepSeek API(OpenAI 호환) 어댑터

**구조 재편**
- `src/` 단일 트리 → 3계층 분리: `guardrail/`(엔진) + `guardrail-ops/`(관측·서빙) + `chatbot/`(학습용 챗봇, 독립)
- 파일명 유지, `sys.path` 부트스트랩으로 두 `src/` 동시 등록
- 설정 경로도 계층별 이동: `guardrail/config/*`, `guardrail-ops/results/*`
- `observe/runtime.py` — `/settings` 변경을 `guardrail-ops/.env`에 영속화(dotenv 형식, 주석·다른 키 보존), 시작 시 자동 복원
- 정책 규칙 13개 → 17개 — 한글 변형 규칙 추가(INJ-004·EXF-004·TOOL-004·ABUSE-005). 한국어는 ㄹ 불규칙 활용(만드는≠만들) 때문에 어간 변형을 alternation으로 병기해야 함
- 멀티턴 대화 — `/v1/check`에 `history` 필드 추가(최대 20턴). `Pipeline.run(prompt, history)`는 모델 단계에만 맥락을 전달하고 정책·레일·분류기는 현재 메시지만 검사. `providers/model.py`의 `chat_messages()`/`sanitize_history()`로 OpenAI 스타일 messages 배열 생성 — Ollama·DeepSeek이 네이티브 멀티턴으로 호출됨. history 미지원 모델에는 `[이전 대화]` 텍스트 폴백. `/chat` 페이지는 최근 12턴을 자동 전송

### 2026-11 (후반) · 페이지 분리 + 랜딩 페이지 + 문서화

**페이지 3분리**
- `/` 랜딩(프로젝트 소개) · `/ops` 운영 GUI · `/chat` 챗봇 — `serve/page.py`에 `LANDING_PAGE`/`PAGE`/`CHAT_PAGE` 3개 HTML 상수
- 운영·챗봇 페이지 상호 링크, `/chatbot`은 `/chat` 별칭

**랜딩 페이지**
- 히어로 배너(그라데이션·CTA·5단계 칩) + sticky 내비게이션(앵커 스크롤)
- 토글 카드(`.dgi`) 컴포넌트 — `＋ 더 보기`/`－ 접기`, 섹션별 개별 접힘
  - 프로젝트 구조: `<details>` 중첩 디렉터리 트리 — 디렉터리 토글 + 파일 리프 표시
  - 도움말 용어: 18개 용어, ㄱㄴㄷ 초성 색인·앵커, allow/review/block 색상 태그
  - LLM 설정: `/llm` 상태 테이블 + 편집 폼 → `POST /settings` 저장·`.env` 영속화
  - 설정 파일·환경변수 표, 소스 흐름도(pre 코드 경로)
- SVG 다이어그램 `docs/diagrams/flow-01~03` — 서비스 파이프라인·판정 파이프라인·계층 구조. `/diagrams/*.svg` 화이트리스트 라우트로 서빙

**버그 수정**
- `page.py` 임베디드 JS의 `\n`이 Python에서 실제 줄바꿈으로 변환돼 JS 파싱 실패 → `\\n` 이스케이프로 수정, `node --check` 검증 절차 확립

**LLM 설정 위젯 공통화 (중복 UI 제거)**
- `/ops` LLM 탭·`/chat` 설정 카드·`/` 설정 탭에 각각 복제돼 있던 LLM 폼 HTML/JS를 `page.py` 하단의 공통 상수로 추출:
  - `LLM_WIDGET_CSS` — `.lw*` 스타일 (`</style>` 앞 `__LLMW_CSS__` 플레이스홀더)
  - `LLM_WIDGET_STATUS` — `/llm` 상태 테이블 영역 (`__LLMW_STATUS__`)
  - `LLM_WIDGET_FORM` — 프로바이더/모델/Base URL/API Key/사용 여부 폼 (`__LLMW_FORM__`)
  - `LLM_WIDGET_JS` — `lwLoad()`/`lwSave()`/`lwToggle()` 공통 로직 (`<script>` 앞 `__LLMW_JS__`, 각 페이지 메인 스크립트보다 먼저 로드)
- 모듈 하단에서 3개 페이지 상수의 플레이스홀더를 일괄 치환 — 이후 LLM 설정 변경은 위젯 한 곳만 수정하면 전 페이지 반영
- 페이지별 역할 유지: `/ops`는 상태 카드+연결 테스트 버튼, `/chat`은 헤더 상태 pill + 폼만, `/`는 탭 진입 시 자동 로드
- 구 페이지별 id(`llmProvider`/`cProvider`/`lProvider` 등)와 함수(`loadCfg`/`saveCfg`/`toggleLKey` 등) 전부 제거, `/ops`의 `loadLlm`은 `lwLoad` 별칭으로 호환 유지

### 운영 메모

- `/settings` 변경은 `guardrail-ops/.env`에 영속화 — 서버·CLI 시작 시 `load_runtime()`이 환경변수로 복원. 화이트리스트 키만 저장되며 `DEEPSEEK_API_KEY` 같은 비밀값도 이 파일에 둔다(gitignore 권장).
- NeMo Guardrails·Llama Guard는 lazy import — 미설치 시 명확한 에러, 기본 경로에는 영향 없음
- 인증은 의도적으로 미구현 (로컬 `127.0.0.1` 바인딩 전제)
