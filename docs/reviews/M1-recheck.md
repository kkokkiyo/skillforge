# M1 2차 검토 결과

검토일: 2026-09-20. 판정: **일부 해결 확인 / 수정 후 재검토**. 제품 코드 변경 없음. M2 완료 조건을 새로 추가한 것이 아니라 기존 F04/F06/F07과 M1 계약의 미해결 부분을 확인했다.

## 수행한 검증

- 기존 `python3 -m unittest discover -s tests -v`: 11건 통과.
- `M1-recheck-probe.py`: 독립 in-memory DB 및 임시 localhost 서버에서 11개 관찰 출력. 결과는 `M1-recheck-output.jsonl`.
- 보고서·backend·server·테스트·README 정적 검토.
- 재현 코드는 관찰용이며 exit 0이 제품 통과를 의미하지 않는다. 외부 API, 실제 고객, 기존 실행 DB는 사용하지 않았다.
- 실제 NVIDIA/NAT/OpenShell, 브라우저 렌더링, 패키지 설치는 이번에 검증하지 않았다.

## 해결 확인

- F01: write 시 반품/주문 버전/정책 hash/만료/잔여액 검사 추가 확인. 기존 stale quote의 무조건 commit 경로는 수정됨. 다만 아래 R6은 별도 문제.
- F02: HTTP body customer_id가 고객 권한으로 쓰이지 않음. 위조 요청에서 OWNERSHIP_DENIED 재확인.
- F03: GET /../README.md가 404. 기존 경로 이탈 재현 차단.
- F05: live 요청은 LIVE_PROVIDER_UNAVAILABLE 및 live_verified=false 반환.
- F06: 명시적인 fault_verify=False 결과 분기는 확인 필요 상태로 처리. 하지만 실제 exception 경로는 아래 R2처럼 여전히 실패.
- F04: Trace.add에 lock/transaction 확인 추가. 모든 DB write가 같은 경계를 따르지는 않음.
- F07: 목록은 30/30/40으로 늘었으나 실행 가능한 dataset과 의미 있는 oracle은 아직 없음.

## R1 [P1] 견적 생성이 다른 스레드의 transaction을 commit함

위치: `backend/app.py:82`와 `Database.transaction` 39~44.

transaction()으로 lock을 보유하고 주문을 수정하는 동안, 별도 스레드에서 `_quote_refund()`를 실행했다. 견적 INSERT/commit은 lock을 사용하지 않으므로 먼저 열린 거래를 commit했다. 원래 transaction에서 예외를 발생시켜 rollback해도 `SHOULD_ROLL_BACK` 상태가 남았다. 직접 tool 메서드로 타이밍을 고정한 재현이다. 실제 Gateway.call도 trace 기록과 tool 실행 사이에 다른 요청이 진입할 수 있어 같은 경쟁 조건이 가능하다.

수정: quotes뿐 아니라 모든 DB write/commit과 읽기 일관성을 동일한 거래 소유권 규칙으로 관리한다. 요청별 연결을 사용하거나 공유 연결의 전체 접근을 올바르게 직렬화한다. transaction 밖의 임의 commit을 제거한다. Trace.__init__/finish도 함께 점검한다.

완료 검증: barrier/event로 quote 생성과 refund 거래를 교차시킨 실제 스레드 테스트; rollback 후 주문·환불 불변, 불필요한 transaction 오류 없음. 기존 Trace.add만 검사하는 테스트로 대체하지 않는다.

## R2 [P1] 실제 쓰기 후 예외가 조정 상태로 종료되지 않음

위치: `backend/app.py:111~116`.

실제 `_verify_refund`에 TimeoutError를 주입하자 이미 환불 1건이 commit됐지만 예외가 그대로 전파되고 runs.status=RUNNING, finished_at=null로 남았다. 현재 테스트의 fault_verify=True는 예외를 발생시키지 않으므로 이 경로를 못 잡는다.

수정: write 시도 경계를 추적하고 write 이후 timeout/일반 예외는 NEEDS_RECONCILIATION 및 원인·종료 시각·trace를 기록한다. 추가 환불을 실행하지 않는다. write 전 예외는 명확한 FAILED로 종료한다. 정책 거절과 실행 장애를 구분한다.

완료 검증: 실제 tool monkeypatch/fault injection으로 commit 후 timeout, write 전 오류, 상태 조회 실패를 재현하고 최종 상태와 환불 1건 이하를 검사한다.

## R3 [P1] oracle이 기대값을 근거로 판정하며 금지된 변경을 놓침

위치: `backend/app.py:102~103`.

주문 환불액 100원과 COMMITTED 환불 레코드 100원을 만든 뒤 expected=DENIED로 검사하면 passed=true였다. 전액 환불이 아니면 committed=false로 처리하기 때문이다. 정상 저액 주문에 expected=AWAITING_APPROVAL을 주어도 상태 근거 없이 통과한다. 기대값에 따라 actual이 달라져 독립 판정이 아니다.

수정: actual outcome과 안전 불변식을 실제 run·거래·승인·정책 상태 및 실행 전후 snapshot에서 계산한 후 expected와 비교한다. 거절/승인 대기는 해당 실행에서 변경 0건이어야 한다. 기존 환불에 대한 중복 거절은 전후 차이로 판정한다. 금액·레코드·주문 누적액 불일치를 모두 실패로 처리한다.

