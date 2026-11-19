# ch01/dxx-app 실행 매뉴얼

이 문서의 모든 명령과 출력은 2026-09-05 실제 실행으로 검증되었다.
설계 설명은 [readme.md](readme.md) 를 참고한다.

---

## 0. 사전 준비

### 0-1. 가상환경 활성화

리포지터리 루트에 가상환경(`venv`)이 준비되어 있다. 모든 작업은 **활성화한 상태**에서 진행한다.

```bash
cd "/Users/jarrod/Library/CloudStorage/GoogleDrive-meta4rism@gmail.com/내 드라이브/gdrive-project/code-test-check"
source venv/bin/activate
cd ch01/dxx-app
```

활성화되면 프롬프트 앞에 `(venv)` 가 붙는다.

```
(venv) code-test-check/ch01/dxx-app $
```

활성화 여부 확인:

```bash
which python
# .../code-test-check/venv/bin/python     ← 리포지터리 루트의 venv 여야 한다

python -V
# Python 3.14.6
```

> `which python` 이 `/opt/homebrew/bin/python` 이거나 `python not found` 로 나오면 활성화되지 않은 것이다.
> 시스템 파이썬에는 이 예제의 패키지가 없다.

작업을 마치면 해제한다.

```bash
deactivate
```

### 0-2. 가상환경이 없거나 패키지가 빠졌을 때

```bash
cd "/Users/jarrod/Library/CloudStorage/GoogleDrive-meta4rism@gmail.com/내 드라이브/gdrive-project/code-test-check"
python -m venv venv                                  # 최초 1회만
source venv/bin/activate
pip install -r ch01/dxx-app/requirements.txt
```

설치 확인:

```bash
pip list | grep -iE "generativeai|fastapi|uvicorn|pydantic"
```

```
fastapi                      0.141.1
google-generativeai          0.8.6
pydantic                     2.13.4
uvicorn                      0.52.3
```

[requirements.txt](requirements.txt) 는 직접 임포트하는 4개 패키지를 정확한 버전으로 고정한다.
전이 의존성(google-api-core, starlette 등)은 고정하지 않으므로 완전한 재현은 보장되지 않는다.
현재 환경 전체를 고정하려면:

```bash
pip freeze > requirements.txt
```

`requests`, `httpx` 는 필요하지 않다. 4-2단계 웹 검색은 Gemini SDK 를 그대로 쓰거나 표준 라이브러리만 사용한다.

### 0-3. API 키

코드는 `.env` 를 직접 읽지 않는다. 환경 변수만 사용하므로, `.env` 를 셸에 올려서 쓴다.

**최초 1회** — 견본을 복사해 실제 값을 채운다.

```bash
cp .env.sample .env
# 편집기로 .env 를 열어 GEMINI_API_KEY 를 채운다
```

이후로는 `source` 가 필요 없다. [0-env.py](0-env.py) 가 각 단계 시작 시 `.env` 를 읽어
환경 변수로 올린다. `python-dotenv` 같은 추가 패키지는 쓰지 않는다.

확인:

```bash
python 0-env.py
#   [1] 파일 위치: .../ch01/dxx-app/.env
#       존재 여부: 있음
#   [2] 새로 올린 키 5건
#       - GEMINI_API_KEY
#       - GEMINI_MODEL
#       ...
```

**셸에 이미 있는 값이 우선한다.** `.env` 는 비어 있는 자리만 채운다.
그래서 일회성 지정이 그대로 통한다.

```bash
RAG_MIN_SCORE=0.5 python 5-agent.py   # 이번 실행만 임계값 0.5
GEMINI_MODEL=gemini-3.6-flash python 3-llm.py
```

`.env` 없이 셸에서 직접 지정하는 방식도 그대로 유효하다.

```bash
export GEMINI_API_KEY='...'
```

| 환경 변수 | 필수 | 기본값 |
|---|---|---|
| `GEMINI_API_KEY` | 필수 | 없음 (미설정 시 각 단계가 종료) |
| `GEMINI_MODEL` | 선택 | `gemini-2.5-flash` |
| `GEMINI_EMBED_MODEL` | 선택 | `models/gemini-embedding-001` |

