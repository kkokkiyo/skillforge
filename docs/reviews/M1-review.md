# M1 검토 결과

- 검토일: 2026-09-20
- 대상: `/home/dongchan-lee/projects/nvidia-hackothon`
- Git 미사용. 아래 SHA-256의 구현을 검토했다.
- 판정: **수정 후 재검토. M1 부분 구현이며 M2 착수 승인 아님.**
- 제품 코드는 수정하지 않았다. 검토 재현 코드는 별도 메모리 DB와 임시 localhost 서버만 사용했다.

## 검토 대상

```text
dc2d9abd9457cef3735f5cb8acb0ac147079078c68f3a10b99f3cc40ef912ddc backend/app.py
e0fa781e476888596fec4e007e4fac3ec82be61325d61e66cd5c604c8a934849 backend/server.py
102b6d90181c2a5c4df37876bbbbeb712674f8e4ae3d165732e50b45afdd22eb tests/test_m1.py
cf9fd7e44b4eed7c7972fc31bb365fa0c7c19d4daa63001cb1cc3f9414d3482a web/app.js
```

## 직접 수행한 검증

1. `python3 -m unittest discover -s tests -v`: 5건 통과, exit 0.
2. `python3 docs/reviews/M1-review-probe.py`: 7개 관찰 결과 출력, exit 0. **이 스크립트는 결함 재현 도구이며 exit 0이 제품 검증 통과라는 뜻은 아니다.** 출력은 `M1-review-probe-output.jsonl`에 저장했다.
3. 보고서, README, task 상태, backend, server, tests, UI 코드를 읽었다.

실제 NVIDIA API·NAT·OpenShell, 브라우저 렌더링·키보드 E2E, 의존성 설치는 수행하지 않았다. 이전 smoke run ID는 현재 프로세스의 기록으로 독립 재확인하지 못했다. 실행 데이터가 in-memory이므로 프로세스 재시작 시 사라진다.

## 발견 사항 — 모두 mock 환경에서 재현 또는 코드 확인

### F01 [P1] 환불 직전 최신 상태를 재검증하지 않음

위치: `backend/app.py:134` (`_issue_refund`, 특히 137~146).

견적 생성 후 반품 received=0, 주문 paid_krw=100/version=2, quote policy_hash를 다른 값으로 바꿨다. 기존 견적 89,000원이 그대로 COMMITTED되고 DB에 paid=100/refunded=89,000이 남았다. 주문/정책 버전과 반품 수령, 잔여 결제액, 금액 범위를 write transaction에서 확인하지 않는다. 견적 만료도 없다.

수정: 거래 안에서 소유권·반품·잔여액·정수 금액·주문 버전·현재 정책 hash·견적 expiry를 모두 다시 검증하고 실패 시 0 commit. 각각 독립 사례로 회귀 테스트한다. REQ-01/08, T02/03.

### F02 [P1] 고객 신원을 요청 본문에서 선택할 수 있음

위치: `backend/server.py:29`.

독립 fixture에서 타 고객 order-003의 반품을 수령 상태로 만든 후, HTTP body에 customer_id=cust-002를 넣자 120,000원 환불이 성공했다. `_order`의 비교 자체는 있지만 비교 대상 신원을 호출자가 정하므로 API 경계에서 보호되지 않는다.

수정: 고객 신원을 서버의 신뢰된 데모 세션에서 주입한다. body의 customer_id/approved를 권한으로 받지 않는다. 데모에서 고객 전환이 필요하면 명시적인 서버 fixture/session 경로로 분리한다. 현재 사용자로 타 주문 요청 시 거절하는 HTTP 테스트 필요. REQ-01/08.

### F03 [P1] 정적 파일 경로가 web 디렉터리를 벗어남

위치: `backend/server.py:20`.

`GET /../README.md`가 200과 실제 프로젝트 README 내용을 반환했다. 민감 파일을 읽지는 않았다. 동일 경로 처리로 web 외부 파일 접근이 가능하다.

수정: 검증된 static-file handler 또는 resolve 후 web root 포함 검사로 traversal을 거절한다. `..`, 인코딩, query, symlink 경계를 테스트한다. 파일별 Content-Type도 명시한다. 외부에 공개하기 전에 반드시 해결한다.

### F04 [P1] 공유 DB 연결로 다른 요청의 trace가 환불 transaction을 commit할 수 있음

위치: `backend/app.py:45`, `backend/app.py:76`, `backend/server.py:9`, `backend/server.py:34`.

ThreadingHTTPServer가 하나의 connection을 공유하고 Trace.add가 매번 commit한다. 한 스레드에서 BEGIN IMMEDIATE 후 주문 변경, 다른 스레드에서 trace 추가, 첫 스레드 rollback을 실행해도 주문 변경이 남았다. unique 제약만으로 거래 격리를 보장하지 못한다.

수정: 요청별 connection + 파일 DB/명시적 transaction 관리 또는 전체 DB 작업의 올바른 직렬화를 적용한다. 다른 요청의 trace가 거래를 commit하지 못하게 한다. 승인 소비·환불·주문 변경의 원자성, 병렬 요청, 중간 오류 rollback 테스트 필요. REQ-01/08.

### F05 [P1] mock 실행을 live로 기록하고 더미 키만 있어도 live=true 표시

