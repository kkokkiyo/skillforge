# 레퍼런스와 확인 수준

조사일: 2026-09-20. 공식 문서도 이후 변경될 수 있다. 원문 전체를 복제하지 않고 링크·확인 범위·설계에 적용한 판단을 기록한다. 특정 기능의 설치 성공이나 사용자 계정 접근은 웹 문서 확인과 다르다.

## R01 해커톤 안내 / R02 신청서

- [Fastcampus NVIDIA 해커톤](https://fastcampus.co.kr/NVIDIA_hackathon)
- [신청서](https://docs.google.com/forms/d/e/1FAIpQLScyZ5GYYaCOycNUzXVUTenliEUmSEIdXelVdYphvMvLeLuiHA/viewform)
- 상태: 직접 웹 열람 실패. **이번 대화에 사용자가 붙여넣은 내용**을 일정·심사·제출 규정의 근거로 사용했다. 별개 Fast Builderthon 검색 결과는 이번 대회 자료로 쓰지 않았다.
- 확인 범위: 9/28 접수 종료, 팀 2~5인, 팀원 각자 신청, 데모 제출, 링크를 담은 Word/PDF 업로드, NVIDIA 기술/실용성/완성도/독창성 평가.
- 미확인: 마감 시각·상세 배점·Skill API의 구체적 정의·허용 모델·개인 참가와 팀 지원 문구의 적용 방식. T00/T18에서 재확인.

## R03 AI Day Seoul

- [NVIDIA 공식 행사 페이지](https://www.nvidia.com/ko-kr/ai-days/?ncid=no-ncid)
- 공식 본문 확인: 2026년 11월 9~10일 COEX 행사. 사용자 제공 쇼케이스 일정은 11/10 오후이므로 전체 행사 일정과 구분한다.
- 활용: 발표 기회와 일정 맥락. 프로젝트의 수상 가능성 근거로 사용하지 않는다.

## R04 NVIDIA 교육 원본

- [사용자 지정 시작 페이지](https://nvdli.github.io/NemoClawDLI/nemoclaw/01a-loop.html): 직접 접근 실패.
- [NVDLI 공식 교육 저장소](https://github.com/NVDLI/NemoClawDLI): 대체 원문 확인.
- [과정 목표](https://github.com/NVDLI/NemoClawDLI/blob/main/web/nemoclaw/COURSE_CANON.md): 모델·도구·루프, routing, OpenShell, 지속 스킬 학습 목표 확인.
- [2A Workflow 원문](https://raw.githubusercontent.com/NVDLI/NemoClawDLI/main/web/nemoclaw/02a-routing.html): ReAct와 구조화된 실행, routing을 설명. 우리 선형 재사용 방식의 설계 참고이며 자동 컴파일을 강의가 제공한다는 뜻은 아니다.
- [3C Always-on 원문](https://raw.githubusercontent.com/NVDLI/NemoClawDLI/main/web/nemoclaw/03c-always-on.html): markdown skill을 통한 지침 재사용 확인. 문서와 실행기가 다른 역할이라는 설계에 반영.
- [4A Safety 원문](https://raw.githubusercontent.com/NVDLI/NemoClawDLI/main/web/nemoclaw/04a-safety.html): prompt·harness·sandbox 방어 구분 확인. 사업 규칙과 OS 격리를 분리.
- 위 강의별 원문을 확인했지만 실습을 직접 수행한 상태는 아니다. 1A 세부 실습의 성공을 주장하지 않는다.

## R05 NeMo Agent Toolkit

- [공식 Overview](https://docs.nvidia.com/nemo/agent-toolkit/latest/)
- [공식 Quick Start](https://docs.nvidia.com/nemo/agent-toolkit/latest/get-started/quick-start.html)
- 확인: 도구/워크플로 구성, profiling 및 evaluation 기능, NVIDIA_API_KEY를 이용한 예제 실행 경로.
- 적용: 자체 profiler를 크게 만들기 전에 NAT 이벤트와 평가 기능을 연결한다. 패키지·플러그인·설정 syntax는 설치한 버전 기준으로 검증한다. NeMo Platform의 별도 평가 SDK와 NAT를 섞어 설치하지 않는다.

## R06 OpenShell / R07 NemoClaw

- [OpenShell 공식 저장소](https://github.com/NVIDIA/OpenShell)
- [NemoClaw 공식 저장소](https://github.com/NVIDIA/NemoClaw)
- 확인: OpenShell은 정책 기반 실행 격리, NemoClaw는 OpenShell 위 agent 실행과 관리된 추론을 연결하는 프로젝트. OpenShell README의 Windows WSL2 지원은 experimental로 표시되어 있다.
- 적용: WSL 기본 개발과 격리 검증을 별도 gate로 둔다. 특정 명령/버전을 추측하여 설치 스크립트를 복사하지 않는다. 검증 프로필이 실패하면 운영 UI에 미검증으로 표시한다.

## R08 모델 후보

- [NVIDIA Nemotron 3 Super 120B A12B 모델 카드](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b/modelcard)
- 확인: agentic workflow·tool use 용도, reasoning 설정 관련 안내. 모델 카드의 supported languages 목록에 한국어는 명시되어 있지 않았다.
- 적용: `nvidia/nemotron-3-super-120b-a12b`를 첫 후보로 검증하되 실제 계정 가용성·지연·한국어 10문장 tool/intent 정확도를 먼저 확인한다. 영어 내부 도구 계약 + 한국어 UI를 기본으로 한다. 다른 모델로 바꾸면 동일 비교군을 다시 측정한다.
- 모델 카드의 일반 benchmark 수치를 우리의 환불 업무 성능으로 옮기지 않는다. 로컬 GPU 대신 hosted API를 우선 검토한다.

## R09 선행 연구

- [Agent Workflow Memory, Wang et al., 2024](https://arxiv.org/abs/2409.07429)
- 초록 확인: 과거 경험에서 재사용 가능한 workflow를 유도해 이후 agent 실행에 제공하는 방향을 제안한다.
- 적용: 경험 기반 절차 재사용 자체를 최초 기여라고 주장하지 않는다. 이 프로젝트는 검증 가능한 실행 DSL과 변경 업무의 정책 경계에 초점을 둔다. 해당 논문의 benchmark 결과를 우리 성능으로 인용하지 않는다.

## R10 Kiro 스펙 주도 개발

- [Specs](https://kiro.dev/docs/specs/)
- [Feature Specs](https://kiro.dev/docs/specs/feature-specs/)
- [Quick Spec](https://kiro.dev/docs/specs/quick-spec/)
- 확인: requirements.md, design.md, tasks.md 구조, EARS 인수 조건, 요구사항부터 설계/태스크를 연결하는 방식.
- 적용: `.kiro/specs/skillforge-mvp/`에 세 문서를 배치하고 태스크마다 REQ ID·의존성·완료 기준을 명시했다. 이 결과는 해당 구조를 참고해 작성한 문서이며 Kiro가 실행/승인했다는 뜻은 아니다.

## R11 Codex 개발 지침

- [공식 AGENTS.md 안내](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- 확인: 프로젝트별 AGENTS.md 지침을 개발 컨텍스트로 사용한다.
- 적용: 짧은 프로젝트 지침에서 권위 있는 스펙·검증·범위를 가리킨다. 첨부 원안의 CLI 명령·권한 설정 예시를 이번 환경에서 실행 완료한 것으로 간주하지 않는다.

## 사용자 원안

[source-original.txt](source-original.txt)는 사용자가 제공한 ReAct-to-Workflow Compilation 구상 원문이다. “13일”, 샘플 성능 수치, 예시 API 명칭은 현재 일정이나 실측값이 아니다. 수정 판단은 [주제 전략](01-product-strategy.md)에 기록했다.
