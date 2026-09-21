# 개발 작업 프롬프트

이 문서는 구현을 시작할 때 사용할 작업 지시 템플릿이다. 한 번에 전체 프로젝트를 요청하기보다 [tasks.md](../.kiro/specs/skillforge-mvp/tasks.md)의 완료 기준으로 진행한다. AGENTS.md 사용 방식은 [공식 문서](https://learn.chatgpt.com/docs/agent-configuration/agents-md)를 참고했다.

## 첫 작업: T00

```text
AGENTS.md와 .kiro/specs/skillforge-mvp의 세 문서를 읽고 T00만 수행해줘.
기존 파일을 먼저 확인하고 보존해줘.
NVIDIA Skill API의 정확한 요구를 확인 가능한 공식 자료로 조사하고,
확인되지 않는 내용은 docs/08-decisions-and-spikes.md에 blocker로 남겨줘.
키 값을 출력하지 말고 환경변수 존재 여부만 확인해줘.
키가 있으면 지정 모델의 실제 tool call 1회와 한국어 의도 추출 검증을 수행해줘.
키가 없으면 mock을 live 성공으로 표시하지 말고 독립적인 환경 점검을 마쳐줘.
NAT의 최소 실행/프로파일링 호환 버전을 확인하고 결과와 근거를 저장해줘.
유료 자원 생성·신청서 제출·외부 메시지 발송은 하지 마.
보고는 확인된 사실, 실제 실행 결과, 남은 결정으로 구분해줘.
```

## 공통 작업 템플릿

```text
AGENTS.md와 관련 스펙을 읽고 TXX를 구현해줘.
선행 태스크의 완료 증거를 확인하고 필요한 범위만 수정해줘.
REQ-XX의 인수 조건과 연결되는 의미 있는 테스트를 수행해줘.
테스트가 통과한 뒤 tasks.md를 갱신하고 행동 변경은 설계에도 반영해줘.
완료한 파일, 실제 실행한 검증, 실패/미확인 사항을 보고해줘.
다음 태스크의 기능을 임의로 추가하지 마.
```

## 컴파일러 작업 시 추가 조건

```text
도구 전체 순서 그룹화와 provenance 기반 인자 바인딩만 지원해줘.
tool name 문자열 나열을 실행 가능한 workflow로 간주하지 마.
이전 order ID/quote ID를 새 실행에 재사용하지 않는 테스트를 포함해줘.
모호한 참조, 미래 참조, 필수 검증 누락, 알 수 없는 tool은 거절해줘.
동일 입력 반복은 독립 support로 세지 말고 source trace를 보존해줘.
```

## 평가 작업 시 추가 조건

```text
docs/03-evaluation.md 기준으로 A/B/C를 같은 조건에서 비교해줘.
discovery/validation/test를 분리하고 최종 test로 후보를 수정하지 마.
실패, timeout, missing token usage를 숨기지 마.
수동 workflow보다 자동 workflow가 느려도 결과를 그대로 남겨줘.
보고서 숫자를 run ID에서 재계산 가능한 형태로 저장해줘.
```

## 검토 요청

```text
현재 구현을 REQ-01~11과 비교해줘.
특히 승인 우회, 정책 변경 후 stale workflow, 동시 중복 환불,
commit 뒤 timeout에서의 재실행, 평가 데이터 누출을 확인해줘.
발견한 실제 문제와 재현 방법을 우선 보고하고,
검증하지 않은 사항은 완료로 표시하지 마.
```
