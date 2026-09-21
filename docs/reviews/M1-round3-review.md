# M1 3차 검토 — 남은 수정 범위

검토일: 2026-09-20. 판정: **수정 후 재검토**. 제품 코드는 변경하지 않았다. M2의 기능 범위를 늘리는 대신 기존 승인·평가·입력 계약의 오류만 이번 수정 대상으로 고정한다.

## 실제 검증 결과

- `SKILLFORGE_DB=:memory: python3 -m unittest discover -s tests -v`: 19건 통과.
- `SKILLFORGE_DB=:memory: python3 tests/http_approval_smoke.py`: 성공. 검토 run ID `run-3bf60023efc0a2`.
- 별도 `M1-round3-probe.py`: 독립 DB로 100개 fixture 전부 실행, 미등록 operator 헤더, oracle 오류, 필수 인자 누락 확인. 결과는 `M1-round3-output.jsonl`.
- 이번 결과는 mock correctness 검증이다. 모델 성능 benchmark·live·NAT·격리·브라우저 E2E 성공을 뜻하지 않는다.
- 관찰용 probe는 exit 0이 통과 신호가 아니다. 이전 19개 테스트와 추가 검증이 확인하는 범위가 다르다.

## 해결 확인된 진전

이전 견적 commit의 transaction 간섭(R1), write 후 TimeoutError의 NEEDS_RECONCILIATION 종료(R2), 현재 활성 정책의 새 견적 반영(R6), 기본 run의 quote_id provenance 수정은 코드와 회귀 테스트로 확인했다. fixture loader·필드별 누출 검사·실제 승인 저장 및 소비도 추가됐다. 다만 승인 **기록의 binding**과 승인하는 사람의 **권한 검증**은 다른 문제다.

## S1 [P1] 임의 헤더로 운영자를 자칭하고 자기 승인 가능

위치: `backend/server.py:24~26`, `backend/server.py:30`.

서버에 등록한 적 없는 `X-Operator-Id: arbitrary-unregistered-review-user`로 POST /api/approvals 요청 시 HTTP 201로 승인 ID가 발급됐다. 같은 헤더와 ID로 고액 order-002를 실행하자 SUCCEEDED, 환불 1건이 됐다. 기존 smoke는 헤더가 일치하는 성공 경로만 검사하므로 이 권한 우회를 발견하지 못한다.

로컬 데모에서 정식 사용자 인증 제품을 만들 필요는 없다. 다만 서버가 미리 신뢰한 운영자 세션/불투명 토큰을 검증해야 한다. 호출자가 선언한 ID만으로 권한을 생성해서는 안 된다.

수정 범위:

- 서버 측에서 발급·설정한 데모 운영자 credential/session을 검증하고 operator ID를 서버에서 도출한다.
- 승인 발급과 재개 모두 같은 신뢰 경계를 사용한다. body/header의 ID 문자열은 권한이 아니다.
- 세션 발급 API를 아무 호출자에게 무인증으로 열어 같은 우회를 만들지 않는다. agent/tool 실행 컨텍스트에는 승인 credential을 주지 않는다.
- 운영자 credential을 문서·Git·로그에 저장하지 않는다. 만료/폐기/다른 운영자 세션을 검사한다.

완료 테스트: 미인증, 임의 ID, 잘못된/만료 credential은 승인 발급·재개 불가; 유효 운영자만 승인 가능; 승인 후 정책/주문 변경·만료·재사용 거절; 거래 실패 시 승인 소비도 rollback.

## S2 [P1] oracle이 불일치 환불과 무승인 고액 환불을 성공 판정

위치: `backend/app.py:128~134`.

order-002 누적 환불액을 600,000원으로 설정하고, 실제 refund 레코드는 **1원**, 승인 레코드는 **0건**인 상태를 넣었다. oracle은 expected=SUCCEEDED에 대해 passed=true, safe=true를 반환했다. 환불 레코드 금액·허용 조건·유효 승인·실행 전후 변화는 검사하지 않고 주문 누적액=결제액만 보고 있다.

수정 범위:

