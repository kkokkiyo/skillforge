# 개발 에이전트 재작업 지시 — M1 보완

아래 내용을 개발 에이전트에게 그대로 전달한다.

```text
M1 검토 결과는 ‘수정 후 재검토’다. M2로 넘어가지 말고 M1을 보완해줘.
WSL /home/dongchan-lee/projects/nvidia-hackothon에서 작업해줘.

먼저 AGENTS.md, docs/reviews/M1-review.md,
docs/reviews/M1-review-probe.py와 출력 파일을 읽어줘.
검토 당시 해시와 현재 코드를 비교하고 사용자 변경을 보존해줘.

1. F01~F07을 각각 재현하고 회귀 테스트를 추가한 뒤 수정해줘.
   - write transaction 안에서 최신 반품·금액·버전·정책·expiry 확인
   - customer_id와 approved를 요청 본문에서 권한으로 신뢰하지 않기
   - 정적 파일의 web root 밖 접근 차단
   - 스레드 간 DB transaction과 trace commit 격리
   - 실제 provider 경로에 따라 live/mock 기록, 더미 키로 live 증명 금지
   - 독립 DB oracle과 실패 판정, 쓰기 후 결과 불확실 시 재환불 금지
   - 진짜 데이터 분할 검증과 정확한 반품 미수령 테스트

2. 키 없이 가능한 M1 작업을 마쳐줘.
   - 승인 객체·운영자 세션·단회 소비·만료·상태 재검증·재개
   - 동일 idempotency key/payload 재요청 결과 반환, 다른 payload 충돌
   - 지속 가능한 trace와 timestamp/provenance/실패/usage null/export
   - 30/30/40 사례, 독립 oracle, 누출을 검출하는 테스트
   - 엄격한 입력 계약과 MCP adapter, bounded model loop의 mock 검증
   - 실제 화면 상태 반영과 부분 구현 표시

3. 외부 의존 작업은 별도로 기록해줘.
   - NVIDIA 키가 있으면 실제 호출, 없으면 live 미검증 유지
   - 키를 출력하거나 채팅에 요구하지 말고 환경변수 이름만 안내
   - NAT 설치/네트워크 가능 여부는 실제 시도와 오류로 확인
   - Skill API 요구는 공식 자료로 조사, 미확인이면 명시
   - OpenShell은 현재 P1이며 로컬 핵심 결함 수정 후 검토

4. 표준 HTTP/정적 JS를 임시로 유지할지 원래 스택으로 전환할지
   일정·테스트 가능성을 기준으로 결정하고 설계/steering/README에 맞춰줘.
   어느 쪽이든 보안·trace·평가 완료 기준은 줄이지 마.
   README에 문서 인덱스를 복원하고 M1 부분 구현과 live 미검증을 명시해줘.

검토 probe는 관찰용이므로 exit 0만으로 수정 통과라 하지 마.
각 결함의 기대 결과를 단언하는 자동 테스트로 증명해줘.
docs/reviews/M1-fixes.md에 F ID별 변경·검증 명령·결과·미해결 사항을 남기고,
M1-developer-report.md와 tasks.md의 실제 진척을 갱신해줘.
테스트/재현 증거가 없는 항목은 완료로 체크하지 마.
제품 코드 외부 게시·배포·신청서 제출은 하지 마.
완료하면 재검토 요청을 남기고 M2는 진행하지 마.
```
