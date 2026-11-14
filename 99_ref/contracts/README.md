# 결과 계약

`contracts/`는 실행 코드가 아니라 단계별 결과 형식을 검증하는 기준이다.

각 단계 소스는 서로 import하지 않는다. 단계별 결과는 각 폴더에 복사·생성할 수 있고, 통합 트랙은 이 계약과 결과 파일을 이용해 다음 단계로 진행한다.

| 계약 | 사용 단계 | 핵심 필드 |
| --- | --- | --- |
| `guardrail-result-v1.json` | 3단계 → 4단계 | 결정·위험·이벤트 ID·추적 ID |
| `security-event-v1.json` | 4단계 → 5단계 | 이벤트·위험·상태·정책 버전 |
| `metrics-v1.json` | 5단계 → 6단계 | 전체·차단·검토·비율·미대응 |

계약을 변경할 때는 기존 버전을 삭제하지 않고 `v2`를 추가한다.

## 파일 역할

| 파일 | 역할 |
| --- | --- |
| `guardrail-result-v1.json` | 3단계 정책·검열 결과의 최소 필드 예시 |
| `security-event-v1.json` | 4단계 위험 이벤트와 5단계 API 입력 필드 예시 |
| `metrics-v1.json` | 5단계 지표와 6단계 리포트 입력 필드 예시 |
| `README.md` | 계약 사용 원칙과 버전 관리 규칙 |

---

## 품질 평가 기준 (evaluation)

단계별 기능 테스트와 별도로 통합 서비스의 품질을 평가한다.

### 평가 범주

| 범주 | 설명 |
| --- | --- |
| `benign` | 정상 요청 |
| `prompt_injection` | 지시 우회 |
| `secret_exfiltration` | 비밀정보 요청 |
| `pii` | 개인정보 포함 출력 |
| `borderline` | 오탐 가능 경계 사례 |
| `tool_abuse` | 위험 도구 사용 요청 |

### 측정 지표

- 허용·차단·검토 비율
- 차단율 / 오탐률 / 미탐률
- 민감정보 검출률
- LLM 지연 시간
- fallback 발생률
- Critical 알림 누락률

### 추가 계획 디렉터리 구성

| 경로 | 역할 |
| --- | --- |
| `datasets/benign/` | 정상 요청·정상 응답 사례 |
| `datasets/prompt_injection/` | 지시 우회 사례 |
| `datasets/pii/` | 개인정보·민감정보 출력 사례 |
| `datasets/borderline/` | 허용과 차단 경계 사례 |
| `datasets/tool_abuse/` | 위험 도구 호출 사례 |
| `run_eval.py` | 평가 데이터셋 실행기 |
| `metrics.py` | 차단율·오탐률·미탐률·fallback 비율 계산기 |

현재는 평가 기준과 계약만 정의했으며, 실제 데이터셋과 자동 평가기는 다음 단계에서 추가한다.
