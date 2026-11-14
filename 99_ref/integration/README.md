# 점층 통합 실습

`01~06` 폴더는 독립 학습용으로 유지한다. 이 디렉터리는 단계별 코드를 수정하거나 공통 import로 묶지 않고, 실제 서비스가 단계적으로 확장되는 모습을 별도 실행 트랙으로 제공한다.

```text
01 architecture
  → 02 model policy
  → 03 guardrail
  → 04 risk
  → 05 monitoring
  → 06 reporting
```

각 단계는 이전 단계의 결과 계약을 읽지만, 다음 규칙을 따른다.

- 단계 폴더의 소스코드는 직접 수정하지 않는다.
- 단계 폴더끼리 공통 Python import를 만들지 않는다.
- 결과 파일은 `integration/results/`에 별도로 저장한다.
- 계약 변경은 `contracts/`의 버전을 올린다.
- 독립 단계 실습은 이전 단계 결과 없이도 실행 가능하게 유지한다.

## 실행

```bash
python3 integration/run.py --stage 01
python3 integration/run.py --stage 02
python3 integration/run.py --stage 03
python3 integration/run.py --stage 04
python3 integration/run.py --stage 05
python3 integration/run.py --stage 06
```

전체 점층 흐름은 다음처럼 실행한다.

```bash
python3 integration/run.py --all
```

실제 2단계 Guardrail 호출은 5단계 API를 통해 수행한다. 서버를 실행한 뒤 다음 요청을 보내면 NeMo Guardrails와 Llama Guard의 결과가 SQLite 이벤트로 저장된다.

```bash
uvicorn api:app --app-dir 05_security_dashboard_alerts/src --port 8000
curl -X POST http://127.0.0.1:8000/guardrail/chat \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-only-key' \
  -d '{"message":"안전한 업무 요청입니다"}'
```

이 경로는 `integration/guardrail_service.py`에서 `03_policy_blocking_output_filtering`의 입력·출력 정책과 2단계 실제 provider를 연결한다. provider 초기화 또는 호출이 실패하면 API는 `503`을 반환한다.

통합 결과는 `integration/results/`에 기록되며, 기존 `results/`의 독립 실습 결과와 분리된다.

## 파일·디렉터리 역할

| 경로 | 역할 |
| --- | --- |
| `run.py` | `--stage 01~06` 또는 `--all`로 점층 통합을 실행하는 진입점 |
| `guardrail_service.py` | 실제 Guardrail provider와 정책 엔진을 연결하는 서비스 계층 |
| `results/` | 통합 트랙만 사용하는 결과 저장소 |
| `results/README.md` | 통합 결과 파일별 역할 |
| `README.md` | 독립 트랙과 통합 트랙의 운영 규칙·실행 방법 |
