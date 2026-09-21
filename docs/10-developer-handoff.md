# 개발 에이전트 인계 지시문

역할: 다른 에이전트가 구현하고, 현재 기획·검토 에이전트가 결과를 확인한다. 프로젝트의 기준 경로는 WSL `/home/dongchan-lee/projects/nvidia-hackothon`이다. Windows 문서 사본과 별도로 개발하지 말고 **WSL을 원본**으로 삼는다.

## 1. 첫 메시지 — 그대로 전달

```text
너는 SkillForge의 개발 담당 에이전트다. 구현과 자체 검증을 맡고,
다른 검토 에이전트가 마일스톤별로 코드·실행·제출 근거를 검토한다.

프로젝트 경로:
/home/dongchan-lee/projects/nvidia-hackothon
Windows 접근:
\\wsl.localhost\Ubuntu-24.04\home\dongchan-lee\projects\nvidia-hackothon

먼저 기존 파일과 변경 상태를 확인하고 다음 문서를 읽어라.
- AGENTS.md, README.md
- .kiro/specs/skillforge-mvp/requirements.md
- .kiro/specs/skillforge-mvp/design.md
- .kiro/specs/skillforge-mvp/tasks.md
- docs/02-ux-design.md, docs/03-evaluation.md
- docs/09-submission-runbook.md, docs/11-review-protocol.md

목표는 2026 NVIDIA 해커톤 예선용 실행 가능한 MVP다.
반품 수령 후 전액 환불 하나에 집중한다.
Nemotron ReAct의 실제 실행 기록에서 전체 도구 순서와 인자 출처를 유도하고,
선형 JSON workflow를 별도 사례에서 검증한 후 활성화·재사용한다.
모든 경로가 같은 정책·승인·멱등성 검사를 거쳐야 한다.
운영 콘솔에서 실행 기록, 후보 출처, 검증, 승인·차단, 실측 비교를 보여준다.

이번 작업 범위는 M1: T00~T07 및 T12다. 작업 순서는 의존성을 따른다.
실제 API 경로가 막혀도 독립적인 DB·정책·mock 테스트·UI는 진행해라.
키는 출력하지 말고 live/mock을 명확히 구분해라.
Skill API 요구가 불명확하면 공식 자료를 조사하고 미확인으로 기록해라.
질문만 남기고 멈추지 말고, 답변 없이도 할 수 있는 작업은 완료해라.

임의 DAG, PrefixSpan, 모델 학습, 실제 결제, 추가 업무를 만들지 마라.
기존 사용자 파일을 덮어쓰지 말고, 일반적인 구현 선택은 스펙 안에서 결정해라.
버전은 설치 검증 후 lock하고 현재 스펙에 반영해라.
위험 동작·핵심 상태 변경에 의미 있는 테스트를 작성하고 실제 실행해라.
T00가 막혔다면 관련 완료 체크를 하지 말고 의존성 없는 태스크만 진행해라.

끝나면 docs/reviews/M1-developer-report.md에
docs/11-review-protocol.md의 보고 양식대로 근거를 남겨라.
README의 실행 절차와 tasks.md의 실제 완료 상태를 갱신해라.
M1 결과를 보고한 뒤 M2는 검토 피드백을 받은 다음 진행한다.
유료 자원 생성, 외부 발송, 공개 배포, 신청서 제출은 하지 마라.
```

## 2. 이후 작업 단위

| 마일스톤 | 태스크 | 검토자가 확인할 핵심 |
|---|---|---|
| M1 실행 기반 | T00~T07, T12 | live 도구 호출, 공통 정책, trace, DB 불변식, 분할, UI 골격 |
| M2 재사용 엔진 | T08~T11, T13 | 기록 기반 유도, 새 입력 바인딩, 검증/승격, stale 처리, E2E |
| M3 증거와 안정화 | T14~T15, 필요 시 T16~T17 | 공정한 A/B/C, 예외·동시성, 실제 격리 여부 |
| M4 제출 준비 | T18, T19 buffer 활용 | 실행 안내, 최종 문구, PDF, 영상 자료, 링크·결과 일치 |

M4에 영상 녹화나 계정 게시처럼 실행 환경에서 못 하는 일이 있으면 대본·장면별 실행 절차·필요 파일까지 만들고 사람이 수행할 항목을 분리한다. 수행하지 않은 녹화·게시를 완료로 표시하지 않는다.

## 3. 검토 후 다음 단계 명령

```text
docs/reviews/M1-review.md의 지적 사항을 읽어라.
수정이 필요한 항목을 재현한 뒤 고치고 해당 검증을 다시 실행해라.
해결 근거를 docs/reviews/M1-fixes.md에 남겨라.
수정 완료 후 M2(T08~T11, T13)를 구현해라.
완료 기준은 기존 스펙을 따르고, 결과는 M2-developer-report.md로 남겨라.
검토에서 수정 요청이 없으면 바로 M2를 진행해라.
```

M3/M4도 ID만 바꿔 같은 방식으로 진행한다. 검토 결과가 존재하지 않으면 존재한다고 가정하지 않는다. 검토자가 아직 보지 않은 변경은 보고서에 추가로 표시한다.

## 4. 개발 완료 후 이 대화에 보낼 메시지

```text
개발 에이전트가 M1을 완료했어.
WSL /home/dongchan-lee/projects/nvidia-hackothon에서
docs/reviews/M1-developer-report.md를 읽고 직접 검토해줘.
보고서를 그대로 믿지 말고 코드·스펙·테스트·실행 증거를 확인해줘.
개발 구현은 다른 에이전트가 수정할 예정이니 검토 결과와 수정 지시를
docs/reviews/M1-review.md에 남겨줘.
중대한 결함, 증거 부족, 다음 단계 진행 가능 여부를 구분해줘.
```

M1 대신 실제 완료한 단계명을 넣는다. Git을 쓰면 검토 대상 commit SHA도 알려준다. 다른 Codex 작업에서 개발한다면 해당 작업 이름/ID도 전달하면 보고와 현황을 함께 확인할 수 있다. 별도 감시 자동화가 설정된 것은 아니므로 완료 후 검토를 요청한다.