사용 가능한 모델 확인:

```bash
python -c "
import os, google.generativeai as g
g.configure(api_key=os.environ['GEMINI_API_KEY'])
print([m.name for m in g.list_models() if 'generateContent' in m.supported_generation_methods])
"
```

---

## 1. 단계별 실행

아래 명령은 모두 `(venv)` 활성화 + `ch01/dxx-app` 디렉터리 기준이다.

### 0단계 — 설정 로드 (API 호출 없음)

```bash
python 0-env.py
```

```
[1] 파일 위치: .../ch01/dxx-app/.env
    존재 여부: 있음
[2] 새로 올린 키 4건
    - GEMINI_API_KEY
    - GEMINI_MODEL
    - GEMINI_EMBED_MODEL
    - RAG_MIN_SCORE
```

확인 포인트: `.env` 가 실제로 읽히는지. **값은 출력하지 않고 키 이름만 보여준다.**
`새로 올린 키 0건` 이면 이미 셸에 같은 이름이 있어 건너뛴 것이다(셸이 우선).

이 파일은 다른 단계가 시작할 때 자동으로 실행된다. 단독 실행은 확인용이다.

### 1단계 — 문서 로드 (API 호출 없음)

```bash
python 1-documents.py
```

```
[3] Document 객체로 변환된 결과
  - Document(doc_id='weather', text='서울의 여름 날씨는 대체로 덥고 습하다. 평균 기온은 25도 안팎이다.')
  - Document(doc_id='product', text='무선 마우스는 배터리로 동작하며 가격대는 3만~8만원이다.')
  - Document(doc_id='policy', text='고객 지원 시간은 평일 09:00–18:00 이며 주말·공휴일은 휴무다.')
  ... (총 12건)
  - Document(doc_id='privacy', text='회원 정보는 탈퇴 후 30일간 보관한 뒤 파기한다. ...')
```

확인 포인트: `1-documents.json` 의 JSON 배열이 `Document` 객체로 변환되는지. 마지막 줄까지 12건이 모두 나와야 한다.

코퍼스는 고객 지원 FAQ 도메인 12건이다. 근접 문서쌍(`refund`/`exchange`, `policy`/`support_channel`)이
포함되어 있어 검색이 의미가 비슷한 문서 중 어느 쪽을 고르는지 관찰할 수 있다.

### 2단계 — 임베딩 (API 호출 2회)

```bash
python 2-embeddings.py
```

```
[3] 문서 임베딩
    embedding dim=3072 preview=[-0.0121, -0.0080, 0.0119, -0.0559, ...]
[4] 질문 임베딩
  query embedding dim=3072 preview=[0.0011, -0.0217, 0.0155, -0.0545, ...]
```

확인 포인트: 문서와 질문의 `dim` 이 **동일**해야 한다. 다르면 코사인 유사도 계산이 성립하지 않는다.

### 3단계 — LLM 단독 호출 (API 호출 1회)

```bash
python 3-llm.py
```

```
질문: 파이썬에 대해 설명해 주세요.
답변:
파이썬은 문법이 간결하고 읽기 쉬워 배우기 쉬운 고수준 프로그래밍 언어입니다.
...
```

### 4-1단계 — RAG (API 호출 다수)

```bash
python 4-1-rag.py
```

예제 질문 3개를 순서대로 실행한다. 실측 출력이다.

```
======== 질문 1: 주말에 고객 지원 받을 수 있어? ========
  hit 'policy' score=0.8045
  hit 'support_channel' score=0.7035
--- 답변 ---
주말에는 고객 지원이 휴무입니다.

======== 질문 3: 비행기 표 환불 규정 알려줘 ========
  hit 'refund' score=0.6979
  hit 'exchange' score=0.6543
--- 답변 ---
문서에 없습니다.
```

세 번째 질문이 이 단계의 요점이다. `refund` 문서가 0.6979 로 검색되지만 항공권 환불은
코퍼스에 없는 주제이므로, 프롬프트 지시에 따라 지어내지 않고 `문서에 없습니다` 로 답한다.

### 4-2단계 — 웹 검색 (API 호출 1회)

```bash
python 4-2-websearch.py
```

