"""Build the review portfolio with explicit evidence scope and clickable links."""
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf'; OUT.mkdir(parents=True,exist_ok=True)
fontroot=Path('C:/Windows/Fonts') if Path('C:/Windows/Fonts').exists() else Path('/mnt/c/Windows/Fonts')
pdfmetrics.registerFont(TTFont('KR',str(fontroot/'malgun.ttf')))
pdfmetrics.registerFont(TTFont('KRB',str(fontroot/'malgunbd.ttf')))
pdfmetrics.registerFontFamily('KR',normal='KR',bold='KRB')
green=colors.HexColor('#3e701a'); dark=colors.HexColor('#14241d')
styles={k:ParagraphStyle(k,fontName='KRB' if k in ('title','h','sub') else 'KR',fontSize=size,leading=leading,textColor=green if k=='sub' else dark,spaceAfter=12,wordWrap='CJK') for k,size,leading in [('title',32,44),('h',22,32),('sub',12,19),('body',10,18),('small',8,13)]}
story=[]
def p(s,k='body'):return Paragraph(s,styles[k])
def add(*rows):story.extend(rows)
def table(rows,widths):
    t=Table([[p(str(x),'small') for x in row] for row in rows],colWidths=widths)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf4e8')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),('LINEBELOW',(0,0),(-1,-1),.5,colors.HexColor('#dbe3dc'))]))
    return t
