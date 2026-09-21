# 개발 에이전트에 전달할 2차 수정 지시

```text
M1 2차 검토 결과 ‘수정 후 재검토’다. M2는 시작하지 마.
docs/reviews/M1-recheck.md와 M1-recheck-probe.py를 읽어줘.

이번 범위는 R1~R6과 키 없이 가능한 승인 흐름 완성이다.
1. 모든 DB 접근의 transaction 경계를 통일하고 quote commit의 타 거래 침범을 차단.
2. 실제 write 후 exception을 NEEDS_RECONCILIATION으로 종료하고 중복 실행 금지.
3. expected와 독립된 실제 상태/전후 변경 기반 oracle 구현.
4. 100개 실제 fixture loader와 실행 가능한 split, order/text/seed 누출 검사.
5. quote_id 등 각 인자의 실제 이전 step 출처를 trace에 기록.
6. 새 견적은 현재 활성 정책을 사용하고 오래된 견적만 차단.
7. 운영자 승인 객체·단회 소비·만료·조건 재검증·재개 구현.

각 항목은 실제 경쟁 조건/예외/잘못된 상태를 넣는 자동 테스트로 증명해줘.
기존 정상·거절·중복·승인대기 테스트도 유지해줘.
관찰용 probe의 exit 0이나 단순 목록 크기를 완료 근거로 사용하지 마.
MCPAdapter 위임 함수와 목록 길이 검사 MockModelLoop를
실제 MCP/모델 실행 루프 구현 완료로 표시하지 마.
도구 계약 hash가 인자와 타입 변경도 감지하도록 수정해줘.

결과는 docs/reviews/M1-fixes-round2.md에
R ID별 파일·재현·검증 명령·결과·남은 한계로 기록해줘.
외부 인증 때문에 못 한 작업과 로컬 미구현을 분리해줘.
완료 후 재검토를 요청하고 M2는 진행하지 마.
```
