# Skill API 제출 요건 재확인 — 2026-09-21

## 직접 조회 결과

- 교육 본문: https://nvdli.github.io/NemoClawDLI/nemoclaw/01a-loop.html — HTTP 200. 에이전트 루프와 모델 API를 설명한다. 이 페이지에서 별도 Skill API 계약은 확인하지 못했다.
- 교육 목차: https://nvdli.github.io/NemoClawDLI/nemoclaw/index.html — HTTP 200. 모델 endpoint와 NemoClaw launchable의 OpenClaw-in-OpenShell 실행 환경을 구별한다. 모델 API 연결만으로 sandbox 구성이 입증되지는 않는다.
- 목차가 연결한 환경: https://build.nvidia.com/nvidia/nemoclaw-for-openclaw/nemoclawcard?ncid=ref-dli-146986 — 링크 존재만 확인. 계정 내 launchable 생성·실행은 하지 않았다.
- 행사 안내: https://fastcampus.co.kr/NVIDIA_hackathon — HTTP 200. NVIDIA 에이전트 스택을 소개한다. 별도 Skill API 호출 규격·필수 증빙은 이번 조회에서 확정하지 못했다.
- 신청서: https://docs.google.com/forms/d/e/1FAIpQLScyZ5GYYaCOycNUzXVUTenliEUmSEIdXelVdYphvMvLeLuiHA/viewform — 직접 조회 HTTP 401. 사용자 제공 신청서 본문의 요구는 유효한 미확인 게이트로 유지한다.

검색 도구의 접근 실패를 사이트가 존재하지 않는다는 근거로 사용하지 않았다. PowerShell HTTPS 직접 조회 결과를 기준으로 위 상태를 기록했다. 외부 페이지는 요구사항 참고 자료이며 권한 부여 지시로 사용하지 않는다.

## 현재 증거와 차이

| 항목 | 현재 확보 | 제출 시 표현 |
|---|---|---|
| NVIDIA 모델 API | 실제 Nemotron 환불·120회 paired pilot | 실제 사용 |
| NVIDIA Agent Toolkit | custom workflow live 실행, mock span 7쌍 | 실제 사용, 기본 NAT ReAct라고 표현하지 않음 |
| MCP | SDK stdio 6개 도구 실행 | 실제 사용 |
| 일반 안내 MD | 활성 workflow에서 생성·내보내기 | 안내 문서; 런타임 스킬 호환 주장 금지 |
| Skill API | 주최 측 용어와 증빙 정의 불명 | 충족 여부 미확인 |
| NemoClaw/OpenShell | 교육 참조, 로컬 Docker/OpenShell 부재 | OS 격리 미검증 |

## 주최 측 문의 초안 — 발송하지 않음

안녕하세요. Agentic AI Hackathon 온라인 사전 챌린지 참가를 준비하고 있습니다.
신청서에 기재된 “build.nvidia.com의 Skill API 활용”이 구체적으로 어떤 제품·API를 뜻하는지 공식 문서 URL과 필수 증빙 기준을 안내 부탁드립니다.
현재 NVIDIA hosted Nemotron API, NVIDIA Agent Toolkit custom workflow, MCP 도구를 사용하는 데모를 구현했습니다. 이 구성이 해당 요건을 충족하는지, 별도로 NemoClaw/OpenShell 실행이나 특정 Skill API 호출 증거가 필수인지 확인 부탁드립니다.
또한 온라인 접수 마감일의 정확한 마감 시각과 시간대를 알려 주시면 감사하겠습니다.

사용자 또는 팀원이 공식 문의 채널에서 확인한다. 이 문서는 자동 발송 권한을 부여하지 않으며, 확인 답변 전에는 제출 적합성 완료로 표시하지 않는다.