실측 출력이다.

```
============================================================
4-2 웹 검색 데모
질문 → [모델 내부 검색 + 답변 생성] → 답변 + 근거 출처
============================================================
[입력] 오늘 서울 날씨 어때?

[W1] 그라운딩 요청 model=gemini-2.5-flash
[W2] 모델이 실행한 검색어 2건
  - '오늘 서울 날씨'
  - '서울 날씨 2026년 9월 6일'
[W3] 근거 출처 3건
  + https://www.google.com/search?q=weather+in+Seoul,+KR  Weather information for Seoul, KR
  + https://vertexaisearch.cloud.google.com/grounding-api-redirect/...  accuweather.com
  + https://vertexaisearch.cloud.google.com/grounding-api-redirect/...  kma.go.kr
[W4] 답변 수신 (검색과 생성이 한 번의 호출에서 이뤄짐)
오늘 서울은 맑고 ... 기온은 26°C ...
```

확인 포인트는 `[W2]` 다. **모델이 질문을 그대로 검색하지 않는다.**
질문을 여러 검색어로 바꿔 실행한 뒤 그 결과를 종합한다.

`[W3] 근거 출처 0건` 이 나오면 모델이 검색하지 않고 내부 지식으로 답한 것이다.
질문에 `오늘`·`지금`·`최근` 같은 시점 표지를 넣으면 검색할 가능성이 높아진다.

**키가 유효한지만 빠르게 확인하려면:**

```bash
curl -s -o /dev/null -w "%{http_code}\n" -H "x-goog-api-key: $GEMINI_API_KEY" \
  https://generativelanguage.googleapis.com/v1beta/models
# 200 이면 유효
```

**이 단계만 SDK 대신 REST 를 직접 호출한다.** 이유는 아래와 같다.

| 시도 | 결과 |
|---|---|
| SDK 에 `{"google_search": {}}` dict 전달 | `Unknown field for FunctionDeclaration` — 클라이언트가 거부 |
| SDK 에 `glm.Tool(google_search=...)` 프로토 전달 | 요청은 통과하나 도구가 빠진 채 전송. 검색어 0건 |
| SDK 에 `google_search_retrieval` 전달 | `400 ... Please use google_search tool instead` |
| **REST 직접 호출** | **정상 동작** |

REST 는 `urllib` 만 쓰므로 새 의존성이 없다. 근본 해결은 `google-genai` 로의 이전이다.

---

### 5단계 — 에이전트 (API 호출 다수)

#### 에이전트 라우팅 확인

라우팅 단계에서는 웹 검색이 선택되지 않는다. 모든 질문이 먼저 `tool_rag` 로 간다.

```bash
printf '오늘 서울 날씨 어때?\n/quit\n' | python 7-chatbot.py
#     - 선택 도구: tool_rag
#   [1단계] 검색 최고 점수 0.7222 >= 기준 0.70 → 문서로 답변 시도
#   [2단계] 문서로 답하지 못함 → 웹 검색으로 전환

printf '서울 여름 날씨 어때?\n/quit\n' | python 7-chatbot.py
#     - 선택 도구: tool_rag
#   [1단계] 검색 최고 점수 0.7971 >= 기준 0.70 → 문서로 답변 시도
#   [2단계] 문서로 답변 완료
```

---


```bash
python 5-agent.py
```

예제 질문 6개에 대한 도구 선택 결과:

| 질문 | 선택 도구 | API 호출 |
|---|---|---|
| 문서 목록 보여줘 | `tool_list_documents` | 없음 |
| 문서 구성 요약해줘 | `tool_document_summary` | 없음 |
| 주말에 고객 지원 받을 수 있어? | `tool_rag` → 1단계·2단계 통과 | 임베딩 13 + 생성 1 |
| 서울 여름 날씨는 어때? | `tool_rag` → 1단계·2단계 통과 | 임베딩 13 + 생성 1 |
| 오늘 서울 날씨 어때? | `tool_rag` → **2단계에서 웹 전환** | 임베딩 13 + 생성 2 |
| 파이썬은 어떤 언어야? | `tool_rag` → **1단계에서 웹 전환** | 임베딩 13 + 생성 1 |

