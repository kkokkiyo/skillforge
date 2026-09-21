# SkillForge - 실행 기록에서 배우는 안전한 업무 자동화

서비스명: **SkillForge**  
팀명(사용자 검토 전 임시안): **TraceMakers**  
저장소명 추천: `skillforge`  
저장소 URL: 아직 생성하지 않음. 공개 URL 확정 후 PDF와 이 파일에 함께 반영해야 함.

## Problem Definition (300자 내외)

반품·환불을 처리하는 커머스 운영팀은 비슷한 요청을 반복적으로 처리하면서도 매번 소유권, 반품 수령, 금액과 승인 조건을 확인해야 합니다. LLM 에이전트가 이를 매번 처음부터 추론하면 모델 호출과 지연이 누적되고, 처리 결과를 설명하거나 변경된 정책을 일관되게 적용하기 어렵습니다. 반대로 모든 예외를 사람이 고정 절차로 작성하면 유지보수 부담이 커집니다. SkillForge는 성공한 실행 경험을 재사용하면서도 금전 변경 업무의 정책 검사와 검증 근거를 유지하는 문제에 집중했습니다. 실제 고객·결제 대신 합성 주문에서 동작을 검증합니다.

## Solution (500자 내외)

SkillForge는 에이전트의 성공 기록을 검증 가능한 선형 워크플로로 전환하는 운영 콘솔입니다. NVIDIA Nemotron이 주문 조회, 반품 확인, 정책 조회, 견적 생성, 환불, 결과 검증 도구를 호출하면 입력·출력의 출처와 정책 버전을 기록합니다. 서로 다른 주문의 성공 기록 5건 이상에서 동일한 도구 순서와 인자 참조를 확인해 후보를 만들고, 생성에 쓰지 않은 30개 사례를 독립 DB에서 재실행합니다. 검증을 통과한 후보만 운영자가 활성화하며 새 요청에서는 최신 데이터를 읽어 재사용합니다. 모델 실행과 워크플로 실행 모두 같은 정책 게이트웨이를 통과합니다. 고액 환불은 서버에 저장된 단회 승인을 요구하고, 정책 변경 시 기존 절차를 제외하며, 쓰기 후 오류는 조정 필요 상태로 남깁니다. 콘솔에서 실시간 이벤트, 후보 출처, 실행 지표와 비교 평가를 확인할 수 있습니다. 자동 생성은 환불 도메인의 제한된 계약을 사용하며 범용 코드 생성이나 모델 학습은 하지 않습니다.

## Tech Stack

- 실제 모델: `nvidia/nemotron-3-super-120b-a12b`, NVIDIA hosted Chat Completions API, tool calling.
- NVIDIA NeMo Agent Toolkit 1.9.0: 사용자 정의 workflow 플러그인으로 동일한 bounded agent와 gateway를 실행. 실제 live 실행 증거 저장.
- MCP Python SDK 2.2.0: 6개 환불 도구의 stdio 서버와 실제 client/server smoke 검증.
- Python 3.12, FastAPI 0.141.1, Pydantic 2.13.5, Uvicorn 0.53.0, SQLite.
- React 19.3.0, TypeScript 5.9.3, Vite 7.3.6. SSE 진행 스트림 및 JSONL export.
- 자체 구현: trace 기반 도메인 컴파일러, 데이터 전용 DSL interpreter, 정책·승인 gateway, 독립 DB oracle, A/B/C 평가.
- OpenShell/NemoClaw sandbox: 미검증. 앱의 정책 검사와 OS 격리를 동일한 보장으로 소개하지 않음.
- 신청서의 ‘Skill API’ 명칭·별도 증빙 요구: 미확정. 일반 NVIDIA inference 성공만으로 충족을 주장하지 않음.

## 제출 정보

GitHub: https://github.com/kkokkiyo/skillforge
영상 URL: https://github.com/kkokkiyo/skillforge/blob/main/output/video/SkillForge-evidence-walkthrough.mp4
3분 자막형 실행 증거 재생 자료입니다. 실제 브라우저 녹화가 아니며 GitHub에서 다운로드해 재생할 수 있습니다.
공개 저장소에는 API 키, 운영자 토큰, 개인 연락처, SQLite DB를 올리지 않습니다. 각 팀원은 본인 개인정보·동의를 직접 작성하고 공통 포트폴리오 파일을 사용합니다.
