# 보조 실행 스크립트

| 파일 | 역할 |
| --- | --- |
| `run_pipeline.py` | 3단계 결과 생성 → 4단계 이벤트 생성 → 6단계 통합 리포트의 빠른 파일 기반 실행 |

점층 통합 전체 실행은 이 파일이 아니라 `integration/run.py`를 사용한다.

```bash
python3 scripts/run_pipeline.py
```