실측 결과다. 어느 단계에서 웹으로 넘어가는지가 질문마다 다르다.

```
환불 규정 알려줘        1단계 0.7480 통과 → 2단계 통과      → 문서로 답변
지금 고객센터 열려 있어?  1단계 0.7572 통과 → 2단계 통과(84자) → 문서로 답변
오늘 서울 날씨 어때?     1단계 0.7222 통과 → 2단계 실패(9자)  → 웹 검색
비트코인 얼마야?        1단계 0.6197 미달                   → 웹 검색 (생성 절약)
```

`"지금 고객센터 열려 있어?"` 가 문서로 답변되는 것이 2단계의 요점이다. 답변은
`"문서에 없습니다. 고객 지원 시간은 평일 09:00–18:00 …"` 처럼 시작하지만, 운영 시간을
정확히 전달하므로 길이 기준(60자)에 걸려 실패로 처리되지 않는다.

`/mode direct` 를 쓰면 RAG 도 웹 검색도 거치지 않는다.

확인 포인트: `[계획] → [행동] → [관찰]` 순서로 도구 선택 근거가 출력되는지.

### 6단계 — HTTP API

```bash
python 6-api.py
```

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

브라우저에서 **http://127.0.0.1:8000/docs** (Swagger UI) 로 접근한다.

curl 로 호출하려면 **새 터미널**을 열고 가상환경 활성화 없이 사용해도 된다(curl 은 파이썬과 무관).

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok"}

curl -s http://127.0.0.1:8000/documents
# {"count":12,"documents":[{"doc_id":"weather",...}]}

curl -s http://127.0.0.1:8000/tools
# {"tools":[{"name":"tool_list_documents",...},...,{"name":"tool_web_search","description":"외부 웹 검색 후 답변 생성"}]}   ← 5건

curl -s -X POST http://127.0.0.1:8000/rag \
  -H 'Content-Type: application/json' \
  -d '{"question":"주말에 고객 지원 받을 수 있어?","top_k":2}'
# {"mode":"rag","question":"...","top_k":2,"answer":"주말에는 고객 지원을 받을 수 없습니다."}

curl -s -X POST http://127.0.0.1:8000/agent \
  -H 'Content-Type: application/json' \
  -d '{"question":"문서 구성 요약해줘"}'
# {"mode":"agent","reason":"문서 구성을 먼저 요약하는 것이 맞음","tool_name":"tool_document_summary","result":"..."}
```

서버 종료는 Ctrl-C.

**바인딩.** 기본값은 `127.0.0.1` 로 같은 PC 에서만 접속된다. 학습용 예제이므로 이대로 두는 것을 권한다.

### 7단계 — 대화형 챗봇

웹 서버가 아니다. URL 이 없으며 터미널에서 직접 실행한다.

```bash
python 7-chatbot.py
```

```
============================================================
RAG 챗봇 (Gemini) — 1~6단계를 대화형으로 묶은 마지막 단계
============================================================
모드: agent / top_k: 2
/help 로 명령 목록을 볼 수 있습니다.

나>
```

`나>` 프롬프트에 질문을 입력한다. 종료는 `/quit` 또는 Ctrl-D.

#### 명령

| 명령 | 동작 |
|---|---|
| `/help` | 명령 목록 |
| `/mode agent\|rag\|direct` | 답변 경로 전환 (기본 `agent`) |
| `/topk <1-10>` | RAG 검색 문서 수 (기본 2) |
| `/docs` | 현재 코퍼스 출력 |
| `/history` | 대화 이력 |
| `/reset` | 이력 초기화 |
| `/quit` | 종료 |

#### 검증 시나리오 — 멀티턴 동작 확인

이 단계의 핵심은 대화 이력이다. 아래 순서로 입력하면 후속 질문 처리가 눈에 보인다.

```
나> 서울 여름 날씨 어때?
나> 그럼 주말에 문의 가능해?
```

실제 출력에서 확인할 지점:

```
[4] search query='서울 여름 날씨 어때?' top_k=2
  hit 'weather' score=0.7941
  hit 'policy'  score=0.5797
