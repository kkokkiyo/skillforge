# SkillForge — 정책 변화에 대응하는 검증 가능한 자동화

서비스명: **SkillForge**
팀명: **TraceMakers (임시안, 팀원 신청서와 일치시키세요)**
GitHub: https://github.com/kkokkiyo/skillforge

## Problem Definition (313자, 공백 포함)

커머스 운영팀은 반복되는 반품·환불을 자동화하면서도 정책이 바뀔 때마다 기존 절차와 승인 조건을 다시 점검해야 합니다. LLM에 매번 판단을 맡기면 호출과 지연이 누적되고, 고정 워크플로만 쓰면 어떤 사례가 달라지는지 사람이 추적해야 합니다. 특히 금전 변경 업무에서는 처리 속도만큼 실행 근거, 잘못된 환불 방지, 정상 요청의 과도한 차단 방지가 중요합니다. SkillForge는 성공한 실행 경험을 재사용하되 정책 변경의 영향을 확인하고 검증된 절차만 다시 활성화하는 운영 문제에 집중합니다. 실제 고객·결제 대신 합성 주문에서 구현과 검증을 수행했습니다.

## Solution (501자, 공백 포함)

SkillForge는 실행 기록을 검증된 자동화로 전환하고 정책 변화에 대응하는 운영 콘솔입니다. NVIDIA Nemotron이 6개 환불 도구를 호출하면 공개 이벤트와 인자 출처, DB 판정을 기록합니다. 독립 성공 기록 5건 이상에서 실제 입력과 이전 출력의 값·타입·순서를 확인해 참조 기반 워크플로를 구성합니다. 분리된 30개 사례와 6개 경계 검사를 통과한 후보만 운영자가 활성화합니다. 승인 기준을 50만원에서 30만원으로 바꾸기 전에는 42쌍의 격리 실행으로 판정 변화, 위험 변경, 정상 오차단을 비교합니다. 예를 들어 35만원 환불이 자동 처리에서 승인 필요로 바뀌는 이유를 화면에서 확인할 수 있습니다. 변경 적용 후 기존 절차는 중지되고, 출처와 부모 버전을 보존한 새 후보를 재검증해야 합니다. 모든 경로는 같은 정책·단회 승인·중복 방지 게이트웨이를 통과합니다. 쓰기 후 결과가 불확실하면 자동 재시도 대신 상태 확인을 요구하며, 실행과 비교 증거를 내려받을 수 있습니다.

## Tech Stack

- NVIDIA hosted Nemotron `nvidia/nemotron-3-super-120b-a12b`: 실제 tool calling과 공개 실행 증거.
- NVIDIA NeMo Agent Toolkit 1.9.0 custom workflow: 자체 bounded loop를 실행하는 플러그인. NAT 기본 ReAct라는 주장 아님.
- MCP SDK 2.2.0 stdio: 공통 gateway의 6개 도구, 실제 client/server 검증.
- Python 3.12, FastAPI, Pydantic, SQLite; React, TypeScript, Vite, SSE.
- typed symbol table, trace 정규화·해시 그룹화, 제한된 JSON DSL, artifact/report hash binding, 정책 변경 compare-and-swap, 독립 DB oracle.
- NemoClaw/OpenShell OS 격리와 신청서의 Skill API 세부 요건은 미확인. 일반 inference 성공으로 동일 요건 충족을 단정하지 않음.

## 제출 방법

Google Form의 서비스 파일 항목에 `NVIDIA 해커톤_팀명_SkillForge.pdf` 한 파일을 올립니다. PDF에 프로젝트명·공개 GitHub 링크·영상 링크가 들어 있습니다. 팀명 확정 시 파일명과 PDF 팀명을 일치시킵니다. 모든 팀원이 개별 신청서를 작성하고 같은 프로젝트 자료를 사용합니다. 개인정보와 동의 항목은 본인이 작성합니다.

접수 마감은 사용자에게 전달된 주최측 답변 기준 **2026-09-28 23:59**입니다. 답변에 시간대는 별도 표기되지 않았으므로 여유 있게 제출하세요. 이 저장소가 신청서를 자동 제출하지는 않습니다.

영상: https://github.com/kkokkiyo/skillforge/blob/main/output/video/SkillForge-evidence-walkthrough.mp4
영상은 실행 증거를 시각화한 재생 자료이며 브라우저 녹화가 아닙니다.