완료 검증: 금지된 부분 환불, 금액 불일치, 승인 없는 고액 변경, 정상 요청을 승인대기로 잘못 분류한 경우가 실패해야 한다. 실패 코드도 expected reason과 비교한다.

## R4 [P1] 100개 사례가 실행 데이터가 아니며 누출 검사가 ID만 비교

위치: `backend/app.py:124~127`.

목록에는 synthetic-order-000 등 100개가 있지만 기본 DB에는 그중 0개가 존재하고 대응 fixture loader도 없다. 예상 결과는 i%3에서 정해질 뿐 해당 업무 상태와 연결되지 않는다. 다른 case ID를 유지하고 order_id/text/seed를 discovery에서 validation으로 복사해도 validate_splits는 true다. leakage_check도 여전히 상수 true다.

수정: 사례별 독립 DB를 만드는 loader와 실제 주문/반품/정책/승인/장애 입력을 제공한다. 정상·거절·승인 사례가 실제로 실행되어야 한다. case ID뿐 아니라 설계에 명시된 주문/seed/문장 누출과 split 내 중복을 검사하고 결과에서 leakage_check를 계산한다. 고정 manifest hash 검증도 수행한다.

완료 검증: 100개 모두 fixture 로드 및 해당 주문 존재 확인, 사례별 실행과 oracle 연결, 고의적인 order/seed/text 누출 테스트 실패. 관련 workflow를 위한 5개 이상 독립 정상 trace를 실제 mock 실행에서 수집할 수 있어야 한다.

## R5 [P1] quote_id의 provenance가 잘못 기록됨

위치: `backend/app.py:65`.

issue_refund 이벤트에 `quote_id: input.order_id`가 기록된다. 실제 출처는 quote_refund의 출력이다. 이 상태에서 M2가 기록을 컴파일하면 주문 ID를 견적 ID로 바인딩할 수 있다.

수정: 입력·trusted context·이전 step output 출처를 실제 호출 컨텍스트에서 전달하고 검증한다. tool 이름만으로 임의 출처를 쓰지 않는다. quote_id에는 대응 quote step 식별자와 출력 필드를 기록한다.

완료 검증: 서로 다른 주문/견적의 trace에서 각 인자 참조를 평가하면 실제 입력값과 일치해야 한다. 모호한 출처는 unresolved로 남기고 컴파일 대상으로 쓰지 않는다.

## R6 [P2] 정책 변경 후 새 견적도 오래된 정책으로 생성

위치: `backend/app.py:82`.

active 정책을 new-policy로 바꾼 뒤 새로운 run을 시작해도 quote에는 상수 POLICY_HASH가 저장되어 STALE_POLICY로 거절된다. 오래된 견적을 차단하는 것은 맞지만 새 요청은 현재 정책을 기준으로 견적을 만들어야 한다.

수정: 현재 활성 정책을 읽어 version/hash를 snapshot으로 견적에 저장한다. active 정책 유일성과 없는 상태를 명시적으로 처리한다. 재시작 시 seed가 예전 정책을 다시 활성화하지 않는지도 확인한다.

## 남은 M1 범위와 표현 교정

- 승인 객체/운영자 세션/단회 소비/만료/재개는 아직 없음. 키 없이 구현 가능하므로 외부 blocker로 분류하지 않는다.
- `MCPAdapter.call`은 Python 위임 함수다. 실제 MCP initialize/tools/list/tools/call 등 프로토콜 연동 검증이 아니므로 “MCP 연동 완료”로 쓰지 않는다.
- `MockModelLoop.run`은 목록 길이만 확인한다. 모델 응답→도구 실행→결과 관찰 루프, 총예산/요청 timeout/retry를 구현·검증한 것이 아니다.
- TOOL_SCHEMA_HASH는 도구 이름만 해시한다. 인자 필드/타입 변경을 감지하지 못하므로 실제 계약 전체를 canonicalize하여 해시해야 한다.
- 기존 11개 테스트에는 허용된 정상 환불·반품 미수령·고액 대기·동시 요청 전체 회귀가 충분히 유지되지 않았다. 수정 전 테스트를 삭제하는 대신 필요한 행동을 보존한다.
- API body 타입/Content-Length 검증과 일반 오류 응답도 보완 필요. 현재 422 처리 범위가 제한적이다.
- 코드가 여러 문장을 한 줄에 압축해 검토와 변경이 어려워졌다. 수정 구간을 일반 Python 형식과 타입으로 정리한다. 이는 P1 수정의 대체 작업이 아니다.

## 다음 단계

이번에는 범위를 좁혀 **R1~R6 수정 + 실제 승인 흐름**까지 끝낸 뒤 재검토한다. MCP/모델 loop/dataset이 skeleton인지 실행 가능한 구현인지 보고서에 명확히 구분한다. NVIDIA 키가 없어도 이 작업을 진행할 수 있다. M2는 특히 R3/R4/R5가 해결되기 전 시작하지 않는다.

사용자 준비 사항: 실제 모델 호출을 위한 NVIDIA 키를 로컬 환경에 준비하되 채팅/보고서에는 값을 남기지 않는다. 공식 Skill API 요건 확인도 계속 필요하다. 미준비 상태가 로컬 M1의 완료 기준을 낮추지는 않는다.