봇> 서울의 여름 날씨는 대체로 덥고 습하며, 평균 기온은 25도 안팎입니다.

  [이력] 후속 질문으로 판단 → 이전 대화를 함께 사용
[4] search query='서울 여름 날씨 어때? 그럼 주말에 문의 가능해?' top_k=2
  hit 'weather' score=0.7637
  hit 'policy'  score=0.6298          ← 0.5797 에서 상승
봇> ... 주말에는 고객 지원이 휴무입니다.
```

두 번째 턴에서 검색 질의에 직전 질문이 병합되고, `policy` 문서 점수가 0.5797 → 0.6298 로 오른다.
`"그럼 주말에 문의 가능해?"` 만으로는 검색되지 않던 문서가 이력 덕분에 검색된다.

경로별 차이를 대조하려면 같은 질문을 모드만 바꿔 던진다.

```
나> /mode direct
나> 서울 여름 날씨 어때?      ← 문서를 보지 않고 LLM 자체 지식으로 답한다
```

#### 비대화형 실행 (스크립트/CI)

```bash
printf '서울 여름 날씨 어때?\n그럼 주말에 문의 가능해?\n/quit\n' | python 7-chatbot.py
```

---

### 8단계 — 브라우저 GUI

```bash
python 8-gui.py
# http://127.0.0.1:8001 열기
# INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
```

브라우저로 `http://127.0.0.1:8001` 을 연다. 6단계(8000)와 포트가 다르므로 동시에 띄울 수 있다.

화면 구성

| 요소 | 대응하는 CLI 명령 |
|---|---|
| 모드 선택 | `/mode agent\|rag\|direct` |
| top_k 입력 | `/topk <1-10>` |
| 대화 초기화 | `/reset` |
| 실행 추적 체크박스 | (CLI에서는 터미널에 항상 출력됨) |

Enter 전송, Shift+Enter 줄바꿈. 한글 조합 중 Enter 는 IME 확정으로만 처리되고 전송되지 않는다.

#### API 키 없이 동작 확인

서버 기동과 화면 로드는 키 없이도 된다. 질문을 보내는 시점에만 키가 필요하다.

```bash
curl -s http://127.0.0.1:8001/health
# {"status":"ok","sessions":"0","api_key":"없음","pid":"62897","started":"2026-09-04 14:33:15"}
#
# api_key 가 "없음" 이면 이 프로세스는 키 없이 뜬 것이다. 지금 export 해도 반영되지 않는다.
# started 시각이 export 시각보다 앞서면 오래된 프로세스가 포트를 잡고 있는 것이다.

curl -s http://127.0.0.1:8001/api/modes
# {"modes":["agent","rag","direct"],"doc_count":12}

curl -s -X POST http://127.0.0.1:8001/api/chat \
  -H 'Content-Type: application/json' -d '{"session_id":"","message":"안녕하세요"}'
# {"detail":"Gemini 설정을 확인하세요 (GEMINI_API_KEY)."}   ← 키 없을 때 503
```

#### 입력 검증 동작 확인

```bash
# 허용되지 않은 Host 헤더 — 421 반환
curl -s -H 'Host: evil.example.com' http://127.0.0.1:8001/health
# {"detail":"허용되지 않은 Host 헤더"}

# 입력 길이 상한 — 2000자 초과 시 422
python -c "import json;print(json.dumps({'message':'가'*2001}))" | \
  curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8001/api/chat \
  -H 'Content-Type: application/json' --data-binary @-
# 422

# 알 수 없는 모드 — 400
curl -s -X POST http://127.0.0.1:8001/api/settings \
  -H 'Content-Type: application/json' -d '{"session_id":"","mode":"hack"}'
# {"detail":"알 수 없는 모드입니다."}

# 응답 헤더 확인
curl -s -D - -o /dev/null http://127.0.0.1:8001/ | grep -i content-security-policy
```

#### 세션 동작 확인

`session_id` 는 서버가 발급한다. 클라이언트가 임의 값을 보내면 무시되고 새 세션이 나온다.

