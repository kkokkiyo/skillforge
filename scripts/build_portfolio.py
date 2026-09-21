from pathlib import Path
import json
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_LEFT
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf';OUT.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(TTFont('Korean','C:/Windows/Fonts/malgun.ttf'))
pdfmetrics.registerFont(TTFont('KoreanBold','C:/Windows/Fonts/malgunbd.ttf'))
pdfmetrics.registerFontFamily('Korean',normal='Korean',bold='KoreanBold')
GREEN=colors.HexColor('#407118'); DARK=colors.HexColor('#14241d'); GREY=colors.HexColor('#5e6c64')
styles={
 'eyebrow':ParagraphStyle('eyebrow',fontName='KoreanBold',fontSize=9,textColor=GREEN,spaceAfter=13),
 'title':ParagraphStyle('title',fontName='KoreanBold',fontSize=34,leading=44,textColor=DARK,spaceAfter=18,wordWrap='CJK'),
 'h':ParagraphStyle('h',fontName='KoreanBold',fontSize=21,leading=30,textColor=DARK,spaceAfter=18,wordWrap='CJK'),
 'sub':ParagraphStyle('sub',fontName='KoreanBold',fontSize=12,leading=19,textColor=DARK,spaceBefore=17,spaceAfter=8,wordWrap='CJK'),
 'body':ParagraphStyle('body',fontName='Korean',fontSize=10,leading=17,textColor=DARK,spaceAfter=11,wordWrap='CJK'),
 'small':ParagraphStyle('small',fontName='Korean',fontSize=8,leading=13,textColor=GREY,spaceAfter=8,wordWrap='CJK')}
