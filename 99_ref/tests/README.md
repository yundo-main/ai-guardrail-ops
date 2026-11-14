# 공통 테스트

| 파일 | 참조 단계 | 역할 |
| --- | --- | --- |
| `test_guardrail.py` | 03단계 단독 | 입력 차단·출력 마스킹 회귀 테스트 |
| `test_step05-monitoring.py` | 05단계 단독 | 모니터링 집계·Critical 알림 회귀 테스트 |
| `test_z_api.py` | 05단계 단독 | FastAPI 인증·이벤트 등록·지표·Critical 알림·acknowledgement 테스트 |
| `test_contracts.py` | 루트 JSON 파일 | 결과 JSON의 추적 필드와 정책 규칙 규약 테스트 |
| `test_architecture.py` | 01단계 단독 | 1단계 최소 파이프라인의 정상·차단·검토 분기 테스트 |
| `test_real_guard_adapters.py` | 02단계 단독 | Llama Guard 파서·NeMo 설정 경계 테스트 |

각 테스트 파일은 한 단계 `src/` 만 `sys.path`에 추가한다.
N단계 테스트에서 N+1 이후 단계 폴더를 참조하지 않으므로 단계별 디렉터리를 복사해도 독립 실행이 가능하다.

실행:

```bash
python3 -m unittest discover -s tests -v
```