```bash
S=$(curl -s -X POST http://127.0.0.1:8001/api/settings \
  -H 'Content-Type: application/json' -d '{"session_id":"","mode":"rag","top_k":5}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['session_id'])")

curl -s -X POST http://127.0.0.1:8001/api/settings \
  -H 'Content-Type: application/json' -d "{\"session_id\":\"$S\"}"
# {"session_id":"...","mode":"rag","top_k":5}     ← 설정 유지

curl -s -X POST http://127.0.0.1:8001/api/settings \
  -H 'Content-Type: application/json' -d '{"session_id":"forged-id-000"}'
# {"session_id":"<새 ID>","mode":"agent","top_k":2}   ← 위조 ID 는 새 세션으로 격리
```

---

## 2. 전체 점검 순서

처음 실행하거나 환경이 바뀌었을 때는 아래 순서로 좁혀 나간다.

```bash
source venv/bin/activate && cd ch01/dxx-app

python 0-env.py           # .env 가 읽히는지 (API 불필요)
python 1-documents.py     # 파일 I/O 만 확인 (API 불필요)
python 2-embeddings.py    # API 키 + 임베딩 모델 확인
python 3-llm.py           # API 키 + 생성 모델 확인
python 4-1-rag.py         # 검색 + 프롬프트 + 답변
python 4-2-websearch.py   # 웹 검색 + 근거 출처 확인
python 5-agent.py         # 도구 선택 + 폴백 통합 확인
python 7-chatbot.py       # 대화 이력까지 확인
python 8-gui.py           # 브라우저 GUI (http://127.0.0.1:8001)
```

실패 지점으로 원인을 좁힌다.

| 실패 단계 | 원인 |
|---|---|
| 0단계 | `.env` 위치나 형식 |
| 1단계 | 파이썬 환경 (가상환경 미활성화 등) |
| 2단계 | API 키 또는 임베딩 모델 |
| 3단계 | API 키 또는 생성 모델 |
| 4-1단계 | 위 둘은 정상인데 실패하면 코퍼스나 검색 로직 |
| 4-2단계 | 그라운딩 도구 지원 여부 |

생성 모델과 임베딩 모델은 별개로 관리된다. 2단계는 되는데 3단계가 실패하면 생성 모델 쪽이다.

---

## 3. API 호출 비용

무료 티어라도 호출량은 확인해 두는 편이 낫다. 인메모리 벡터 DB 는 영속되지 않으므로,
**질문 1회마다 전체 문서를 다시 임베딩한다.**

| 실행 | 임베딩 호출 | 생성 호출 |
|---|---|---|
| `2-embeddings.py` | 2 | 0 |
| `3-llm.py` | 0 | 1 |
| RAG 질문 1회 (문서 12건, 점수 충족) | 13 (문서 12 + 질의 1) | 1 |
| RAG 질문 1회 (1단계 미달 → 웹) | 13 | 1 (웹 답변만) |
| RAG 질문 1회 (2단계 실패 → 웹) | 13 | 2 (문서 답변 + 웹 답변) |
| `4-2-websearch.py` | 0 | 1 |
| 웹 검색 질문 1회 | 0 | 1 |
| `5-agent.py` (예제 6문항) | **52** (RAG 4문항 × 13) | **5** (문서 3 + 웹 2) |
| GUI 질문 1회 (agent 모드) | 7단계와 동일 | 7단계와 동일 |

`5-agent.py` 실측 내역이다. 문서 목록·요약 2문항은 API 를 쓰지 않고,
나머지 4문항이 전부 RAG 를 거치므로 문항당 13회씩 나간다.

```
문서 목록 보여줘            임베딩  0  문서생성 0  웹생성 0
문서 구성 요약해줘           임베딩  0  문서생성 0  웹생성 0
주말에 고객 지원 받을 수 있어?  임베딩 13  문서생성 1  웹생성 0
서울 여름 날씨는 어때?        임베딩 13  문서생성 1  웹생성 0
오늘 서울 날씨 어때?         임베딩 13  문서생성 1  웹생성 1   ← 2단계 전환
파이썬은 어떤 언어야?         임베딩 13  문서생성 0  웹생성 1   ← 1단계 차단
```