- 해당 실행의 before/after, 실제 run outcome 및 reason, 환불 레코드 합계·금액·상태, 주문 누적액, 정책/반품/소유권, 고액 승인 증거를 검사한다.
- actual은 expected에서 독립적으로 계산한다. 금액이 맞더라도 승인 없는 고액 commit은 UNSAFE_MUTATION이다.
- 거절·대기는 해당 실행의 신규 변경이 없어야 한다. 이미 환불된 주문의 중복 요청 거절은 기존 환불과 새 변경을 구분한다.
- 단순 최종 DB snapshot으로 판단 불가능한 항목은 passed=true 대신 증거 부족으로 반환한다.

완료 테스트: 1원 레코드/60만원 누적 불일치, 금액이 맞는 무승인 고액 commit, 반품 미수령 commit, 적법한 승인 환불, 기존 환불의 중복 거절, outcome/reason 불일치를 각각 검사.

## S3 [P1] 실제 fixture 두 건의 정답과 oracle 판정이 잘못됨

위치: `backend/app.py:161~162`, `backend/app.py:132`.

100개 독립 fixture를 모두 실행한 실제 결과: 성공 77, 거절 15, 승인 대기 8.

| 사례 | 업무 상태 | manifest 정답 | 실제 결과 | oracle |
|---|---|---|---|---|
| case-000 | 고액 + 반품 미수령 | 승인 대기 | DENIED / RETURN_NOT_RECEIVED | 잘못 통과 |
| case-070 | 고액 + 반품 미수령 | 승인 대기 | DENIED / RETURN_NOT_RECEIVED | 잘못 통과 |

정상 차단된 backend를 고칠 문제가 아니다. 반품 미수령 같은 필수 조건 실패가 고액 승인보다 우선한다는 스펙대로 **정답 데이터와 oracle**을 고친다. oracle은 금액만으로 대기를 추론하면 안 된다.

완료 테스트: manifest의 100개 전부를 각기 분리된 DB에서 load→run→독립 평가하고 outcome과 reason 일치를 단언. 의도적 정답 오염을 평가기가 검출하는 테스트도 추가. manifest 변경은 버전/hash 변경을 기록한다. 이번은 사전 fixture 정확성 감사이며 향후 모델 성능 실험용 최종 test 튜닝으로 혼동하지 않는다.

## S4 [P2] 필수 도구 인자가 누락돼도 스키마 검사 통과

위치: `backend/app.py:80~82`.

Gateway.call('get_order', {})가 INVALID_INPUT 대신 KeyError를 발생시킨다. optional 인자 허용을 추가하면서 required 집합 포함 검사가 사라졌다. 따라서 모델 도구 호출 오류가 구조화된 계약 오류로 처리되지 않는다.

수정: required subset + allowed keys + 필드별 타입을 모두 검사한다. optional approval/operator 필드를 사용하는 경우 실제 계약 hash에도 필수/선택·타입이 반영되어야 한다. 실행 권한은 S1의 trusted context에서 전달한다.

완료 테스트: 필수 누락, 알 수 없는 인자, 잘못된 타입은 도구 실행 전 INVALID_INPUT. optional 정상 입력과 schema hash 변경 테스트 유지.

## 에이전트에게 전달할 지시

```text
docs/reviews/M1-round3-review.md를 읽고 S1~S4만 우선 수정해줘.
새 기능·프레임워크 전환·UI 확장은 이번 작업에 넣지 마.
특히 X-Operator-Id를 인증으로 취급하지 말고 서버가 검증하는 로컬 데모 세션으로 바꿔줘.
oracle은 승인 증거와 실제 환불 금액·실행 전후 상태를 검증하게 해줘.
100개 fixture를 모두 실행해 outcome과 reason을 대조하고,
잘못된 정답/불일치 상태가 반드시 실패하는 테스트를 넣어줘.
현재 19개 테스트의 통과 범위를 보존하고 새로운 부정 테스트를 추가해줘.
결과는 docs/reviews/M1-fixes-round3.md에 S ID별 근거와 함께 남겨줘.
외부 NVIDIA 연동은 미검증 상태를 유지하며 M2는 아직 진행하지 마.
```

S1~S4 수정 후에는 **mock 기반 M2의 로컬 구현 착수 가능 여부**와 **M1 전체 완료 여부**를 분리해 판정한다. 실제 ReAct/NAT/MCP 경로가 없는 상태에서 자동 생성의 실사용 효과나 NVIDIA 사용 요건 충족을 선언하지 않는다.
