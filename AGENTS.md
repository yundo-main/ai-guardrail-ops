# AGENTS.md — AI Guardrails Ops 작업 규칙

이 저장소에서 작업하는 모든 에이전트(Devin, Codex, Claude 등)는 아래 규칙을 따른다.

## 필수: 작업 로그 기록

**모든 작업은 완료 시 `100_teacher/logs/YYYY-MM-DD.md`에 기록한다.** 로그를 남기지 않은 작업은 미완료로 간주한다.

- 파일이 없으면 새로 생성하고, 있으면 같은 날짜 파일에 `## 주제` 섹션을 추가한다.
- 기록 항목: 변경 내용(파일 경로 포함), 이유, 검증 결과(테스트·명령 실행 여부), 미처리/남은 과제.
- 과거 로그의 옛 경로 표기는 이력 보존을 위해 수정하지 않는다.
- `.gitignore`에 의해 git 추적은 안 되지만, 파일 자체는 반드시 작성한다.

로그 형식 예시:

```markdown
# 2026-11-15 개발 로그

## 포털 템플릿 갱신
- `100_teacher/templates/gen_portal.py`, `100_teacher/templates/project-portal.html`에 단계 인덱스 `0` 링크와 통합 프레임워크 카드 반영
- 검증: `python3 100_teacher/templates/gen_portal.py` 재생성, JS `node --check` 통과
- 미처리: 없음
```

## 명명 규칙

- 학습 단계 표기는 **`N단계`**(한글) / **`step0N`**(파일·식별자) — `일차`, `day`, `7-N` 표기 사용 금지
- `00_intro/`는 과정 개요(0단계)·결과 규약·용어집, `01_`~`06_`은 각 학습 단계, `10_ai_guardrail_ops_framework/`는 통합 프레임워크 — `99_ref/`는 폐기됨(과거 공통 참조 영역)
- 결과 JSON은 `stepNN-*.json` 명명, `source_stage` 값도 `stepNN`

## 포털 페이지 규칙

- 단계 포털(`0N_*/index.html`)은 `100_teacher/templates/gen_portal.py`로 생성 — **직접 편집 금지**, `PROJECTS` 설정 수정 후 `python3 100_teacher/templates/gen_portal.py` 재실행
- 루트 `index.html`은 `100_teacher/templates/gen_index.py`로 생성 — **직접 편집 금지**, `STEPS` 설정 수정 후 `python3 100_teacher/templates/gen_index.py` 재실행
- `00_intro/index.html`은 `100_teacher/templates/gen_intro.py`로 생성 — `python3 100_teacher/templates/gen_intro.py` 재실행
- `00_intro/glossary/index.html` + `00_intro/glossary.md`는 `100_teacher/templates/gen_glossary.py`로 생성 — `python3 100_teacher/templates/gen_glossary.py` 재실행 (용어 소스: `gen_portal.py`의 `PROJECTS.gloss`)
- `10_ai_guardrail_ops_framework/index.html`은 `100_teacher/templates/gen_docs.py`로 생성 — `python3 100_teacher/templates/gen_docs.py` 재실행
- 템플릿 변경은 `100_teacher/templates/project-portal.html`(단계·인트로 포털 공용 CSS/JS), `100_teacher/templates/index-portal.html`(루트 인덱스)에 반영
- `100_teacher/`는 `.gitignore`로 git 추적 제외 — 강사 전용(템플릿·교사용 가이드 포함, 로컬 전용)
- 포털은 `file://`로 서버 없이 동작해야 한다

## 검증

- 변경 후 관련 검증 실행: 단계별 `tests/` 디렉터리가 있으면 `python3 -m unittest discover -s <단계>/tests -v` 실행, `python3 -m compileall` 또는 직접 실행으로 문법 확인
- SVG 변경 시 `xmllint --noout <file>.svg` 검증
- 포털 재생성 후 JS 문법 `node --check` 확인 권장

## SVG 슬라이드

- SVG 슬라이드·도식 작성 시 `100_teacher/templates/svg-metaprompt.md`의 프롬프트와 검수 기준을 따른다 (로컬 전용, git 제외)
- 완료 후 `xmllint --noout` XML 검증 + 렌더링 육안 확인

## 기타

- `.env` 등 비밀 파일 커밋 금지 (`.gitignore` 준수)
- 단계별 `src/`는 독립·중복 유지 — 단계 간 연결은 각 단계 `results/` JSON과 5단계 API로만 (규약 문서는 `00_intro/results.md`·`00_intro/contracts/`)
