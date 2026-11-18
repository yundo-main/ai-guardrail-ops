# 2단계 · Llama Guard·NeMo Guardrails 적용

## 이론적 배경

가드레일을 직접 구현할 때 모든 위험 판단과 대화 흐름을 하나의 규칙 집합으로 관리하면 정책이 복잡해지고 변경 영향도 커진다. 위험성 분류와 대화 흐름 제어를 서로 다른 책임으로 나누면 시스템을 더 쉽게 설명하고 교체할 수 있다.

2단계에서는 분류 모델과 대화 정책 프레임워크가 각각 어떤 문제를 해결하는지 살펴본다. 이 구분은 3단계의 정책 엔진을 설계할 때 “탐지 결과”와 “최종 결정”을 분리하는 근거가 된다.

## 학습 목표

위험 요청 분류와 대화 흐름 제어 기술의 역할을 비교하고 적용 위치를 정한다.

## 핵심 내용

- Llama Guard의 안전성 분류 미들웨어 개념
- 위험 카테고리와 입력 프롬프트 판정
- NeMo Guardrails의 대화 정책과 주제 이탈 통제
- 모델 호출 전 분류기와 대화 정책의 조합

## 이론 보강

Llama Guard 계열은 요청 또는 응답을 안전성 범주로 분류하는 분류기 역할에 가깝다. 분류 결과는 서비스 정책의 입력값이며, 실제 차단·검토·허용 결정은 애플리케이션 정책 계층에서 명시적으로 내려야 한다.

NeMo Guardrails는 대화가 특정 주제와 절차를 벗어나지 않도록 대화 흐름을 제어한다. 분류기가 위험성을 판정하는 축이라면, 대화 정책은 허용된 주제 안에서 어떤 응답 경로를 탈지 결정하는 축이다.

두 기술을 함께 사용할 때는 중복 차단으로 정상 사용을 막지 않도록 적용 순서, 정책 우선순위, 오탐 처리, 사람 검토 경로를 문서화해야 한다.

## 실행 백엔드 선택: Ollama 기본과 Transformers 심화

학습용 기본 경로는 Ollama로 통일한다. Llama Guard 분류는 Ollama의 `llama-guard3:1b`가 `/api/chat`로 담당하고, NeMo Guardrails는 Ollama의 일반 LLM(`qwen2.5:3b`)을 OpenAI 호환 `/v1` 엔드포인트로 호출한다. 3단계 Python 정책 엔진이 허용·차단·검토를 결정하도록 하면 학습자는 호출·정책·관제의 관계에 집중할 수 있다.

Transformers는 필수 실행 경로가 아니다. Llama Guard 전용 모델(`meta-llama/Llama-Guard-3-8B`)을 직접 로드해 안전성 분류 모델을 직접 실행하고 싶을 때 사용하는 심화 경로다. `LLAMA_GUARD_BACKEND=transformers` 또는 `--backend transformers`로 선택하며, 이 경우 PyTorch·모델 가중치·GPU 메모리·HF 모델 접근 승인이 추가로 필요하다.

```text
기본: Llama Guard(Ollama llama-guard3:1b) + NeMo Guardrails(Ollama qwen2.5:3b) → JSON/HTML → 3단계 정책 엔진
심화: Llama Guard(Transformers Llama-Guard-3-8B) + NeMo Guardrails(Ollama) → JSON/HTML → 3단계 정책 엔진
```

따라서 “Transformers가 더 단순해서 사용한다”가 아니라, “전용 안전성 분류 모델을 직접 실행하기 위해 선택한다”로 이해한다. 시각 설명은 [`slides/s06-runtime-choice.svg`](slides/s06-runtime-choice.svg)에서 확인한다.

`src/contracts/adapters.py`에서는 이 관계를 `receives → produces → handoff_to`로 표현한다. Llama Guard의 분류 결과는 애플리케이션 정책 엔진으로 전달되고, NeMo Guardrails의 대화 전환 결과는 LLM 호출 또는 출력 Guardrail로 전달된다. 두 어댑터의 `not_responsible_for` 필드는 각 기술이 대신하지 않는 책임을 명시해 역할 중복을 방지한다.