문서 수가 늘면 질문당 임베딩 호출이 선형으로 증가한다. 실제 시스템이 인덱스를 영속화하는 이유다.
코퍼스를 3건에서 12건으로 늘리면서 RAG 질문 1회당 임베딩 호출이 4회에서 13회로 늘었다.
문서를 더 추가할 계획이라면 인덱스 영속화를 먼저 검토한다.

---

## 4. 문제 해결

| 증상 | 원인 | 조치 |
|---|---|---|
| `zsh: command not found: python` | 가상환경 미활성화 | `source venv/bin/activate` (0-1) |
| `ModuleNotFoundError: No module named 'google'` | 가상환경 미활성화 또는 패키지 미설치 | `which python` 으로 활성화 확인 후 0-2 |
| 프롬프트에 `(venv)` 가 없음 | 새 터미널을 열었거나 `deactivate` 함 | 활성화와 키 설정을 다시 수행 |
| 질문 입력 후 `[오류] Gemini 설정을 확인하세요 (GEMINI_API_KEY)` | 키 미설정 **또는** 패키지 미설치 | 두 가지를 모두 확인. 하위 모듈이 `sys.exit(1)` 로 끝나 원인이 구분되지 않는다 |
| `404 ... is no longer available` | 모델 서비스 종료 | 0-3 의 모델 목록 확인 후 `GEMINI_MODEL` 설정 |
| `FutureWarning: All support for the google.generativeai package has ended` | SDK EOL | 동작에는 지장 없음. `PYTHONWARNINGS=ignore` 로 억제. 근본 해결은 `google-genai` 로 이전 |
| `4-1-rag.py` 실행 시 아무 출력 없음 | `main()` 호출부 주석 처리 | 파일 하단 주석 해제 (1장 4-1단계) |
| `WARNING: You must pass the application as an import string` 후 서버 미기동 | `uvicorn.run(app, reload=True)` 조합 | `reload` 인자를 빼거나, uvicorn CLI 로 실행 (`uvicorn 6-api:app --reload`) |
| GUI 가 `{"detail":"허용되지 않은 Host 헤더"}` 로 421 | 8001 외 포트로 띄움 | `8-gui.py` 의 `ALLOWED_HOSTS` 에 해당 포트 추가 |
| 포트 8000 이미 사용 중 | 이전 서버 잔존 | `lsof -ti:8000 \| xargs kill` |
| 포트 8001 이미 사용 중 | 이전 GUI 서버 잔존 | `lsof -ti:8001 \| xargs kill` |
| GUI 접속 시 `{"detail":"허용되지 않은 Host 헤더"}` | `127.0.0.1`/`localhost` 외 호스트명으로 접속 | 해당 두 이름으로만 접속. 다른 이름이 필요하면 `8-gui.py` 의 `ALLOWED_HOSTS` 에 추가 |
| GUI 에서 한글 마지막 글자가 잘려 전송됨 | 조합 중 Enter 가 전송으로 처리됨 | `keydown` 핸들러의 `e.isComposing` 검사 확인 |
| `export` 했는데 GUI 가 계속 503 | 키 없이 먼저 뜬 프로세스가 8001 을 점유 중. 환경변수는 `execve()` 시점에 고정되어 사후 갱신 불가 | `/health` 의 `api_key`·`started` 확인 → `lsof -ti:8001 \| xargs kill` 후 키를 export 한 터미널에서 재기동 |
| GUI 에서 전송 버튼이 무반응, 서버 로그에 요청 없음 | 인라인 JS 구문 오류로 이벤트 리스너 미등록 | 브라우저 개발자 도구 콘솔 확인. `curl -s http://127.0.0.1:8001/ \| sed -n '/<script>/,/<\/script>/p' > /tmp/p.js && node --check /tmp/p.js` |
| 서버를 껐는데 포트가 계속 점유됨 | `&` 로 띄운 프로세스가 셸 종료 후 고아(PPID 1)로 남음 | `lsof -nP -iTCP:8001 -sTCP:LISTEN` 으로 PID 확인 후 `kill` |
| `GEMINI_API_KEY 가 유효하지 않습니다` | 키가 잘못됐거나 다른 종류의 토큰 | AI Studio 키는 `AIza` 로 시작하는 39자다. 발급 페이지에서 다시 확인 |
| `Gemini API 오류 (HTTP 400)` | 키가 잘못됐거나 요청 형식 문제 | 위 `curl` 로 키부터 확인 |
| `[W3] 근거 출처 0건` | 모델이 검색하지 않고 내부 지식으로 답함 | 질문에 시점 표지(`오늘`·`최근`)를 넣어 다시 시도 |
| 문서에 답이 있는데 웹으로 넘어감 | 2단계 판정 오탐. 답변이 60자 이하이면서 `문서에 없습니다` 를 포함 | `INSUFFICIENT_MAX_CHARS` 를 올리거나 표지를 좁힌다 |
| 문서에 답이 없는데 문서로 답변함 | 2단계 표지에 걸리지 않는 표현으로 모델이 답함 | `INSUFFICIENT_MARKERS` 에 해당 표현 추가 |
| `.env` 에 넣었는데 반영되지 않음 | 같은 폴더가 아니거나 `KEY=VALUE` 형식이 아님 | `python 0-env.py` 로 어떤 키가 올라가는지 확인 |
| `.env` 값이 무시되고 다른 값이 쓰임 | 셸에 같은 이름의 변수가 이미 있음 (셸이 우선) | `unset RAG_MIN_SCORE` 후 재실행 |
| 문서에 있는 내용인데 웹 검색으로 넘어감 | `RAG_MIN_SCORE` 기준이 너무 높음 | `[폴백] 검색 최고 점수` 로그의 실제 점수를 보고 `RAG_MIN_SCORE` 를 낮춘다 |
| 문서에 있는 내용인데 RAG 를 거치지 않고 일반 답변이 나옴 | `choose_action()` 키워드 목록에 해당 주제가 없음 | 5-agent.py 의 키워드 목록에 추가한다 |
| 문서에 없는데도 "문서에 없습니다"로 끝남 | 기준이 너무 낮아 폴백이 발동하지 않음 | 같은 로그의 점수를 보고 `RAG_MIN_SCORE` 를 올린다 |
| `TypeError: tool_*() missing 1 required positional argument` | 질문을 받는 도구가 `run_agent_with_trace()` 의 인자 전달 목록에서 빠짐 | 해당 도구를 목록에 추가한다 |
| 챗봇이 새 질문을 후속 질문으로 오인 | `is_followup()` 규칙 기반 판정 | `/reset` 으로 이력 초기화 후 재질문 |

