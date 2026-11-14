# 3단계 · 정책 기반 차단 및 출력 검열 구현

## 이론적 배경

모델 기반 안전성 판단만으로는 조직별 허용 범위, 데이터 분류, 도구 권한 같은 서비스 고유 정책을 충분히 표현하기 어렵다. 반대로 키워드만으로 모든 위험을 판단하면 표현 변형과 문맥을 놓칠 수 있다.

그래서 운영 시스템은 설명 가능한 정책 규칙과 출력 후처리를 함께 사용한다. 입력 단계에서는 위험한 요청의 모델 전달을 줄이고, 출력 단계에서는 모델이 생성한 민감정보가 사용자에게 노출되는 것을 막는 다중 방어 구조를 만든다.

## 학습 목표

허용·거부 규칙으로 입력을 차단하고, 모델 출력을 검열·마스킹한다.

## 핵심 내용

- 규칙 ID, 패턴, 사유, 위험 등급, 판정 결과
- 프롬프트 인젝션·비밀정보 탈취·위험한 도구 요청 차단
- 이메일·전화번호·API 키·비밀 키워드 마스킹
- 차단 응답, 검토 응답, 안전한 대체 응답

## 이론 보강

정책은 단순 키워드 목록이 아니라 `규칙 ID → 탐지 조건 → 사유 → 위험 등급 → 결정`의 구조로 관리해야 한다. 이렇게 해야 정책 변경 이력과 차단 근거를 추적할 수 있다.

출력 검열은 탐지와 대응을 분리한다. 탐지기는 민감한 필드를 찾고, 대응기는 마스킹·재생성·검토 중 하나를 선택한다. API 키와 개인 식별정보는 로그와 사용자 화면 모두에서 원문이 남지 않도록 주의한다.

정책 기반 휴리스틱은 빠르고 설명 가능하지만 표현 변형과 문맥을 모두 이해하지 못한다. 운영 전에는 정상·위험·경계 사례로 오탐과 미탐을 측정해야 한다.

## 실습

```bash
python3 -m unittest discover -s tests -v
python3 03_policy_blocking_output_filtering/src/guardrail.py
```

`src/policy.py`와 `src/guardrail.py`의 입력 차단·출력 검열 흐름을 실행한다. 직접 실행하면 `results/step03-guardrail-result.json`이 생성되고, 다음 명령으로 결과를 확인할 수 있다.

```bash
python3 -m json.tool results/step03-guardrail-result.json
```

## 산출물

- 정책 규칙표
- 입력 차단 테스트 결과
- 출력 마스킹 전·후 비교
- `results/step03-guardrail-result.json` 다음 단계 전달 파일

## 단계 간 연결

[← 2단계](../02_llama_guard_nemo_guardrails/readme.md) · [4단계 →](../04_risk_rating_system/readme.md) · [전체 과정](../readme.md)

2단계의 적용 전략을 정책 규칙으로 구현하고, `result_payload()` 또는 `write_result()`로 판정 결과를 `results/step03-guardrail-result.json`에 남긴다. 4단계는 이 파일을 읽어 이벤트로 변환한다.

## 완료 기준

정상 요청은 허용하고 위험 요청은 차단하며, 민감한 출력은 원문을 노출하지 않고 마스킹할 수 있다.

## 파일·디렉터리 역할

| 경로 | 역할 |
| --- | --- |
| `src/policy.py` | 정책 규칙 로딩·입력 탐지·위험 등급 계산 |
| `src/guardrail.py` | 입력 차단·출력 마스킹·결과 JSON 생성 |
| `policy-rules.json` | 규칙 ID·정규식·사유·위험·판정 설정 |
| `slides/s00-tech-spec.svg` | 3단계 기술·정책 파일·결과 규약 사양 |
| `slides/s01-policy-filtering.svg` | 정책 차단과 출력 검열 전체 흐름 |
| `slides/s02-policy-theory.svg` | 판정·마스킹 이론 |
| `slides/s03-policy-source.svg` | `policy.py`·`guardrail.py` 소스 설명 |
| `slides/s04-policy-checklist.svg` | 정책·검열 실습 체크리스트 |
| `slides/s05-summary.svg` | 3단계 핵심 요약과 질문 |
| `slides/readme.md` | 슬라이드 순서·제목·산출물 목록 |