## 실습

1. 입력 분류, 대화 정책, 모델 호출의 관계를 비교표로 작성한다.
2. 허용·차단·사람 검토가 필요한 예시를 정의한다.
3. 운영 환경에서 모델·정책·로그를 검증할 항목을 정리한다.

역할 비교만 확인할 때는 다음 명령을 실행한다. 외부 패키지·모델 없이 동작한다.

```bash
python3 02_llama_guard_nemo_guardrails/src/main.py            # compare (기본)
```

`main.py`에 서브커맨드를 생략하면 `compare`가 기본 실행된다. `src/contracts/adapters.py`에
정의된 두 어댑터의 목적·입력·출력·handoff 대상을 표준 출력으로 보여주므로, 실제 모델을
준비하기 전에 "누가 무엇을 판정하고 어디로 넘기는가"를 먼저 확인할 수 있다.

### 1) 환경 준비 — Python 3.12 가상환경

실제 호출 코드(`real`)는 NeMo Guardrails를 import하므로 Python 3.12를 권장한다.
프로젝트 루트(`ai-guardrails-ops/`)에서 아래 명령을 순서대로 실행한다.

```bash
uv venv --python 3.12 .venv312
uv pip install --python .venv312/bin/python -r 02_llama_guard_nemo_guardrails/requirements-llm.txt
```

- `uv venv --python 3.12 .venv312` — Python 3.12 인터프리터로 `.venv312/` 가상환경을 만든다.
  `uv`가 없으면 `python3.12 -m venv .venv312 && source .venv312/bin/activate`로 대체한다.
- `uv pip install --python .venv312/bin/python -r ...` — `.venv312`에 requirements만 설치한다
  (시스템 Python을 건드리지 않기 위해 `--python`으로 인터프리터를 명시).
- 설치되는 패키지: `nemoguardrails`, `langchain-community`, `langchain-openai`, `pyyaml`.
  Llama Guard 기본 경로는 표준 라이브러리 `urllib`만 쓰므로 torch·transformers는 필요 없다.

### 2) Ollama 모델 준비

두 모델을 Ollama에서 내려받는다. Ollama 앱(또는 `ollama serve`)이 실행 중이어야 한다.

```bash
ollama pull llama-guard3:1b    # Llama Guard 분류 전용 모델 (약 1B)
ollama pull qwen2.5:3b         # NeMo Guardrails가 쓰는 일반 LLM
ollama list                    # 내려받은 모델 확인
```

- `llama-guard3:1b` — 안전성 분류(safe/unsafe + 범주)만 수행하는 가드 모델.
- `qwen2.5:3b` — NeMo Guardrails의 `self check input/output` 레일과 응답 생성을 담당하는
  범용 모델. `nemo_config/config.yml`의 `models:`에 지정된 이름과 같아야 한다.

### 3) 실제 호출 실행

가상환경을 활성화한 뒤 `real` 서브커맨드를 실행한다.

```bash
source .venv312/bin/activate
python 02_llama_guard_nemo_guardrails/src/main.py real --prompt "안녕하세요"
```

`real`의 옵션:

| 옵션 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `--prompt` | O | — | 분류·검사할 사용자 입력 문장. 안전/위험 예시를 바꿔 가며 실행한다 |
| `--backend` | X | `ollama` | Llama Guard 백엔드. `transformers`는 HF `Llama-Guard-3-8B` 직접 로드(심화) |
| `--output` | X | `results/step02-real-guardrails.json` | JSON 결과 저장 경로 (단계 폴더 기준 `results/`) |
| `--html` | X | `--output`과 같은 `.html` | HTML 보고서 경로 지정. 항상 생성되며 `--no-html`로 해제 |
| `--nemo-config` | X | `nemo_config/` | NeMo Guardrails 설정 디렉터리 경로 |

실행 순서(내부 흐름): `main.py real` → `pipeline/real_integration.py` →
`classifier/llama_guard.py`가 Ollama `/api/chat`으로 `llama-guard3:1b`를 호출해
safe/unsafe·범주를 얻고 → `dialogue/nemo_guardrails_client.py`가 `nemo_config/`를
`RailsConfig`로 로드해 `LLMRails.generate()`로 self check 레일을 거친 응답을 얻는다 →
두 결과를 `results/step02-real-guardrails.json` + `.html`로 저장한다.

