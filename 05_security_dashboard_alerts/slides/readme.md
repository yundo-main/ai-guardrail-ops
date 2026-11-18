# 5단계 슬라이드

| 순서 | 슬라이드 주제 | 산출물 |
| --- | --- | --- |
| s01 | 보안 대시보드 및 알림 구축 | 이벤트·지표·Critical 알림 연결 |
| s02 | 대시보드와 알림 이론 | 운영 지표와 긴급 알림의 역할 |
| s03 | 대시보드와 알림 소스코드 | 집계 함수·API·Critical 필터 |
| s04 | 실습 순서 | 서버 실행·이벤트·리포트·Discord 명령 |
| s05 | Discord 웹훅 알림 설정 | 웹훅 URL 발급·discord.py 입력·발송 확인 |
| s06 | 서버 실행과 이벤트 테스트 | uvicorn 실행·이벤트 등록·대시보드·Discord 확인 |
| s07 | 실행 흐름 Flow 도식 | api.py 엔드포인트→store·monitoring·discord·guardrail_service 호출 순서 (1920×1080) |
| s08 | 복습 체크리스트 | 지표·알림·보안 확인 |
| s09 | 핵심 요약과 실습 질문 | 학습 내용과 완료 확인 |

기술 사양: [s00-tech-spec.svg](s00-tech-spec.svg)

실제 슬라이드: [s01-dashboard-alerts.svg](s01-dashboard-alerts.svg), [s02-dashboard-theory.svg](s02-dashboard-theory.svg), [s03-dashboard-source.svg](s03-dashboard-source.svg), [s04-practice-order.svg](s04-practice-order.svg), [s05-discord-setup.svg](s05-discord-setup.svg), [s06-server-event-test.svg](s06-server-event-test.svg), [s07-flow.svg](s07-flow.svg), [s08-dashboard-checklist.svg](s08-dashboard-checklist.svg), [s09-summary.svg](s09-summary.svg)

`s00-tech-spec.svg`는 FastAPI·SQLite·API Key의 참고 기술 사양이다. `s01`~`s09`는 발표용 SVG이며, `s07-flow.svg`는 소스코드 실행 흐름 Flow 도식(1920×1080)이다., `s03-dashboard-source.svg`는 `api.py`, `store.py`, `monitoring.py`, `report.py`의 역할을 설명한다.
