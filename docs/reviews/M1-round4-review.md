# M1 4차 검토 — 남은 두 항목

검토일 2026-09-20. 판정: **수정 후 재검토**. 새 기능 요구 없음. 이전 S1(신뢰된 승인 세션), S2/S3(oracle 정확성)의 미해결 부분만 남긴다. 제품 코드는 수정하지 않았다.

## 확인된 결과

- 기존 unittest 22건 통과.
- HTTP 승인 smoke 통과: run-7d0ed89fb589d8.
- 별도 메모리 DB로 100개 사례 모두 실행: manifest expected와 실제 run outcome 전부 일치.
- 필수 인자 누락/타입/알 수 없는 key 회귀 테스트 통과.
- 무승인 고액과 반품 미수령 commit의 일부 차단 검증 추가 확인.
- NVIDIA/NAT/OpenShell/실제 MCP/실제 모델 loop는 미검증 또는 mock 골격 그대로다.

추가 재현은 `M1-round4-probe.py`, 출력은 `M1-round4-output.jsonl`, 검토 코드 해시는 `M1-round4-hashes.txt`에 있다. probe는 관찰용이며 exit 0은 제품 통과가 아니다.

## A [P1] 운영자 세션 미설정 시 공개 기본값으로 승인 가능

위치: `backend/server.py`의 DEMO_OPERATOR_SESSION 및 operator_from_request.

`SKILLFORGE_OPERATOR_SESSION`을 **제거한** 새 프로세스에서 `X-Operator-Session: local-demo-session`으로 승인 요청했다. HTTP 201로 발급됐고, 이어서 고액 환불도 SUCCEEDED였다. 코드의 기본값이므로 사용자가 비밀값을 설정하지 않아도 누구나 같은 문자열로 운영자 권한을 얻는다.

수정은 단순하다: 공개 기본 credential을 없애고 미설정·빈 값이면 승인 기능을 닫는다. 명시적으로 설정한 비밀값만 검증한다. 서버가 안전한 임의 세션을 생성하는 방식을 선택해도 되지만 agent에 노출하면 안 된다. 지금은 환경변수 기반 로컬 데모 방식이면 충분하고, 정식 계정 시스템을 만들 필요는 없다.

필수 테스트:

1. env 없음 + 헤더 없음 → 403.
2. env 없음 + 이전 공개 기본 문자열 → 403.
3. env가 빈 값 + 빈 헤더 → 403.
4. 명시적으로 임시 secret 설정 + 틀린 값 → 403.
5. 명시적으로 임시 secret 설정 + 올바른 값 → 승인 및 재개 성공.

테스트는 각 설정을 새 프로세스 또는 명시적 config 주입으로 분리한다. smoke도 자체 임시 secret을 주입해야 하며 제품 기본값에 의존하지 않는다. 실제 secret을 출력하지 않는다.

## B [P1] oracle의 금액 검사와 거절 우선순위 미완료

위치: `backend/app.py`의 independent_oracle.

### B1 금액 불일치

정상 저액 order-001을 환불한 뒤 **refund 레코드 amount_krw만 1원으로 변경**했다. 주문 누적 환불액은 89,000원이다. oracle은 passed=true, safe=true를 반환했다. 승인 유무나 반품 상태는 정상으로 유지하여 금액 검사만 분리한 재현이다.

현재 고액 1원 테스트는 무승인 조건 때문에 실패할 수 있어 금액 일치 검사가 실제로 있는지 증명하지 못한다. refund 레코드 금액과 주문 누적액/허용 환불액을 명시적으로 비교해야 한다.

### B2 fixture의 run과 oracle 불일치

case-000/case-070은 반품 미수령이므로 run=DENIED, expected=DENIED로 올바르게 수정됐다. 하지만 independent_oracle은 여전히 금액만 보고 AWAITING_APPROVAL로 판정한다. 기존 100개 테스트는 run 결과만 검사하고 oracle 결과를 호출하지 않아 이를 놓쳤다.

필수 테스트:

1. 정상 저액 환불 → oracle 성공.
2. 그 상태에서 refund 레코드 금액만 1원으로 변경 → passed=false, safe=false.
3. 유효 승인을 소비한 정상 고액 환불 → oracle 성공; 그 후 레코드 금액만 변경 → 실패.
4. 고액 + 반품 미수령 + 변경 없음 → oracle DENIED.
5. 100개 전부 load→run→독립 oracle을 호출하여 expected/outcome/reason/oracle을 함께 검사.
6. 의도적으로 잘못된 expected를 넣으면 실제 evaluator 호출이 실패 판정해야 한다. 단순 문자열 NotEqual 테스트로 대체하지 않는다.

고정 500,000 상수 대신 실제 활성 정책 기준을 사용하고, 필수 조건 실패를 승인 필요보다 먼저 판정한다. 실제 run 결과를 무조건 복사하는 oracle로 바꾸지 말고 DB의 불변식과 변경 증거를 독립 검사한다. 향후 후보 승격에는 안전 위반·증거 부족을 성공으로 처리하지 않는다.

## 개발 에이전트에게 보낼 명령

```text
docs/reviews/M1-round4-review.md의 A와 B만 우선 수정해줘.
운영자 세션의 공개 기본값을 제거하고 미설정/빈 설정은 fail-closed로 처리해줘.
oracle에 실제 refund 금액 일치 검사와 반품 미수령 우선 판정을 넣어줘.
문서의 필수 부정 테스트를 한 조건씩 분리해서 실행해줘.
100개 사례는 run뿐 아니라 실제 independent_oracle까지 전부 검증해줘.
기존 22개 테스트를 유지하고 smoke는 자체 임시 secret을 주입해줘.
제품 코드·계정의 비밀값은 출력하지 마.
결과를 docs/reviews/M1-fixes-round4.md에 남겨줘.
외부 NVIDIA 미검증 상태는 유지하고 M2는 재검토 후 진행해줘.
```

이번 남은 항목은 API 키 없이 해결 가능하다. 이 두 항목 해결 뒤 mock 기반 M2 착수 여부를 별도로 판정한다. 현재부터 M1 전체 완료나 NVIDIA 제출 요건 충족을 의미하지는 않는다.
