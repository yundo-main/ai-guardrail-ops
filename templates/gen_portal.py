#!/usr/bin/env python3
"""templates/gen_portal.py — 01~06 단계 폴더에 index.html 포털 페이지를 생성한다.

사용법:  python3 templates/gen_portal.py   (프로젝트 루트에서 실행)

각 페이지는 file:// 로 서버 없이 동작하며, readme.md/slides/readme.md 를
HTML로 변환해 페이지에 내장한다(뷰어 스냅샷). 원본 수정 후 재생성 필요.
"""
import html as H
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {'__pycache__', '.git', 'node_modules', '.DS_Store'}
STEP_DIRS = ['01_guardrail_concept_architecture', '02_llama_guard_nemo_guardrails',
             '03_policy_blocking_output_filtering', '04_risk_rating_system',
             '05_security_dashboard_alerts', '06_operations_report_integrated_lab']

# ---------------- markdown → html ----------------
def _inline(t):
    t = H.escape(t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    return t

def md2html(md):
    out, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith('```'):
            i += 1; code = []
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code.append(lines[i]); i += 1
            out.append('<pre><code>' + H.escape('\n'.join(code)) + '</code></pre>'); i += 1; continue
        if not s: i += 1; continue
        if s.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(set(c) <= set('-: ') for c in cells): rows.append(cells)
                i += 1
            body = ''
            for ri, r in enumerate(rows):
                tag = 'th' if ri == 0 else 'td'
                body += '<tr>' + ''.join(f'<{tag}>{_inline(c)}</{tag}>' for c in r) + '</tr>'
            out.append('<table>' + body + '</table>'); continue
        m = re.match(r'^(#{1,4})\s+(.*)', s)
        if m:
            lv = min(len(m.group(1)) + 1, 4)
            out.append(f'<h{lv}>{_inline(m.group(2))}</h{lv}>'); i += 1; continue
        if s.startswith('>'):
            i += 1; q = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                q.append(lines[i].strip().lstrip('>').strip()); i += 1
            out.append('<blockquote style="border-left:3px solid var(--accent);margin:.6rem 0;padding:.3rem .9rem;color:var(--muted);background:#f8fafc;border-radius:0 8px 8px 0">' + _inline(' '.join(q)) + '</blockquote>'); continue
        if re.match(r'^[-*]\s+', s) or re.match(r'^\d+\.\s+', s):
            ordered = bool(re.match(r'^\d+\.', s)); items = []
            while i < len(lines):
                t = lines[i].strip()
                mm = re.match(r'^[-*]\s+(.*)', t) or re.match(r'^\d+\.\s+(.*)', t)
                if not mm: break
                items.append(_inline(mm.group(1))); i += 1
            tag = 'ol' if ordered else 'ul'
            out.append(f'<{tag}>' + ''.join(f'<li>{x}</li>' for x in items) + f'</{tag}>'); continue
        out.append(f'<p>{_inline(s)}</p>'); i += 1
    return '\n'.join(out)

# ---------------- readme parsing ----------------
def section(md, name):
    m = re.search(r'##\s+' + re.escape(name) + r'\s*\n(.*?)(?=\n##\s|\Z)', md, re.S)
    return m.group(1).strip() if m else ''

def first_para(md_text):
    for blk in md_text.split('\n\n'):
        blk = blk.strip()
        if blk and not blk.startswith(('#', '-', '|', '```', '>', '*')):
            return re.sub(r'\s+', ' ', blk)[:220]
    return ''

def bullets(md_text):
    return [re.sub(r'^[-*]\s+', '', l.strip()) for l in md_text.splitlines() if re.match(r'^[-*]\s+', l.strip())]

# ---------------- directory tree ----------------
def build_tree(root: Path):
    def kids(dirpath: Path, depth: int):
        try:
            entries = sorted(os.listdir(dirpath), key=lambda x: (not os.path.isdir(dirpath / x), x.lower()))
        except OSError:
            return ''
        out = []
        dirs = [e for e in entries if os.path.isdir(dirpath / e) and e not in SKIP and not e.startswith('.')]
        files = [e for e in entries if os.path.isfile(dirpath / e) and e not in SKIP and not e.startswith('.')]
        for f in files:
            out.append(f'<div class="dtl">{H.escape(f)}</div>')
        for d in dirs:
            inner = kids(dirpath / d, depth + 1)
            op = ' open' if depth == 0 else ''
            out.append(f'<details class="dt"{op}><summary>{H.escape(d)}/</summary><div class="dt-kids">{inner}</div></details>')
        return ''.join(out)
    return f'<div class="dtree"><div class="dtn">{H.escape(root.name)}/</div>{kids(root, 0)}</div>'

# ---------------- slides ----------------
def slide_cards(proj: Path):
    sdir = proj / 'slides'
    if not sdir.is_dir():
        return ''
    titles = {}
    sreadme = sdir / 'readme.md'
    if sreadme.exists():
        for m in re.finditer(r'\|\s*(s\d+[^|]*)\|\s*([^|]+)\|', sreadme.read_text()):
            titles[m.group(1).strip()] = m.group(2).strip()
    cards = []
    for f in sorted(sdir.glob('s*.svg')):
        key = f.stem
        if key.startswith('s00'):
            title = '기술 사양 (참고용)'
        else:
            title = titles.get(key) or titles.get(key.split('-')[0]) or key.replace('-', ' ')
        cards.append(
            f'<div class="dgi"><div class="dgi-head"><span class="dgi-t">{H.escape(key)} · {H.escape(title)}</span><span class="badge">SVG</span></div>'
            f'<img src="slides/{f.name}" alt="{H.escape(title)}" loading="lazy"></div>')
    return '\n'.join(cards)

# ---------------- run ----------------
def try_run(proj: Path, cmd: str, timeout=25):
    try:
        r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout + r.stderr).strip()
        return out[:4000] if out else ''
    except Exception:
        return ''

