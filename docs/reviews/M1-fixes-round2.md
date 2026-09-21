# M1 2차 수정 결과

- 작성 일시: 2026-09-20 (Asia/Seoul)
- 대상: `/home/dongchan-lee/projects/nvidia-hackothon`
- 기준 문서: `docs/reviews/M1-recheck.md`, `docs/reviews/M1-recheck-instructions.md`
- Git: 미사용
- M2: 진행하지 않음
- 결과: R1~R6 및 키 없이 가능한 운영자 승인 흐름 구현. 회귀 테스트 19건과 HTTP 승인 smoke test 통과.

## 항목별 수정·재현·검증

| ID | 구현 | 실제 재현/검증 | 결과 |
|---|---|---|---|
| R1 | `_quote_refund`를 `Database.transaction()` 안으로 이동해 lock/BEGIN IMMEDIATE 경계를 공유 | `test_r1_quote_rolls_back_with_other_transaction`: 다른 thread가 quote를 시도하는 동안 원 거래를 강제 rollback하고 주문 상태·quote 결과 확인 | 통과 |
| R2 | write 이후 일반 예외/timeout을 `NEEDS_RECONCILIATION`으로 종료하고 finished_at·trace를 기록 | `test_r2_post_commit_exception_reconciles_and_stops`: 환불 commit 후 `_verify_refund` timeout 주입, run 상태와 환불 1건을 단언 | 통과 |
| R3 | `independent_oracle`가 expected를 actual 결정에 사용하지 않고 주문 누적액·refund 레코드·전액 불변식으로 판정 | `test_r3_oracle_rejects_partial_or_wrong_pending`: 부분 환불을 DENIED로 기대하거나 정상 주문을 AWAITING_APPROVAL로 기대해도 실패 | 통과 |
| R4 | `load_case`로 100개 synthetic order/return fixture를 실제 DB에 적재하고 order/text/seed/id 교집합 검사 | `test_r4_fixtures_load_and_leak_fields`: 100건 적재 확인 및 order/text/seed 누출 fixture 거절 | 통과 |
| R5 | `Gateway.call(..., provenance)`를 추가하고 issue_refund의 `quote_id`를 `steps.quote.quote_id`로 기록 | `test_r5_quote_provenance_is_previous_step`: 실제 issue 이벤트 provenance JSON을 읽어 입력 order ID가 아닌 이전 step 출력인지 확인 | 통과 |
| R6 | 견적 생성 시 상수 hash 대신 현재 active policy hash/version snapshot 사용 | `test_r6_new_quote_uses_current_policy`: 기존 정책 비활성화 후 `new-policy`를 활성화하고 새 quote hash 확인 | 통과 |

## 실제 승인 흐름

- `approvals` 테이블과 `Database.create_approval/consume_approval` 추가
- operator ID, order ID, amount, order version, policy hash, expiry에 승인 binding
- 단회 소비 및 만료·조건 변경·정책 변경 재검증
- HTTP `POST /api/approvals`는 `X-Operator-Id` 세션 헤더를 요구
- HTTP `POST /api/runs`는 body의 `approved`를 권한으로 신뢰하지 않고 승인 ID와 operator session으로 재개
- 동시에 두 번 재개하면 한 건만 성공하고 다른 건 `ALREADY_REFUNDED`/승인 재사용 거절로 종료

검증 명령:

```text
python3 -m unittest discover -s tests -v
python3 tests/http_approval_smoke.py
```

결과:

- `19 tests`, `OK`, exit 0
- HTTP 승인 smoke: 승인 ID 발급, operator binding, 고액 환불 재개 `SUCCEEDED`
- smoke run ID: `run-fa03d265c51345`

## 추가 보완

- tool schema hash가 도구 이름뿐 아니라 canonicalized 인자 필드·타입을 포함하도록 변경
- 기존 정상/거절/중복/고액 대기·transaction 회귀 테스트 유지
- `split_manifest`의 `leakage_check`가 상수가 아니라 id/order/text/seed 교집합 결과로 계산

## 외부 의존성 및 미완료

- 실제 NVIDIA/Nemotron 호출: 미실행. API 키를 요청·출력하지 않았으며 `live_verified=false` 정책을 유지
- NAT 실행/평가, Skill API 공식 요건 확인, OpenShell: 미검증. 외부 인증/공식 요구 확인이 필요한 별도 항목
- MCPAdapter와 MockModelLoop는 실제 MCP protocol/model 실행 완료가 아니라 제한된 mock 계약 골격으로만 표시
- 브라우저 E2E, FastAPI/React 전환, 후보 생성/workflow interpreter 등 M2 범위는 진행하지 않음
- 승인 API는 로컬 데모 세션 기반이며 실제 사용자 인증 시스템이 아님
