# index.html 생성 프롬프트

## 프롬프트

```text
너는 AI 가드레일 학습 자료의 SVG 인덱스 페이지(index.html)를 작성하는 작성자다.
아래 기준을 따라 index.html을 처음부터 작성하라.

[프로젝트 구조]
- 루트: ai_guardrails_ops/
- 단계 폴더: 01_guardrail_concept_architecture/ ~ 06_operations_report_integrated_lab/
- 각 단계 슬라이드: {단계폴더}/slides/sNN-이름.svg
- 공통 지원 폴더: 99_ref/ (contracts, docs, integration, logs, results, scripts, tests)
- 프로젝트 전체 관계도 SVG: 00_intro/slides/00~04-*.svg
- 진입점: 루트의 index.html (python3 -m http.server 8000 또는 직접 열기)

[디자인 기준]
- 라이트 모드 고정 (color-scheme: light)
- 팔레트: --bg:#f8fafc / --panel:#ffffff / --ink:#122033 / --muted:#516174 / --line:#c9d5e1 / --accent:#1769aa
- 글꼴: -apple-system, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif
- 외부 CDN·폰트·스크립트 사용 금지

[페이지 구성 — 위에서 아래 순서]
1. <head>: charset, viewport, title, <style> (CSS 변수·컴포넌트 정의)
2. 헤더: eyebrow(AI GUARDRAILS OPS · SVG INDEX) + h1(실습 SVG 슬라이드 인덱스) + 부제
3. 빠른 링크 nav: readme.md / 99_ref/integration/README.md / 2단계 소스 관계도
4. 프로젝트 전체 관계도 섹션 (h2 + 카드 그리드)
   - 00_intro/slides/00-course-flow.svg       · 전체 과정 흐름
   - 00_intro/slides/01-practice-guide.svg    · 실습 가이드
   - 00_intro/slides/02-technology-stack.svg  · 기술 스택
   - 00_intro/slides/03-integration-flow.svg  · 점층 통합 흐름
   - 00_intro/slides/04-result-check.svg      · 결과 확인
5. 단계별 섹션: <details> + draw() JS 함수로 카드 자동 생성
   - 01~02 단계: details[open] (기본 펼침)
   - 03~06 단계: 기본 접힘
6. 하단 안내: python3 -m http.server 8000 / http://127.0.0.1:8000/index.html
7. draw() 함수 정의: </main> 직전 <script> 블록 1개만

[카드 1개 구조]
<article class="card">
  <a class="thumb" href="{경로}" target="_blank">
    <img loading="lazy" src="{경로}" alt="{설명}">
  </a>
  <div class="body">
    <h3>{그룹} · {NN}</h3>
    <p>{파일명}</p>
    <a href="{경로}" target="_blank">SVG 열기</a>
    <a href="{경로}" download>다운로드</a>
  </div>
</article>

[draw() 함수 시그니처]
draw(dir, files, group)
- dir: 단계 폴더 경로 (예: '01_guardrail_concept_architecture')
- files: 슬라이드 파일명 배열 (예: ['s00-tech-spec.svg', ...])
- group: 카드 제목 접두어 (예: '아키텍처')
- 경로 조합: dir + '/slides/' + file

[단계별 draw() 호출]
draw('01_guardrail_concept_architecture',
  ['s00-tech-spec.svg','s01-guardrail-flow.svg','s02-guardrail-architecture.svg',
   's03-threats-and-controls.svg','s04-architecture-source.svg',
   's05-architecture-checklist.svg','s06-summary.svg'], '아키텍처');

draw('02_llama_guard_nemo_guardrails',
  ['s00-tech-spec.svg','s01-guard-models.svg','s02-guardrail-theory.svg',
   's03-adapters-source.svg','s04-llama-guard-detail.svg',
   's05-nemo-guardrails-detail.svg','s06-runtime-choice.svg',
   's07-guardrail-checklist.svg','s08-summary.svg'], 'Guardrails');

draw('03_policy_blocking_output_filtering',
  ['s00-tech-spec.svg','s01-policy-filtering.svg','s02-policy-theory.svg',
   's03-policy-source.svg','s04-policy-checklist.svg','s05-summary.svg'], '정책');

draw('04_risk_rating_system',
  ['s00-tech-spec.svg','s01-risk-rating.svg','s02-risk-theory.svg',
   's03-risk-source.svg','s04-risk-checklist.svg','s05-summary.svg'], '위험');

draw('05_security_dashboard_alerts',
  ['s00-tech-spec.svg','s01-dashboard-alerts.svg','s02-dashboard-theory.svg',
   's03-dashboard-source.svg','s04-dashboard-checklist.svg','s05-summary.svg'], '관제');

draw('06_operations_report_integrated_lab',
  ['s00-tech-spec.svg','s01-integrated-report.svg','s02-report-theory.svg',
   's03-integrated-source.svg','s04-report-checklist.svg','s05-summary.svg'], '리포트');

[출력 전 자체 점검]
1) draw() 함수가 1개만 정의되어 있는가
2) 모든 경로가 루트 기준 상대 경로인가 (99_ref/... 또는 0N_.../...)
3) 라이트 모드 고정이 적용되어 있는가 (color-scheme: light)
4) details[open] 설정이 01~02 단계에만 적용되어 있는가
5) 외부 CDN·폰트·스크립트가 없는가
```

## 수정 시 규칙

| 작업 | 조치 |
| --- | --- |
| 단계 슬라이드 추가·삭제 | 해당 draw() 배열만 갱신 |
| 새 단계 추가 | `<details>` 블록 + draw() 호출 세트로 추가 |
| 전체 관계도 SVG 추가 | 수동 `<article>` 카드도 함께 추가 |
| 슬라이드 파일명 | sNN-이름.svg 형식 (소문자·하이픈) 유지 |
| 팔레트·글꼴·모드 | 변경하지 않는다 |