# ---------------- project configs ----------------
PROJECTS = [
    dict(dir='01_guardrail_concept_architecture', h1='Guardrail 개념과 아키텍처', day='STEP 01', cat='GUARDRAIL CONCEPT ARCHITECTURE',
         gloss=[('Guardrail','모델 호출 전후에 정책을 집행하는 통제 계층 — 모델 자체가 아닌 운영 계층'),('입력 가드레일','모델 호출 전 요청의 목적·권한·위험 신호를 검사'),('출력 가드레일','모델 응답이 공개되어도 되는지 호출 후 다시 검사'),('출력 검열','모델 생성 결과에서 민감정보·유해성을 걸러내는 출력 단계 검사'),('통제 계층','모델 앞뒤에 정책 집행 지점을 두는 운영 구조'),('정책 집행 지점','규칙을 실제로 적용하는 코드 위치 — 입력·출력 각각에 존재'),('프롬프트 인젝션','지시문을 조작해 모델의 원래 목적을 우회하는 공격'),('유해 요청','폭력·불법·유해 콘텐츠 생성이나 조장을 요구하는 입력'),('PII','개인식별정보 — 이름·연락처·주민번호 등 개인을 식별할 수 있는 정보'),('민감정보','외부 노출 시 피해가 되는 정보 — PII·비밀키·내부 데이터 등'),('허용·차단·검토','판정 결과 3단계 — 통과·거부·사람 확인 필요'),('보안 이벤트','차단·검토·허용 판정의 기록 단위 — 운영의 기본 데이터'),('규칙 ID','발동된 정책 규칙을 추적하기 위한 식별자'),('위험 등급','이벤트의 심각도를 Low~Critical으로 분류한 라벨'),('이벤트 ID','보안 이벤트를 고유하게 식별하는 ID'),('PipelineStage','파이프라인 각 단계를 추상화한 실행 단위 (architecture.py)'),('더미 모델','실제 LLM 없이 결정적 응답을 반환하는 연습용 모델'),('관제','이벤트 기록·대응 연결 — 파이프라인의 항상 실행되는 마지막 단계'),('운영 로그','판정 결과·규칙 ID·위험 등급·이벤트 ID를 우선 기록하는 로그'),('안전한 기본값','통제 계층이 실패해도 안전하게 동작하도록 하는 기본 반환값'),('접근권한','원문 로그 열람을 제한하는 권한 설정'),('보존기간','로그·원문 데이터를 보관하는 기간 정책')],
         run=True, run_cmd='python3 01_guardrail_concept_architecture/src/architecture.py'),
    dict(dir='02_llama_guard_nemo_guardrails', h1='Llama Guard·NeMo Guardrails', day='STEP 02', cat='LLAMA GUARD · NEMO GUARDRAILS',
         gloss=[('Llama Guard','요청·응답의 안전성 범주를 분류하는 안전성 판정 모델'),('NeMo Guardrails','대화 주제·절차·응답 경로를 정책으로 제어하는 대화 흐름 프레임워크'),('안전성 분류','입력/출력이 허용 범주인지 판정하는 분류 작업'),('분류기(classifier)','위험성을 범주로 판정하는 역할 — 최종 결정은 내리지 않음'),('위험 카테고리','폭력·혐오·개인정보 등 Llama Guard의 분류 범주'),('대화 정책','허용된 주제와 응답 경로를 정의하는 규칙 집합'),('대화 흐름 제어','대화가 특정 주제·절차를 벗어나지 않도록 하는 제어'),('주제 이탈','허용된 주제를 벗어난 발화 — NeMo가 복귀·검토로 전환'),('응답 경로','모델이 답변을 생성하는 경로 — 정책이 허용 범위를 결정'),('탐지 결과','분류기가 산출하는 위험 판정값 — 정책 엔진의 입력값'),('최종 결정','차단·검토·허용의 실제 판정 — 애플리케이션 정책 계층의 역할'),('어댑터','외부 기술을 내부 계약으로 연결하는 계층 — src/contracts/adapters.py'),('receives→produces→handoff_to','어댑터 계약 3요소 — 입력·출력·다음 단계'),('not_responsible_for','각 기술이 대신하지 않는 책임을 명시하는 필드'),('Ollama','로컬 LLM 실행 백엔드 — 학습용 기본 경로'),('Transformers','HuggingFace 모델 직접 로드 경로 — 심화 옵션'),('PyTorch','Transformers 경로의 딥러닝 런타임'),('모델 가중치','학습된 파라미터 — Llama Guard 직접 실행 시 추가 관리 대상'),('GPU 메모리','Transformers 경로에서 모델 로드에 필요한 자원'),('custom adapter','NeMo에서 전용 분류 모델을 연결하는 어댑터'),('오탐','정상 입력을 위험으로 잘못 판정하는 오류'),('정책 우선순위','중복 차단 방지를 위한 적용 순서 규칙'),('사람 검토','자동 판정이 어려운 사건을 담당자가 확인하는 경로'),('llama_guard.py','Llama Guard 실제 호출 모듈 (classifier/)'),('nemo_guardrails_client.py','NeMo Guardrails 호출 모듈 (dialogue/)'),('real_integration.py','실제 모델 호출 파이프라인 (pipeline/)')],
         run=True, run_cmd='python3 02_llama_guard_nemo_guardrails/src/main.py'),
    dict(dir='03_policy_blocking_output_filtering', h1='정책 기반 차단과 출력 검열', day='STEP 03', cat='POLICY · BLOCKING · OUTPUT FILTERING',
         gloss=[('정책 규칙','허용·차단·검토를 결정하는 조건 집합'),('policy-rules.json','규칙 ID·패턴·위험 등급을 정의한 정책 파일'),('규칙 ID','정책 규칙의 고유 식별자 — 변경 이력·차단 근거 추적용'),('탐지 조건','규칙이 발동하는 패턴·키워드 조건'),('사유(reason)','규칙 발동 이유 — 설명 가능한 차단 근거'),('차단(block)','정책 위반 요청을 모델 호출 전에 거부'),('출력 검열','모델 응답에서 PII·비밀정보를 마스킹'),('마스킹','민감 문자열을 [EMAIL_REDACTED] 등으로 치환'),('탐지기','민감한 필드를 찾는 탐지 모듈'),('대응기','탐지 결과에 마스킹·재생성·검토 중 하나를 적용'),('차단 응답','정책 위반 시 사용자에게 반환하는 거부 메시지'),('검토 응답','자동 판정이 어려울 때 사람 확인을 요청하는 응답'),('안전한 대체 응답','위험 요청 대신 제공하는 무해한 대체 답변'),('이메일·전화번호','마스킹 대상 PII 유형'),('API 키','마스킹 대상 비밀정보 — api_key=[API_KEY_REDACTED] 형태'),('비밀 키워드','내부 비밀·자격증명을 나타내는 민감 단어'),('오탐','정상 요청을 위험으로 잘못 차단'),('미탐','위험 요청을 놓치는 오류'),('경계 사례','정상·위험 사이의 애매한 입력 — 테스트에 활용'),('다중 방어','입력 차단 + 출력 검열을 함께 두는 방어 구조'),('설명 가능한 정책','규칙 ID→조건→사유→등급→결정 구조로 관리되는 정책'),('policy.py','정책 규칙 로드·판정 모듈'),('guardrail.py','입력 차단·출력 검열 실행 엔트리포인트'),('result_payload','판정 결과를 JSON 계약으로 변환하는 함수'),('step03-guardrail-result.json','3단계 결과 — 4단계로 전달되는 파일')],
         run=True, run_cmd='python3 03_policy_blocking_output_filtering/src/guardrail.py'),
    dict(dir='04_risk_rating_system', h1='위험 등급 체계', day='STEP 04', cat='RISK RATING · SECURITY EVENT',
         gloss=[('위험 등급','영향·악용 가능성·노출 범위로 정한 대응 강도 단계'),('Low','추세 관찰 수준의 최저 위험 등급'),('Medium','일상 모니터링 대상의 중간 위험 등급'),('High','담당자 검토·차단을 요구하는 높은 위험 등급'),('Critical','즉시 알림·에스컬레이션이 필요한 최고 위험 등급'),('영향 범위','사고 발생 시 피해가 미치는 범위'),('악용 가능성','공격자가 실제로 악용할 수 있는 정도'),('민감도','노출된 데이터·시스템의 민감 정도'),('긴급도','대응이 필요한 시간적 급박함'),('대응 계약','등급이 올라갈수록 강한 조치를 연결하는 규칙'),('에스컬레이션','상위 담당자·팀으로 사건을 escalation하는 절차'),('즉시 알림','Critical 등급에 발송되는 긴급 통지'),('사후 분석','사건 종료 후 원인·대응을 분석하는 절후 활동'),('SecurityEvent','위험 판정을 운영 이벤트로 변환한 기록 구조'),('이벤트 ID·시각·카테고리·판정·상세','이벤트에 남겨야 할 필수 필드'),('행동 기준','등급을 숫자가 아닌 구체적 조치로 정의한 기준'),('등급 변경 기록','변경자·시각·사유를 별도 기록 — 원본 덮어쓰기 금지'),('risk.py','3축 점수→등급 분류·이벤트 변환 모듈'),('classify_risk','영향·악용·노출 점수를 Low~Critical으로 변환'),('event_from_guardrail_file','3단계 결과 JSON을 SecurityEvent로 변환'),('write_event_result','이벤트를 step04-security-event.json으로 저장'),('step04-security-event.json','4단계 결과 — 5단계 API 전달 파일')],
         run=True, run_cmd='PYTHONPATH=04_risk_rating_system/src python3 04_risk_rating_system/src/risk.py'),
    dict(dir='05_security_dashboard_alerts', h1='보안 대시보드와 알림', day='STEP 05', cat='DASHBOARD · ALERTS · OBSERVABILITY',
         gloss=[('대시보드','보안 이벤트·지표를 시각화한 운영 화면 (/dashboard)'),('지표(metrics)','이벤트 수·차단율·등급 분포 등 집계값'),('차단율','전체 요청 대비 차단된 비율 — 정책 효과 지표'),('위험 등급 분포','Low~Critical 등급별 이벤트 비율'),('카테고리별 집중도','공격 유형별 이벤트 분포'),('미대응 건수','아직 처리되지 않은 이벤트 수'),('Critical 알림','최고 위험 이벤트의 즉시 통지 payload'),('알림 피로','과도한 알림으로 담당자가 무뎌지는 현상'),('중복 알림 억제','같은 사건의 반복 통지를 줄이는 장치'),('담당자 라우팅','알림을 적절한 담당자에게 전달하는 규칙'),('재시도','알림 전송 실패 시 재전송 로직'),('acknowledgement','운영자가 이벤트를 확인했음을 기록하는 상태'),('FastAPI','대시보드·API를 제공하는 웹 프레임워크'),('SQLite','이벤트를 저장하는 경량 DB (security_events.db)'),('EventStore','이벤트 기록·조회·집계를 담당하는 저장소'),('PostgreSQL·이벤트 스트림','운영 환경용 저장소 교체 옵션'),('API 키','요청 헤더 X-API-Key 인증 — 기본값 dev-only-key'),('GUARDRAIL_API_KEY','배포 전 변경해야 하는 환경변수 키'),('dashboard_metrics()','이벤트를 집계해 지표를 만드는 함수'),('critical_alert()','Critical 이벤트에만 payload를 생성하는 함수'),('POST /events','보안 이벤트 등록 API'),('GET /metrics','대시보드 지표 조회 API'),('GET /alerts/critical','Critical 알림 목록 API'),('step05-metrics.json','5단계 지표 결과 — 6단계 리포트 입력')],
         run=False, run_cmd='python3 -m pip install -r 05_security_dashboard_alerts/requirements.txt && uvicorn api:app --app-dir 05_security_dashboard_alerts/src --port 8000'),
    dict(dir='06_operations_report_integrated_lab', h1='운영 리포트와 통합 실습', day='STEP 06', cat='OPERATIONS REPORT · INTEGRATED LAB',
         gloss=[('운영 리포트','지표·이벤트·개선안을 정리한 주간/월간 보고서'),('주간 리포트','최근 사건·즉시 조치를 중심으로 작성하는 보고서'),('월간 리포트','추세·정책 효과·반복 오탐·미대응 누적을 분석하는 보고서'),('피드백 루프','탐지·차단 결과를 다음 개선 작업으로 연결하는 순환'),('기준선','기간별 비교의 기준이 되는 지표 값'),('변화량','전 기간 대비 지표 증감'),('개선 과제','리포트 지표에서 도출한 다음 단계 조치'),('탐지 건수·차단 건수·검토 건수','리포트의 기본 집계 지표'),('정책 변경 전후 비교','정책 수정이 지표에 미친 효과 분석'),('미대응 이슈','리포트에 포함해야 할 미처리 사건 목록'),('app.py','전체 파이프라인을 실행하는 통합 엔트리포인트'),('llm.py','로컬 Ollama /api/chat을 호출하는 LLM 모듈'),('USE_LLM','Ollama 실호출 활성화 환경변수 (기본 더미 응답)'),('더미 응답','결정적 가짜 응답 — 실제 LLM 없이 파이프라인 검증'),('이벤트 ID 연결','한 요청의 입력→판정→이벤트 전체 경로 추적'),('trace_id','요청부터 이벤트까지 상관관계를 잇는 ID'),('step06-report.json','최종 통합 실행 결과 파일'),('통합 실습','정책→분류→검열→관제→리포트를 하나로 연결하는 실습')],
         run=True, run_cmd='python3 06_operations_report_integrated_lab/src/app.py'),
]