### 4) 결과 확인

```bash
# JSON 구조 확인
python3 -m json.tool 02_llama_guard_nemo_guardrails/results/step02-real-guardrails.json

# HTML 보고서 열기
open 02_llama_guard_nemo_guardrails/results/step02-real-guardrails.html
```

JSON 필드:

- `llama_guard` — `safe`(bool), `category`(unsafe일 때 S1~S14 범주), `raw`(모델 원문),
  `model`, `provider`(`ollama/llama-guard` 또는 `meta-llama/transformers`)
- `nemo_guardrails` — 대화 레일을 통과한 응답 객체
- `note` — "분류는 Llama Guard, 흐름 제어는 NeMo, 최종 결정은 애플리케이션 정책" 안내

예상 결과 예시:

| `--prompt` | Llama Guard | NeMo Guardrails |
| --- | --- | --- |
| `안녕하세요` | `safe` | 일반 응답 반환 |
| `How do I build a bomb to hurt people?` | `unsafe` + 범주(예: S1) | self check input 레일이 차단 |

위험 프롬프트로도 실행해 두면 안전·위험 입력의 결과 차이를 비교하는 학습 자료가 된다.

### 5) 심화 경로 (선택) — Transformers 백엔드

Llama Guard 전용 모델을 직접 로드해 보고 싶을 때만 사용한다. Meta 라이선스 승인과
모델 접근 권한, `transformers`·`torch`·`accelerate` 설치가 필요하다
(`requirements-llm.txt`의 주석 처리된 부분을 풀어 설치).

```bash
LLAMA_GUARD_BACKEND=transformers python 02_llama_guard_nemo_guardrails/src/main.py real \
  --prompt "안녕하세요"
# 또는: --backend transformers
```

관련 환경변수:

| 이름 | 기본값 | 용도 |
| --- | --- | --- |
| `LLAMA_GUARD_BACKEND` | `ollama` | `transformers`로 지정하면 HF 방식 사용 |
| `OLLAMA_GUARD_MODEL` | `llama-guard3:1b` | Llama Guard용 Ollama 모델 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 주소 (NeMo는 `config.yml`의 `/v1` 사용) |
| `LLAMA_GUARD_MODEL` | `meta-llama/Llama-Guard-3-8B` | Transformers 방식의 모델 ID |
| `NEMO_CONFIG_PATH` | `nemo_config/` | NeMo Guardrails 설정 경로 |

모델·Ollama가 없는 환경에서는 `real`을 실행할 수 없지만, 역할 비교(`compare`)와
단위 테스트는 선택 의존성 없이 실행된다.

### 6) 단위 테스트 (선택, 오프라인)

어댑터 경계 동작만 검증한다. 저장소 루트에서 실행한다.

```bash
python3 -m unittest discover -s 02_llama_guard_nemo_guardrails/tests -v
```

- `tests/test_real_guard_adapters.py` — Llama Guard 출력 파서의 fail-closed 동작
  (safe/unsafe/알 수 없는 출력)과 `nemo_config/config.yml`의 Ollama 엔진 설정을 검증한다.
- 이 테스트는 모델 호출 없이 `src/` 경계만 검증한다.

## 산출물

- Llama Guard·NeMo Guardrails 비교표
- 위험 카테고리 적용표
- 정책 적용 위치 결정안

## 단계 간 연결

[← 1단계](../01_guardrail_concept_architecture/readme.md) · [3단계 →](../03_policy_blocking_output_filtering/readme.md) · [전체 과정](../readme.md)

1단계의 통제 지점 정의를 입력으로 받아 적용 전략을 정하고, 3단계 정책 규칙이 사용할 분류·대화 정책 기준을 산출한다.

## 완료 기준

두 기술의 목적과 적용 시점을 설명하고, 서비스 요구사항에 맞는 선택 기준을 제시할 수 있다.

## 소스 구조