def p(text,kind='body'):return Paragraph(text,styles[kind])
def table(rows,widths):
 t=Table([[p(str(c),'small') for c in r] for r in rows],colWidths=widths,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf4e8')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9),('LINEBELOW',(0,0),(-1,-1),.5,colors.HexColor('#dbe3dc'))]))
 return t
story=[]
def add(*items):story.extend(items)
def page(num,title):add(p(f'SKILLFORGE / {num:02d}','eyebrow'),p(title,'h'))
add(p('2026 NVIDIA KOREA AGENTIC AI HACKATHON','eyebrow'),Spacer(1,28),p('SkillForge','title'),p('실행 기록에서 배우는<br/>안전한 업무 자동화','h'),p('에이전트가 성공한 절차를 발견하고,<br/>검증한 뒤 다시 실행합니다.'),Spacer(1,30))
add(table([['실제 업무 도구','독립 live 성공 기록','분리 검증 사례'],['6개','5건','30건']],[155,155,165]),Spacer(1,22),p('팀 TraceMakers','sub'),p('공개 저장소: github.com/kkokkiyo/skillforge'),p('제출 초안 / 2026-09-21','sub'),p('GitHub 저장소는 공개 상태입니다. 영상 URL과 Skill API 요건 확인 후 최종본으로 사용하세요.','small'),p('범위: 합성 커머스 주문의 전액 환불. 실제 결제·실제 고객정보를 사용하지 않습니다.','small'),PageBreak())
page(2,'반복 추론을 줄여도,<br/>업무 검증은 남아야 합니다.')
add(p('대상 사용자','sub'),p('반품·환불 요청을 처리하고 AI 에이전트의 실행 결과를 검토하는 커머스 운영팀과 자동화 개발자입니다. 고객 인터뷰나 실제 운영 도입을 완료했다고 주장하지 않습니다.'),p('해결하는 문제','sub'),p('같은 유형의 환불 요청도 소유권, 반품 수령, 잔여 금액, 정책과 승인 조건을 확인해야 합니다. 매번 LLM이 전체 절차를 추론하면 반복 호출과 지연이 생기고, 모든 예외를 사람이 고정 절차로 관리하면 유지보수 부담이 커집니다.'),table([['접근','장점','남는 과제'],['매 요청 ReAct','새 상황에 대응','반복 추론과 실행 증거 관리'],['사람이 작성한 워크플로','예측 가능한 실행','절차 작성과 정책 변경 관리'],['SkillForge','실행 근거에서 후보 유도','도메인 계약과 별도 검증 필요']],[95,155,225]),p('우리의 초점','sub'),p('범용 에이전트나 임의 코드 생성기가 아닙니다. 환불 도메인의 제한된 도구 계약을 이용해 실행 기록을 데이터 전용 DSL로 바꾸고, 별도 검증과 운영자 활성화를 거친 경로만 재사용합니다.'),p('경험 기반 workflow 재사용은 선행 연구가 있습니다. 기여는 변경 업무의 정책 경계, 출처 추적, 독립 상태 검증을 한 흐름으로 연결한 구현입니다.','small'),PageBreak())
page(3,'기록부터 재사용까지,<br/>근거가 이어지는 흐름')
for title,body in [('01 실제 실행과 기록','Nemotron이 주문 → 반품 → 정책 → 견적 → 환불 → 검증 도구를 호출합니다. 모델명, 공개 도구 호출, 인자 출처, 사용량과 결과를 기록합니다.'),('02 후보 유도','동일 정책·도구 버전에서 서로 다른 주문의 성공 기록 5건 이상을 묶습니다. 전체 도구 순서와 provenance가 일치해야 하며, 과거 ID 대신 입력·이전 출력 참조를 사용합니다.'),('03 분리된 검증과 활성화','생성에 사용하지 않은 Validation 30건을 독립 DB에서 실행합니다. 보고서와 artifact hash를 확인한 운영자만 후보를 활성화합니다.'),('04 새 요청에서 재사용','활성 절차가 현재 버전과 일치하면 같은 gateway를 통해 실행합니다. 정책 변경 시 STALE로 제외합니다. 자연어 주문이 모호하면 확인을 요청합니다.')]:add(p(title,'sub'),p(body))
add(p('콘솔','sub'),p('React 운영 콘솔은 SSE 진행 타임라인, source trace와 DSL, 고액 승인·재개, Mock/Live 표시, JSONL export와 평가표를 제공합니다.'),p('안전 경계','sub'),p('서버 측 최신 상태 재검사, 원자적 승인 소비·환불 거래, 중복 환불 차단을 적용합니다. 쓰기 후 오류는 NEEDS_RECONCILIATION으로 표시합니다. 로컬 모의 DB의 보장이며 실제 결제의 exactly-once를 보장하지 않습니다.'),PageBreak())
page(4,'NVIDIA 통합과<br/>확인 가능한 실행 증거')
add(table([['기술','실제 사용 및 검증 범위'],['Nemotron','nvidia/nemotron-3-super-120b-a12b / hosted tool calling. 실제 환불, 6개 도구, DB oracle 성공.'],['NeMo Agent Toolkit 1.9.0','custom workflow 플러그인에서 동일 bounded agent를 실행. NAT CLI live 실행 성공. NAT 자체 ReAct 구현을 사용했다고 주장하지 않음.'],['MCP SDK 2.2.0','stdio 서버 도구 6개. 실제 MCP client로 환불 commit과 타 고객 거절 확인.'],['앱 / 데이터','Python 3.12, FastAPI, Pydantic, SQLite, React, TypeScript, Vite. 원자적 거래와 trace 저장.']],[132,343]),p('대표 live 실행','sub'),p('run-5f318a0e32d69499690a: SUCCEEDED, 모델 호출 시도 10회, 업무 도구 6회, 보고된 토큰 6,917, 약 8.4초. 단일 실행 예시이며 평균 성능이 아닙니다.'),p('NAT 실행','sub'),p('run-5536713bb6bb718c1b4c: SUCCEEDED, 모델 호출 6회, 업무 도구 6회, 보고된 토큰 6,581. 원본은 artifacts/nat-live-evidence.json에 보존합니다.'),p('명확하게 남기는 미검증 항목','sub'),p('NemoClaw/OpenShell OS 격리는 검증하지 않았습니다. 신청서의 “Skill API”가 요구하는 정확한 API와 증빙 범위도 아직 확인되지 않았습니다. 일반 NVIDIA inference 성공만으로 제출 요건 충족을 선언하지 않습니다.'),PageBreak())
page(5,'측정 결과와 제출 전 확인')
add(p('현재 확보한 기능 검증','sub'),p('자동 회귀 49건 통과. 별도 안전 행렬 36/36건도 통과했습니다. HTTP 전체 흐름에서 Discovery 30건, Validation 30건, 고액 승인·재개, A/B/C 120회와 정책 변경 무효화를 확인했습니다.'),p('실제 비교: 결과와 한계를 함께','sub'),table([['경로','기대 판정 일치','Unsafe commit'],['A: Nemotron ReAct','34 / 40','0'],['B: 수동 워크플로','40 / 40','0'],['C: 생성 워크플로','40 / 40','0']],[220,135,120]),p('평가 ID: eval-dc5a773edccd641d. 각 군 40건, 1회 반복. A는 HTTP 500 5건과 견적 참조 오류 1건으로 실패했습니다. 모델 호출 A 244회 / B·C 0회. in-memory SQLite의 executor 비교이며 자연어 라우팅·실결제·운영자 대기 비용은 제외했습니다. 초기 429 다발 평가도 보존합니다.','small'),p('재현','sub'),p('README의 설치 명령 후 로컬 콘솔을 실행합니다. 키 없는 Mock 모드와 본인 NVIDIA 키를 쓰는 Live 모드를 구분합니다. artifacts/eval의 manifest·runs.jsonl·summary를 확인하세요.'),p('공식 참고 자료','sub'),p('<link href="https://github.com/NVDLI/NemoClawDLI" color="#407118">NVIDIA DLI 교육 원문</link><br/><link href="https://docs.nvidia.com/nemo/agent-toolkit/latest/" color="#407118">NeMo Agent Toolkit 공식 문서</link><br/><link href="https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b/modelcard" color="#407118">Nemotron 모델 카드</link><br/><link href="https://arxiv.org/abs/2409.07429" color="#407118">Agent Workflow Memory (선행 연구)</link>','small'),p('남은 제출 게이트','sub'),p('GitHub 공개 저장소: github.com/kkokkiyo/skillforge. 영상 URL과 Skill API 요구 확인이 남아 있습니다. 한국어 10문장 검사는 9건 통과했으며 서버 오류를 포함해 보고합니다. 이 PDF는 링크 미완성 초안이며 제출 완료 문서가 아닙니다.','small'))
def footer(c,doc):
 c.setStrokeColor(colors.HexColor('#dbe3dc'));c.line(48,48,547,48);c.setFont('Korean',8);c.setFillColor(GREY);c.drawString(48,32,'TraceMakers · SkillForge / 제출 초안');c.drawRightString(547,32,str(doc.page))
file=OUT/'NVIDIA 해커톤_TraceMakers_SkillForge.pdf'
SimpleDocTemplate(str(file),pagesize=(595.28,841.89),leftMargin=60,rightMargin=60,topMargin=58,bottomMargin=68,title='SkillForge - 실행 기록에서 배우는 안전한 업무 자동화',author='TraceMakers').build(story,onFirstPage=footer,onLaterPages=footer)
print(file)

