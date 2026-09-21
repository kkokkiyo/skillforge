# M1 3차 수정 결과

- 작성 일시: 2026-09-20 (Asia/Seoul)
- 대상: `/home/dongchan-lee/projects/nvidia-hackothon`
- 기준: `docs/reviews/M1-round3-review.md`
- 범위: S1~S4만 수정. 기능 확장과 M2는 진행하지 않음.
- 검증 모드: mock/in-memory 및 localhost. 실제 NVIDIA 연동은 미검증.

## S1 — 승인 권한 검증

변경 내용:

- `X-Operator-Id`를 권한 경계로 사용하지 않도록 제거했습니다.
- 서버가 설정한 `SKILLFORGE_OPERATOR_SESSION`과 일치하는 opaque demo session만 `operator-1`로 해석합니다.
- 승인 발급과 승인 후 재개가 같은 session 검증을 거칩니다.
- 유효하지 않은 session은 승인 발급 403으로 차단됩니다.
- 승인 객체에는 operator, order, amount, order version, policy hash, expiry가 계속 binding됩니다.

검증:

- HTTP smoke에서 임의 `X-Operator-Id` 요청을 전송 → 403
- 유효한 `X-Operator-Session: local-demo-session`으로 승인 발급 → 201
- 같은 session과 승인 ID로 고액 환불 재개 → `SUCCEEDED`
- 잘못된 operator로 승인 재개 → `APPROVAL_BINDING_INVALID`
- 만료 승인 및 동시 재개 → 만료 거절, 한 번만 성공

## S2 — 독립 oracle

변경 내용:

- oracle이 expected를 actual 판정에 사용하지 않습니다.
- 실제 주문 누적액, refund 레코드 상태·금액, 반품 수령, 고액 승인 소비 증거를 검사합니다.
- 부분/금액 불일치, 무승인 고액 환불, 반품 미수령 환불은 `UNSAFE_MUTATION` 또는 실패로 판정합니다.

검증:

- 60만 원 주문에 1원 refund 레코드만 삽입 → `passed=false`, `safe=false`
- 승인 없이 60만 원 누적 환불 → 성공 판정 거절
- 반품 미수령 상태의 확정 환불 → 성공 판정 거절
- 정상 승인 흐름은 실제 승인 소비 후에만 성공

## S3 — 100개 사례 정답 검증

변경 내용:

- 고액이더라도 반품 미수령이면 `AWAITING_APPROVAL`이 아니라 `DENIED/RETURN_NOT_RECEIVED`가 되도록 manifest 정답을 수정했습니다.
- discovery/validation/test 전체 100개를 각기 새 DB에 적재하고 실행했습니다.
- 각 사례의 outcome과 거절 reason을 실제 결과와 비교합니다.
- 의도적으로 정답을 오염한 fixture는 평가에서 불일치로 검출됩니다.

검증:

- 100개 모두 독립 fixture load 및 실행
- 모든 사례의 manifest expected와 실제 outcome 일치
- 거절 사례는 `RETURN_NOT_RECEIVED` reason 일치
- 오염된 expected fixture는 통과하지 않음

## S4 — 필수 도구 인자 검사

변경 내용:

- required field subset, 허용 key, 필드 타입을 모두 검사합니다.
- `approval_id`와 `operator_id`는 `issue_refund`에서만 선택 인자로 허용합니다.
- 누락/알 수 없는 key/잘못된 타입은 tool 실행 전에 `PolicyError(INVALID_INPUT)`으로 종료합니다.
- schema canonical hash는 필드·타입·optional 계약을 포함합니다.

검증:

- `get_order({})` → `INVALID_INPUT`
- `get_order({order_id: 1})` → `INVALID_INPUT`
- 알 수 없는 인자 포함 → `INVALID_INPUT`
- optional 승인 인자를 포함한 정상 issue 경로 → 통과
- tool 필드 타입을 바꾼 canonical schema hash → 기존 hash와 불일치

## 실행 명령과 결과

```text
cd /home/dongchan-lee/projects/nvidia-hackothon
python3 -m py_compile backend/app.py backend/server.py tests/test_m1.py tests/http_approval_smoke.py
python3 -m unittest discover -s tests -v
python3 tests/http_approval_smoke.py
```

- py_compile: 통과
- unittest: 22 tests, OK, exit 0
- HTTP approval smoke: 403 부정 테스트 통과, 승인 발급·재개 성공
- smoke run ID: `run-3ed1de7cced0c3`

## 남은 한계

- 운영자 session은 로컬 데모용 설정값이며 실제 사용자 인증/폐기 시스템이 아닙니다.
- 실제 NVIDIA/Nemotron, NAT, Skill API, OpenShell, 브라우저 E2E는 미검증입니다.
- MCPAdapter와 MockModelLoop는 실제 protocol/model 실행이 아니라 제한된 mock 골격입니다.
- M2 후보 생성·workflow interpreter·검증/활성화는 시작하지 않았습니다.