# ---------------- page generation ----------------
def gen(cfg):
    proj = ROOT / cfg['dir']
    md = (proj / 'readme.md').read_text()
    title_full = re.match(r'#\s*(.+)', md).group(1).strip()
    h1 = cfg.get('h1') or title_full
    eyebrow = f"{cfg['day']} · {cfg['cat']}"
    goal = first_para(section(md, '학습 목표'))
    core = bullets(section(md, '핵심 내용'))
    chips = core[:5] if core else ['단계 1', '단계 2']
    chips_html = ''.join(f'<span>{H.escape(c)}</span>' for c in chips)

    practice_txt = first_para(section(md, '실습'))
    link_txt = first_para(section(md, '단계 간 연결'))
    cards = f'''<div class="grid">
<div class="card card-link" onclick="show('tab-overview')"><span class="ico">🧠</span><h3>이론 <span class="go">→</span></h3><p>{H.escape(goal)}</p></div>
<div class="card card-link" onclick="show('tab-practice')"><span class="ico">🛡️</span><h3>실습 <span class="go">→</span></h3><p>{H.escape(practice_txt)}</p></div>
<div class="card card-link" onclick="show('tab-overview')"><span class="ico">📊</span><h3>단계 연결 <span class="go">→</span></h3><p>{H.escape(link_txt)}</p></div>
</div>'''

    # 개요: 01과 동일한 섹션 구성
    secs = re.findall(r'(?ms)^##\s+(.+?)\s*\n(.*?)(?=^##\s|\Z)', md)
    sec_map = {n.strip(): b.strip() for n, b in secs}
    skip_secs = {'실습', '소스 구조', '파일·디렉터리 역할', '단계 간 연결', '산출물', '완료 기준'}
    canon = ['이론적 배경', '학습 목표', '핵심 내용', '이론 보강']
    ordered = [n for n in canon if n in sec_map]
    ordered += [n for n, _ in secs if n.strip() not in canon + list(skip_secs) and n.strip() not in ordered]
    ov_parts = []
    for n in ordered:
        ov_parts.append(f'<h3>{H.escape(n)}</h3>' + md2html(sec_map[n]))
    if '산출물' in sec_map or '완료 기준' in sec_map:
        ov_parts.append('<h3>산출물 · 완료 기준</h3>'
                        + md2html(sec_map.get('산출물', ''))
                        + md2html(sec_map.get('완료 기준', '')))
    overview_html = '\n'.join(ov_parts)
    link_note = first_para(sec_map.get('단계 간 연결', ''))

    # 용어: 한글 자음순 그룹 + 인덱스 바
    CHO = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'
    def cho(t):
        for ch in t:
            o = ord(ch)
            if 0xAC00 <= o <= 0xD7A3:
                return CHO[(o - 0xAC00) // 588]
            if ch.isalpha():
                return '#'
        return '#'
    groups = {}
    for k, v in cfg['gloss']:
        groups.setdefault(cho(k), []).append((k, v))
    order = [c for c in CHO if c in groups] + (['#'] if '#' in groups else [])
    # 인덱스 바: 전체 자음을 ㄱ~ㅎ 순서로 표시, 용어 없는 글자는 비활성
    gidx_items = ['<a href="#gloss-top" style="min-width:2.2rem">전체</a>']
    for c in CHO:
        if c in groups:
            gidx_items.append(f'<a href="#g-{c}">{c}</a>')
        else:
            gidx_items.append(f'<span class="gidx-off">{c}</span>')
    if '#' in groups:
        gidx_items.append('<a href="#g-#">#</a>')
    else:
        gidx_items.append('<span class="gidx-off">#</span>')
    gidx = '<div class="gidx">' + ''.join(gidx_items) + '</div>'
    gloss_html = gidx + '<div id="gloss-top"></div>'
    for c in order:
        gloss_html += f'<h3 class="ggroup" id="g-{c}">{c}</h3><table>'
        gloss_html += '<tr><th style="width:180px">용어</th><th>설명</th></tr>'
        gloss_html += ''.join(f'<tr><td style="width:180px"><b>{H.escape(k)}</b></td><td>{H.escape(v)}</td></tr>'
                              for k, v in sorted(groups[c], key=lambda x: x[0]))
        gloss_html += '</table>'
    slides_html = slide_cards(proj)
    if not slides_html:
        slides_html = '<p class="sub">슬라이드 없음</p>'

    # practice (실행 방법 + 결과 예시 + 실습 단계 + 추가 명령 + 소스 구조)
    cmds = re.findall(r'```(?:bash|sh|text)?\n(.*?)```', md, re.S)
    cmd_texts = [c.strip() for c in cmds if c.strip() and not c.strip().startswith('text')]
    first_cmd = ''
    for c in cmd_texts:
        for line in c.splitlines():
            if re.match(r'^(python3?|uvicorn|ollama|cd\s|source\s|PYTHONPATH=|pip3?\s|\.\/|sh\s)', line.strip()):
                first_cmd = line.strip(); break
        if first_cmd: break
    if not first_cmd and cmd_texts:
        first_cmd = cmd_texts[0].splitlines()[0].strip()
    primary_cmd = cfg.get('run_cmd') or first_cmd
    copy_cmd_js = ''
    if primary_cmd:
        practice_cmds = (f'<div class="codebox"><pre><code>{H.escape(primary_cmd)}</code></pre>'
                         f'<button class="copybtn" id="copyCmd">복사</button></div>'
                         f'\n<p class="sub" id="copyMsg" style="margin-top:.4rem"></p>')
        copy_cmd_js = ("const COPY_CMD=" + repr(primary_cmd) + ";"
                       "$('copyCmd').onclick=()=>{navigator.clipboard.writeText(COPY_CMD).then(()=>{$('copyMsg').textContent='복사됨 — 터미널에 붙여넣기 (⌘V)'}).catch(()=>{$('copyMsg').textContent='복사 실패 — 직접 입력'})};")
    else:
        practice_cmds = '<p class="sub">실행 명령은 readme.md 참조</p>'
    extra = [c for c in cmd_texts if c.splitlines()[0].strip() != primary_cmd.splitlines()[0].strip()]
    extra_html = ''
    if extra:
        extra_html = '<h3>추가 명령</h3>' + '\n'.join(
            '<div class="codebox"><pre><code>' + H.escape(c) + '</code></pre></div>' for c in extra)
    prac = section(md, '실습')
    steps = [re.sub(r'^\d+\.\s*', '', l.strip()) for l in prac.splitlines() if re.match(r'^\d+\.\s*', l.strip())]
    steps_html = ''
    if steps:
        steps_html = '<h3>실습 단계</h3><ol>' + ''.join(f'<li>{_inline(x)}</li>' for x in steps) + '</ol>'
    src_struct = section(md, '소스 구조')
    tree_block = re.search(r'```text\n(.*?)```', src_struct, re.S)
    src_html = ''
    if tree_block:
        src_html += '<div class="codebox"><pre><code>' + H.escape(tree_block.group(1).strip()) + '</code></pre></div>'
    files_sec = section(md, '파일·디렉터리 역할')
    if files_sec:
        src_html += '<h3>파일·디렉터리 역할</h3>' + md2html(files_sec)

    run_html = ''
    if cfg.get('run') and cfg.get('run_cmd'):
        out = try_run(proj, cfg['run_cmd'])
        if out:
            run_html = f'<h3>실행 결과 예시</h3><pre><code>{H.escape(out)}</code></pre>'

    # embedded readmes for viewer
    md_fw = md2html(md)
    md_map = "'readme.md':'md-readme'"
    extra_divs = f'<div id="md-readme" hidden>{md_fw}</div>'
    sreadme = proj / 'slides' / 'readme.md'
    if sreadme.exists():
        extra_divs += f'<div id="md-slides" hidden>{md2html(sreadme.read_text())}</div>'
        md_map += ",'slides/readme.md':'md-slides'"

    tree_html = build_tree(proj)

    # 전체 단계 인덱스 내비 (1~6)
    stepidx = '<div class="stepidx"><span class="lbl">단계</span><a href="../index.html">⌂</a>' + ''.join(
        f'<a href="../{d}/index.html"{" class=\"cur\"" if d == cfg["dir"] else ""}>{i + 1}</a>'
        for i, d in enumerate(STEP_DIRS)) + '</div>'

    page = f'''<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{H.escape(h1)}</title>
<style>{STYLE}</style></head><body>
<div class="wrap">
<nav class="topnav">
<a class="brand" href="#top">📘 {H.escape(proj.name)}</a>
<a href="#tab-overview">개요</a><a href="#tab-gloss">용어</a><a href="#tab-slides">슬라이드</a><a href="#tab-practice">실습</a><a href="#tab-help">도움말</a>
</nav>
{stepidx}
<div class="hero" id="top">
<div class="eyebrow">{H.escape(eyebrow)}</div>
<h1>{H.escape(h1)}</h1>
<p class="sub">{H.escape(goal)}</p>
<div class="steps">
{chips_html}
</div>
</div>
{cards}
<section class="ltab on" id="tab-overview">
<div class="ltitle">개요 — {H.escape(cfg['day'])} 학습 내용</div>
{overview_html}
<h3>프로젝트 구조</h3>
{tree_html}
{f'<p class="sub" style="margin-top:.8rem">단계 간 연결: {H.escape(link_note)}</p>' if link_note else ''}
<p class="sub" style="margin-top:.4rem">상위 프로젝트: <a href="../10_ai_guardrail_ops_framework/readme.md">10 통합 프레임워크 readme →</a> (도움말 탭에서 뷰어로도 열람 가능)</p>
</section>
<section class="ltab" id="tab-gloss" hidden>
<div class="ltitle">용어 정리 — {H.escape(cfg['day'])} 핵심 개념</div>
{gloss_html}
</section>
<section class="ltab" id="tab-slides" hidden>
<div class="ltitle">슬라이드 — 발표 자료 (SVG)</div>
{slides_html}
</section>
<section class="ltab" id="tab-practice" hidden>
<div class="ltitle">실습 — {H.escape(cfg['day'])} 실행</div>
<p>아래 명령은 <b>터미널</b>에서 프로젝트 루트(<code>ai-guardrails-ops/</code>) 기준으로 실행합니다.</p>
<h3>실행 방법</h3>
<p class="sub">복사 버튼으로 명령을 가져간 뒤 터미널에 붙여넣기 (⌘V) 하세요.</p>
{practice_cmds}
{run_html}
{steps_html}
{extra_html}
<h3>소스 구조</h3>
{src_html}
<p class="sub" style="margin-top:.8rem">※ 브라우저에서는 실행할 수 없습니다 — 명령을 복사해 터미널에 붙여넣으세요.</p>
</section>
<section class="ltab" id="tab-help" hidden>
<div class="ltitle">도움말 — 페이지 사용법</div>
<h3>탭 전환</h3>
<p>상단 내비게이션을 클릭하면 해당 패널이 표시됩니다. 주소창 해시(<code>#tab-slides</code> 등)로 특정 탭에 바로 이동할 수 있습니다.</p>
<h3>SVG 뷰어</h3>
<ul>
<li>슬라이드 탭의 <b>SVG 이미지를 클릭</b>하면 팝업 뷰어로 확대 표시됩니다</li>
<li>뷰어에서 <code>‹</code> <code>›</code> 버튼 또는 <code>←</code> <code>→</code> 키로 이동합니다</li>
<li><code>ESC</code> · <code>✕ 닫기</code> · 어두운 배경 클릭으로 닫습니다</li>
</ul>
<h3>readme 문서</h3>
<p>아래 버튼으로 마크다운 문서를 뷰어 팝업으로 확인할 수 있습니다.</p>
<p><button class="dgbtn" id="openReadme" style="font-size:.85rem;padding:.45rem 1rem">readme.md 열기</button>
<button class="dgbtn" id="openSlidesReadme" style="font-size:.85rem;padding:.45rem 1rem;margin-left:.5rem">slides/readme.md 열기</button></p>
<h3>단축키</h3>
<table>
<tr><th>키</th><th>동작</th></tr>
<tr><td><code>←</code> <code>→</code></td><td>뷰어에서 이전/다음 슬라이드</td></tr>
<tr><td><code>ESC</code></td><td>뷰어 닫기</td></tr>
</table>
<h3>참고</h3>
<ul>
<li>이 페이지는 <b>서버 없이</b> 동작합니다 — <code>index.html</code>을 브라우저로 바로 열면 됩니다</li>
<li>뷰어의 readme 내용은 페이지 생성 시점의 스냅샷입니다 — 원본이 수정되면 페이지 재생성이 필요합니다</li>
</ul>
</section>
<footer>
<span>{H.escape(proj.name)} · {H.escape(cfg['day'])} 학습 자료</span>
</footer>
</div>
{extra_divs}
<div id="viewer" hidden><div class="vbox"><div class="vhead"><span id="vtitle"></span><span style="display:flex;gap:.8rem;align-items:center"><a id="vopen" href="#" target="_blank">새 탭에서 열기</a><button class="dgbtn" id="vclose">✕ 닫기</button></span></div><div class="vbody" id="vbody"></div><button class="vside" id="vsprev" hidden title="이전 슬라이드">‹</button><button class="vside" id="vsnext" hidden title="다음 슬라이드">›</button></div></div>
<script>{SCRIPT.replace("const MD={'readme.md':'md-readme'}; /* TODO: '경로/readme.md':'md-xxx' 등록 */", "const MD={" + md_map + "};")}\n{copy_cmd_js}</script>
</body></html>'''
    (proj / 'index.html').write_text(page)
    return len(page)

# ---------------- CSS / JS ----------------
STYLE = open(ROOT / 'templates' / 'project-portal.html', encoding='utf-8').read().split('<style>')[1].split('</style>')[0]
_tmpl = open(ROOT / 'templates' / 'project-portal.html', encoding='utf-8').read()
SCRIPT = _tmpl.split('<script>')[1].split('</script>')[0]

if __name__ == '__main__':
    for cfg in PROJECTS:
        n = gen(cfg)
        print(cfg['dir'], n, 'bytes')