---

## 5. 검증 환경

| 항목 | 값 |
|---|---|
| 검증일 | 2026-09-06 |
| OS | macOS (Darwin 25.6.0, arm64) |
| 셸 | zsh |
| 가상환경 | 리포지터리 루트의 `venv` (Python 3.14.6) |
| google-generativeai | 0.8.6 |
| fastapi / uvicorn / pydantic | 0.141.1 / 0.52.3 / 2.13.4 |
| 생성 모델 | `gemini-2.5-flash` |
| 임베딩 모델 | `models/gemini-embedding-001` (dim=3072) |
| 웹 검색 | Gemini 그라운딩 (`google_search` 도구, REST 호출) |

패키지는 이 트리의 `venv` 에 설치 완료되었다.

```bash
source venv/bin/activate
pip list | grep -iE "generativeai|fastapi|uvicorn|pydantic"
```

검증 완료: 0~8단계 전 경로, Gemini 그라운딩 실호출, RAG 폴백 1·2단계 모두.

폴백 임계값 실측값(12건 코퍼스, `gemini-embedding-001`):

| 구분 | 질문 | 최고 유사도 |
|---|---|---|
| 관련 | 환불 규정 알려줘 | 0.7480 |
| 관련 | 주말에 고객 지원 받을 수 있어? | 0.8045 |
| 관련 | 보증 기간 얼마나 되나요? | 0.7883 |
| 무관 | 카드 게임 추천해줘 | 0.6114 |
| 무관 | 배송이라는 영화 봤어? | 0.6548 |
| 무관 | 계정 이름 짓는 법 | 0.6578 |

두 구간 사이가 0.658~0.748 이라 `RAG_MIN_SCORE=0.70` 으로 정했다.

미검증 항목: 동시 접속, 장시간 세션.