위치: `backend/server.py:16`, `backend/server.py:29`, `backend/app.py:159`.

HTTP body에 mode=live를 넣으면 모델 호출 없는 고정 Python 흐름이 runs.mode=live로 저장됐다. 실제 키가 아닌 더미 문자열만 환경변수에 설정해도 health.nvidia_live=true였다. 이 상태는 제출 증거를 잘못 표시한다.

수정: provider 실행 경로가 mode를 결정하도록 한다. 미구현 live 요청은 명시적 오류, key_configured/adapter_available/live_verified를 분리한다. 실제 live 호출 근거가 없으면 live_verified=false. README의 키 주입만 하면 live 실행 가능하다는 인상도 고친다. REQ-02/03/11.

### F06 [P1] 검증 결과와 무관하게 성공·oracle 통과를 기록

위치: `backend/app.py:172`.

verify_refund가 committed=false/amount=0을 반환하도록 장애 주입해도 SUCCEEDED와 oracle_result=one_full_refund가 저장됐다. 독립 oracle 구현이 아니라 성공 문구를 상수로 기록한다.

수정: DB 최종 상태를 expected outcome과 대조하는 독립 oracle을 구현한다. verify 불일치/쓰기 후 오류는 성공이 아니라 확인 필요 상태로 처리하고 재환불하지 않는다. model/tool 결과 문자열을 oracle로 쓰지 않는다. REQ-03/07/10, T07.

### F07 [P1] 분할 검증이 상수이고 핵심 테스트가 잘못된 조건을 확인

위치: `backend/app.py:181`, `tests/test_m1.py:16`, `tests/test_m1.py:31`.

실제 split은 discovery=2/validation=1/test=0이며 leakage_check는 계산 없이 True다. 해당 테스트도 True를 다시 확인할 뿐이다. 반품 미수령 테스트는 기본 cust-001로 cust-002 주문을 요청하므로 소유권에서 먼저 차단되어 반품 미수령 분기를 검사하지 않는다.

수정: 독립 고객·주문·문장·seed가 있는 30/30/40 사례와 hash/교집합 검사를 구현한다. 의도적으로 누출한 fixture에서 검사 실패를 확인한다. 반품 미수령은 소유권이 맞는 고객으로 요청하고 RETURN_NOT_RECEIVED/0 commit을 단언한다. T07과 REQ-10 완료 전 M2 후보 생성의 평가 기반으로 사용하지 않는다.

## 미완료 항목 — 결함과 구분

- T03: 고액 승인 대기만 있음. approvals 테이블·operator 경로·단회 소비·expiry·재검증·재개가 없다. `approved=true`는 현재 고액 환불을 허용하지 않고 gateway에서 다시 거절된다. 실제 승인 우회 성공이라고 오해하지 말 것.
- T04: 로컬 gateway는 있으나 MCP protocol adapter와 타입 검사/schema hash는 없음. 입력 키 집합만 검사한다.
- T05: 지속 저장, timestamp/duration, provenance, 사용량 null, 일반 예외의 종료 기록, JSONL export 미완료.
- T06: ReAct/model adapter/턴·시간 예산/NAT 없음. 현재 `run_refund`는 수동 고정 실행 흐름이다.
- T01/T12: 표준 HTTP + 정적 HTML/JS로 스택이 바뀌었다. 임시 mock 접근은 가능하지만 FastAPI/React/TS 설계와 불일치하며 호환성 검증 없이 예정 버전만 나열했다. 스택을 유지할지 스펙을 정식 수정할지 결정하고 이유 기록 필요.
- UI: 상단 승인 대기 0은 상수, 내비게이션 버튼은 미연결. 화면 골격으로만 평가한다. 브라우저 렌더링은 이번 검토에서 확인하지 않았다.
- README에서 기존 문서 인덱스가 사라졌으며 “M1 실행 기반 구현” 대신 부분 구현 범위를 명확히 적어야 한다. tasks.md는 현재 전부 unchecked이므로 완료 체크 과장은 없지만 세부 진척 갱신이 필요하다.

## 외부 blocker와 로컬 구현을 나누기

API 키는 실제 Nemotron 실행에 필요하다. 그러나 DB 재검증, 승인, 멱등성, 독립 oracle, 테스트 데이터, trace, bounded loop의 mock 검증은 키 없이 가능하다. NAT 설치 가능 여부와 공식 요구 조사는 모델 키 부재와 별개다. 실행한 설치/네트워크 확인 명령과 실패 원인을 기록하고, 단순히 패키지가 미설치라는 이유로 모든 로컬 작업을 완료 처리하지 않는다.

OpenShell은 현 스펙에서 P1이며 공식 필수로 확인되지 않는 한 M1의 로컬 결함 수정보다 우선하지 않는다. Skill API 요구는 미확인 상태를 유지하되 공식 확인을 계속한다.

## 다음 지시

[M1-fix-instructions.md](M1-fix-instructions.md)를 개발 에이전트에게 전달한다. F01~F07과 로컬 M1 누락을 수정한 후 재검토한다. 실제 키·외부 환경 때문에 남는 항목은 별도 blocker로 기록한다. 제품 전체 M1 완료나 제출 준비 완료로 판정하지 않는다.
