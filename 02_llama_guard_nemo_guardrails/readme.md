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

## 실행 백엔드 선택: Ollama와 Transformers

학습용 기본 경로는 Ollama로 통일한다. NeMo Guardrails가 Ollama의 일반 LLM을 호출하고, 3단계 Python 정책 엔진이 허용·차단·검토를 결정하도록 하면 학습자는 호출·정책·관제의 관계에 집중할 수 있다.

Transformers는 필수 실행 경로가 아니다. Llama Guard 전용 모델을 직접 로드해 일반 LLM과 안전성 분류 모델을 분리하고 싶을 때 사용하는 심화 경로다. 이 경우 PyTorch·모델 가중치·GPU 메모리·NeMo custom adapter를 추가로 관리해야 한다.

```text
기본: NeMo Guardrails → Ollama → Python 정책 엔진
심화: 일반 LLM → Transformers Llama Guard → Python 정책 엔진
```

따라서 “Transformers가 더 단순해서 사용한다”가 아니라, “전용 안전성 분류 모델을 직접 실행하기 위해 선택한다”로 이해한다. 시각 설명은 [`slides/s06-runtime-choice.svg`](slides/s06-runtime-choice.svg)에서 확인한다.

`src/contracts/adapters.py`에서는 이 관계를 `receives → produces → handoff_to`로 표현한다. Llama Guard의 분류 결과는 애플리케이션 정책 엔진으로 전달되고, NeMo Guardrails의 대화 전환 결과는 LLM 호출 또는 출력 Guardrail로 전달된다. 두 어댑터의 `not_responsible_for` 필드는 각 기술이 대신하지 않는 책임을 명시해 역할 중복을 방지한다.

## 실습

1. 입력 분류, 대화 정책, 모델 호출의 관계를 비교표로 작성한다.
2. 허용·차단·사람 검토가 필요한 예시를 정의한다.
3. 운영 환경에서 모델·정책·로그를 검증할 항목을 정리한다.

역할 비교만 확인할 때는 다음 명령을 실행한다.

```bash
python3 02_llama_guard_nemo_guardrails/src/main.py            # compare (기본)
```

### 실제 프레임워크 호출

실제 호출 코드는 `src/classifier/llama_guard.py`, `src/dialogue/nemo_guardrails_client.py`,
`src/pipeline/real_integration.py`에 있고, 모두 `src/main.py`를 진입점으로 실행한다. `adapters.py`는 책임·handoff 계약이고,
이 세 파일이 각각 실제 모델과 프레임워크를 호출한다.

Python 3.12 환경에서 선택 의존성을 설치한다.

```bash
python3.12 -m venv .venv-guardrails
source .venv-guardrails/bin/activate
python -m pip install -r 02_llama_guard_nemo_guardrails/requirements-llm.txt
```

Llama Guard 3는 Hugging Face에서 Meta 라이선스를 승인하고 모델 접근 권한을
받아야 하며, NeMo Guardrails는 기본 예제 설정에서 로컬 Ollama의 OpenAI 호환
엔드포인트를 사용한다. Ollama를 실행하고 모델을 받은 뒤 다음처럼 호출한다.

```bash
ollama pull qwen2.5:3b
python 02_llama_guard_nemo_guardrails/src/main.py real \
  --prompt "회사 비밀번호 재설정 절차를 요약해줘" \
  --output results/step02-real-guardrails.json
```

실행 결과는 `results/step02-real-guardrails.json`에 저장된다. `llama_guard`는
`safe/unsafe`와 위험 범주를 반환하고, `nemo_guardrails`는 대화 레일을 통과한
응답 객체를 반환한다. 최종 허용·차단 결정은 여전히 3단계 정책 엔진의 책임이다.
모델 가중치·Ollama가 없는 환경에서는 이 명령을 실행할 수 없지만, 역할 비교와
단위 테스트는 선택 의존성 없이 실행된다.

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
├── contracts/adapters.py    # 책임·handoff 계약 (의존성 없음)
├── classifier/llama_guard.py        # 분류: Llama Guard 3
├── dialogue/nemo_guardrails_client.py  # 대화 정책: NeMo Guardrails
└── pipeline/real_integration.py     # 두 어댑터 호출 + 결과 JSON 저장
```

## 파일·디렉터리 역할

| 경로 | 역할 |
| --- | --- |
| `src/main.py` | 진입점. `compare`(기본)·`real --prompt` 서브커맨드로 하위 패키지를 호출 |
| `src/contracts/adapters.py` | 실제 SDK와 독립적인 입력·출력·handoff·비책임 계약 |
| `src/classifier/llama_guard.py` | Transformers로 Llama Guard 3를 실제 로드·생성·분류하는 어댑터 |
| `src/dialogue/nemo_guardrails_client.py` | `RailsConfig`·`LLMRails.generate()`를 호출하는 실제 NeMo 어댑터 |
| `src/pipeline/real_integration.py` | 두 실제 어댑터를 순서대로 호출하고 JSON 결과를 저장 |
| `nemo_config/config.yml` | Ollama 기반 NeMo Guardrails 모델·입출력 레일 설정 |
| `requirements-llm.txt` | Python 3.12용 선택적 Transformers·Torch·NeMo 의존성 |
| `slides/s00-tech-spec.svg` | 2단계 필수 기술과 선택적 실제 모델 연동 범위 |
| `slides/s01-guard-models.svg` | 두 Guardrails 적용 흐름 개요 |
| `slides/s02-guardrail-theory.svg` | 안전성 분류와 대화 정책의 이론 비교 |
| `slides/s03-adapters-source.svg` | `adapters.py` 소스와 선택 기준 |
| `slides/s06-runtime-choice.svg` | 기본 Ollama·심화 Transformers 실행 경로 선택 |
| `slides/s07-guardrail-checklist.svg` | 기술 적용 복습 체크리스트 |
| `slides/s08-summary.svg` | 2단계 핵심 요약과 질문 |
| `slides/s04-llama-guard-detail.svg` | Llama Guard의 분류 책임·입력·출력·정책 변환 상세 |
| `slides/s05-nemo-guardrails-detail.svg` | NeMo Guardrails의 대화 흐름·주제·응답 경로 상세 |
| `slides/readme.md` | 슬라이드 순서·제목·산출물 목록 |

`adapters.py` 자체는 역할 비교용 계약으로 유지하지만, 실제 호출은 같은 2단계 폴더의
세 어댑터 파일에서 수행한다. 따라서 “2단계에서는 방법론만 설명하고 호출은 뒤로
미룬다”는 구조가 아니라, 2단계에서 실제 호출 경로와 책임 경계를 함께 확인할 수 있다.