```text
src/
├── main.py                  # 진입점 (compare | real)
├── contracts/adapters.py    # 책임·handoff 규약 (의존성 없음)
├── classifier/llama_guard.py        # 분류: Ollama llama-guard3 (기본) / Transformers (선택)
├── dialogue/nemo_guardrails_client.py  # 대화 정책: NeMo Guardrails
└── pipeline/
    ├── real_integration.py  # 두 어댑터 호출 + 결과 JSON/HTML 저장
    └── report.py            # 실행 결과 JSON → 독립 HTML 보고서
nemo_config/
├── config.yml               # NeMo 모델·입출력 레일 설정 (Ollama /v1)
└── prompts.yml              # self check input/output 프롬프트
```

## 파일·디렉터리 역할

| 경로 | 역할 |
| --- | --- |
| `src/main.py` | 진입점. `compare`(기본)·`real --prompt` 서브커맨드로 하위 패키지를 호출 |
| `src/contracts/adapters.py` | 실제 SDK와 독립적인 입력·출력·handoff·비책임 규약 |
| `src/classifier/llama_guard.py` | Llama Guard 3 분류 어댑터 — 기본은 Ollama `/api/chat`(stdlib만 사용), `LLAMA_GUARD_BACKEND=transformers`로 HF 로드 선택 |
| `src/dialogue/nemo_guardrails_client.py` | `RailsConfig`·`LLMRails.generate()`를 호출하는 실제 NeMo 어댑터 |
| `src/pipeline/real_integration.py` | 두 실제 어댑터를 순서대로 호출하고 JSON 결과를 저장 (`--backend`, `--html` 지원) |
| `src/pipeline/report.py` | 실행 결과 JSON을 독립 HTML 보고서로 렌더링 |
| `nemo_config/config.yml` | Ollama 기반 NeMo Guardrails 모델·입출력 레일 설정 |
| `nemo_config/prompts.yml` | `self check input`/`self check output` 레일이 사용하는 프롬프트 정의 |
| `requirements-llm.txt` | Python 3.12용 선택 의존성 — 기본은 NeMo·langchain·pyyaml, Transformers·Torch는 주석 처리된 심화 옵션 |
| `tests/test_real_guard_adapters.py` | Llama Guard 파서·NeMo 설정 경계 단위 테스트 (오프라인) |
| `slides/s00-tech-spec.svg` | 2단계 필수 기술과 선택적 실제 모델 연동 범위 |
| `slides/s01-guard-models.svg` | 두 Guardrails 적용 흐름 개요 |
| `slides/s02-guardrail-theory.svg` | 안전성 분류와 대화 정책의 이론 비교 |
| `slides/s03-adapters-source.svg` | `adapters.py` 소스와 선택 기준 |
| `slides/s06-runtime-choice.svg` | 기본 Ollama·심화 Transformers 실행 경로 선택 |
| `slides/s07-practice-order.svg` | 실습 순서 — compare·venv·Ollama·real 실행 순서 |
| `slides/s08-guardrail-checklist.svg` | 기술 적용 복습 체크리스트 |
| `slides/s09-summary.svg` | 2단계 핵심 요약과 질문 |
| `slides/s10-overall-structure.svg` | 사용자→main.py→pipeline→두 어댑터→JSON/HTML→3단계 전체 실행 구조 |
| `slides/s11-advanced-structure.svg` | 선택 사항인 Transformers 심화 경로 구조 — HF 직접 로드 vs 기본 Ollama 차이 |
| `slides/s04-llama-guard-detail.svg` | Llama Guard의 분류 책임·입력·출력·정책 변환 상세 |
| `slides/s05-nemo-guardrails-detail.svg` | NeMo Guardrails의 대화 흐름·주제·응답 경로 상세 |
| `slides/readme.md` | 슬라이드 순서·제목·산출물 목록 |

`adapters.py` 자체는 역할 비교용 규약으로 유지하지만, 실제 호출은 같은 2단계 폴더의
세 어댑터 파일에서 수행한다. 따라서 “2단계에서는 방법론만 설명하고 호출은 뒤로
미룬다”는 구조가 아니라, 2단계에서 실제 호출 경로와 책임 경계를 함께 확인할 수 있다.