def link(url,label):return f'<link href="{url}" color="#3e701a">{label}</link>'
repo='https://github.com/kkokkiyo/skillforge'
add(p('NVIDIA KOREA AGENTIC AI HACKATHON 2026','sub'),Spacer(1,32),p('SkillForge','title'),p('정책이 바뀌면,<br/>자동화의 근거도 다시 검증합니다.','h'),p('에이전트의 실행 경험을 재사용 가능한 절차로 바꾸고,<br/>변경 영향을 확인한 뒤 검증된 버전만 다시 활성화합니다.'),Spacer(1,26),table([['실행 경험','변경 영향','운영 판단'],['출처 기반 6단계 절차','정책 전후 42쌍 비교','재검증 후 명시적 활성화']],[158,158,159]),Spacer(1,22),p('팀 TraceMakers (임시 팀명)','sub'),p(link(repo,'GitHub: github.com/kkokkiyo/skillforge')),p(link(repo+'/blob/main/output/video/SkillForge-evidence-walkthrough.mp4','3분 데모 영상 - 저장된 실행 증거의 시각화')),p('2026-09-26 / 합성 커머스 전액 환불 데모','small'),p('실제 고객정보·결제 없음. 팀명은 실제 신청 팀명과 일치시켜 제출하세요. 주최측 Skill API 세부 요구의 충족 여부는 답변 대기 중입니다.','small'),PageBreak())
add(p('01 / PROBLEM & DIFFERENTIATION','sub'),p('“한 번 성공한 자동화”를<br/>계속 사용해도 될까요?','h'),p('대상: 반품·환불 자동화를 관리하는 커머스 운영팀과 개발자. 정책과 승인 기준이 바뀌면 기존 실행 절차의 영향을 다시 판단해야 합니다. 매번 추론하는 에이전트는 지연과 실패를 반복하고, 고정 워크플로는 변경 근거와 검증을 사람이 추적해야 합니다.'),table([['접근','강점','추가로 필요한 운영 판단'],['매 요청 에이전트','상황별 도구 결정','실행 결과와 권한의 일관성'],['수동 워크플로','예측 가능한 재사용','변경 영향과 재검증 관리'],['SkillForge','실행 출처와 검증을 연결','정책 전후 비교 → 새 버전 승격']],[95,155,225]),p('차별화의 중심','sub'),p('메모리·사람 승인·로그 자체를 새로운 기술이라고 주장하지 않습니다. 실행 출처, 변경 전후 사례, 독립 DB 판정, 불변 버전 계보를 하나의 운영 흐름으로 연결합니다. 운영자는 어떤 요청의 처리 방식이 왜 달라졌는지 확인하고 활성화를 결정할 수 있습니다.'),p('구현 방법','sub'),p('요청·완료 이벤트를 읽어 타입이 있는 참조 표를 구성합니다. 이전 단계의 실제 quote 값과 provenance를 교차 검사하고, 같은 순서·참조를 가진 독립 성공 기록 5건 이상을 묶습니다. 관측 단계에서 JSON 절차를 만들며 수동 템플릿 함수를 호출하지 않습니다. 지원 범위는 명시된 6단계 환불 절차입니다.'),p('선행 연구와 한계','sub'),p(link('https://arxiv.org/abs/2409.07429','Agent Workflow Memory')+'는 경험 기반 워크플로 재사용의 선행 연구입니다. 고객 인터뷰, 운영 도입, 유지보수 시간 절감률, 범용 작업 확장성은 아직 검증하지 않았습니다.','small'),PageBreak())
add(p('02 / DEMO & ENGINEERING','sub'),p('35만원 환불의 판단이<br/>달라지는 순간','h'),table([['단계','화면에서 확인할 근거'],['1. 기록 → 후보','새 NVIDIA 성공 기록 5건, 공개 도구 이벤트, 입력·이전 출력 참조'],['2. 검증 → 활성화','분리된 Validation 30건 + 현재 정책 경계 6건, artifact/report hash'],['3. 변경 미리보기','승인 기준 50만원 → 30만원. 35만원 환불: 자동 처리 → 승인 필요'],['4. 영향 확인','42쌍의 합성 비교 중 5개 판정 변화. 위험 변경 0, 정상 오차단 0'],['5. 적용 → 재승격','이전 절차 STALE. 부모 hash·원래 출처를 보존한 새 후보 재검증'],['6. 승인 후 처리','새 35만원 주문 승인 대기 → 단회 승인 → 1회 환불']],[112,363]),p('검증과 데이터 경계','sub'),p('미리보기는 격리 SQLite에서 실행되어 운영 주문·환불·승인을 바꾸지 않습니다. 적용 시 기본 정책 해시를 다시 확인하여 오래된 미리보기가 새 정책을 덮어쓰지 못합니다. 후보 생성은 중복 요청에도 같은 버전을 돌려주며 활성화는 별도 행동입니다.'),p('공통 업무 게이트웨이','sub'),p('모델과 절차 모두 소유권·반품 수령·최신 정책·금액·견적을 검사합니다. 승인 소비와 환불은 한 거래로 확정합니다. 쓰기 후 결과가 불확실하면 추가 쓰기를 보류합니다. 정책 변화 시 이전 절차 전체를 무효화하며 선택적 안전성이나 실제 결제의 exactly-once를 주장하지 않습니다.'),PageBreak())
add(p('03 / NVIDIA & EVIDENCE','sub'),p('실제 통합과 측정 범위를<br/>분리해 공개합니다.','h'),table([['기술','사용 및 검증'],['Nemotron','nvidia/nemotron-3-super-120b-a12b hosted tool calling. 신규 discovery 5건 성공; 정책 변경 후 승인 대기 확인.'],['NeMo Agent Toolkit 1.9.0','동일 bounded agent를 custom workflow 플러그인에서 실행한 live 증거 보존. NAT 기본 ReAct 구현이라는 주장 아님.'],['MCP SDK 2.2.0','6개 도구 stdio 서버. 실제 client/server 환불·소유권 차단 검증.'],['서비스','Python 3.12 / FastAPI / Pydantic / SQLite / React / TypeScript / Vite / SSE.']],[125,350]),p('검증 결과','sub'),p('회귀 테스트 57건 통과. 정책 전후 42쌍은 모의 executor 실험이며 84회의 실제 모델 호출이 아닙니다. 신규 live 비교의 변경 전 실행은 HTTP 500으로 실패하여 원본을 보존하고 별도 재실행했습니다. 전체 시도와 결과는 공개 evidence에서 확인할 수 있습니다.'),p('이전 버전의 성능 pilot','sub'),p('각 군 40건·1회: Nemotron 34/40, 수동·생성 절차 각각 40/40. 모델 호출 244/0/0, unsafe commit 모두 0. in-memory executor 비교로 자연어 router·운영자 대기·실결제는 제외했습니다. 새 정책 기능의 성능 측정과 혼합하지 않습니다.','small'),p('재현과 공개 근거','sub'),p(link(repo+'/blob/main/artifacts/policy-change-evidence.json','정책 변경 원본 증거')+'<br/>'+link(repo+'/blob/main/docs/reviews/policy-change-release.md','최신 검증 보고서')+'<br/>'+link(repo+'/blob/main/README.md','설치·실행 가이드')+'<br/>'+link('https://docs.nvidia.com/nemo/agent-toolkit/latest/','NVIDIA Agent Toolkit 공식 문서'),'small'),p('미확인 항목','sub'),p('NemoClaw/OpenShell OS 격리는 미검증입니다. 대회 신청서의 Skill API 명칭과 필수 증빙 기준은 주최측 확인 중입니다. 일반 inference 성공만으로 해당 요건 충족을 단정하지 않습니다.','small'))
def footer(c,doc):
    c.setFont('KR',8);c.setFillColor(colors.HexColor('#5e6c64'));c.drawString(60,32,'SkillForge / 2026-09-26 / Synthetic refund demo');c.drawRightString(535,32,str(doc.page))
path=OUT/'NVIDIA 해커톤_TraceMakers_SkillForge.pdf'
SimpleDocTemplate(str(path),pagesize=(595.28,841.89),leftMargin=60,rightMargin=60,topMargin=52,bottomMargin=62,title='SkillForge - 정책 변화에 대응하는 검증 가능한 자동화',author='TraceMakers').build(story,onFirstPage=footer,onLaterPages=footer)
print(path)
