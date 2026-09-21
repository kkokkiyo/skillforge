# M1 수정 및 회귀 검증 보고

- 작성 일시: 2026-09-20 (Asia/Seoul)
- 대상: `/home/dongchan-lee/projects/nvidia-hackothon`
- 기준: `docs/reviews/M1-review.md`, `docs/reviews/M1-fix-instructions.md`
- Git: 미사용. M2는 진행하지 않음.
- 판정 상태: F01~F07 로컬 수정 및 회귀 테스트 통과. 실제 NVIDIA 연동은 미검증.

## 결함별 변경과 검증

| ID | 변경 | 회귀 검증 | 결과 |
|---|---|---|---|
| F01 | `Gateway._issue_refund` 거래 안에서 반품 수령, 주문 version, 정책 hash, quote expiry, 정수·잔여 금액을 재검증 | `test_f01_latest_state_checks`에서 quote 후 반품 상태 변경 시 `RETURN_NOT_RECEIVED`, 환불 0건 단언 | 통과 |
| F02 | HTTP handler가 요청 body의 `customer_id`와 `approved`를 권한으로 사용하지 않고 서버 세션 `cust-001`을 주입 | `test_f02_request_customer_is_not_authority`; localhost POST에 `customer_id=cust-002`를 넣어도 `OWNERSHIP_DENIED` | 통과 |
| F03 | 정적 파일을 resolved `web` root 하위로 제한하고 Content-Type 명시 | `test_f03_static_root_boundary`; localhost `GET /../README.md`가 404 | 통과 |
| F04 | DB transaction을 `RLock + BEGIN IMMEDIATE`로 직렬화하고 환불 insert fault 시 rollback | `test_f04_rollback_has_no_partial_write`: 주문 환불액 0, refunds 0건 | 통과 |
| F05 | mock/live provider 상태 분리. live 요청은 실제 adapter 없을 때 `LIVE_PROVIDER_UNAVAILABLE`, `live_verified=false`; health에 `key_configured`, `adapter_available`, `live_verified` 분리 | `test_f05_live_is_unverified`; localhost live POST도 명시적 실패 | 통과 |
| F06 | verify 불일치를 `NEEDS_RECONCILIATION`으로 종료하고, 독립 DB oracle이 최종 주문/환불 상태를 판정 | `test_f06_verify_mismatch_reconciles`; 성공 문구나 model 결과만으로 SUCCEEDED 기록하지 않음 | 통과 |
| F07 | 독립 synthetic case 100건을 discovery/validation/test 30/30/40으로 생성하고 ID 교집합 검증 | `test_f07_real_splits_and_leak_detection`: 정상 manifest 통과, 의도적 중복 manifest 거절 | 통과 |

## 추가 키 없는 보완

- 엄격한 tool allowlist/입력 타입 검사와 `MCPAdapter` 골격을 추가했습니다.
- `MockModelLoop`에 12-turn bounded loop 검증을 추가했습니다.
- trace에 timestamp, provenance, usage null 필드를 저장하고 JSONL export를 추가했습니다.
- 동일 idempotency key + 동일 payload는 replay 결과를 반환하고, 다른 payload는 `IDEMPOTENCY_CONFLICT`가 되도록 구현했습니다.
- UI의 승인 대기 상수와 live 오해 표시를 제거하고 health 기반 `MOCK · NVIDIA LIVE 미검증` 상태를 표시했습니다.

## 실제 수행한 명령과 결과

| 명령 | 결과 |
|---|---|
| `python3 -m unittest discover -s tests -v` | 11 tests, OK, exit 0 |
| `curl http://127.0.0.1:8090/health` | `mode=mock`, `key_configured=false`, `adapter_available=false`, `live_verified=false` |
| localhost `GET /../README.md` | HTTP 404, 응답 22 bytes |
| localhost POST with forged `customer_id=cust-002` | `DENIED`, `OWNERSHIP_DENIED` |
| localhost POST with `mode=live` | `FAILED`, `LIVE_PROVIDER_UNAVAILABLE`, `live_verified=false` |

The supplied `docs/reviews/M1-review-probe.py` was also rerun. It exits non-zero at its first stale-quote call because the probe still assumes the old vulnerable behavior and does not catch the now-expected `RETURN_NOT_RECEIVED` policy error. Its old output is therefore not reused as a pass signal; the replacement tests above assert the corrected outcomes directly.

## NVIDIA·외부 의존성 상태

- 실제 NVIDIA API/Nemotron 호출: 미실행. API 키를 요구하거나 출력하지 않았습니다.
- NAT 실행/평가: 미검증. 현재 Python 3.12.3 환경에 FastAPI/Uvicorn/Pydantic/pytest가 설치되어 있지 않으며, NAT executable/profile도 확인하지 못했습니다.
- Skill API 공식 endpoint·필수 모델·증빙 방식: 미확인. 따라서 제출 요건 충족으로 주장하지 않습니다.
- OpenShell: 미검증. M1 로컬 보안 결함 수정보다 우선하지 않았습니다.

## 미완료 및 다음 검토 범위

- 승인 객체·운영자 세션·단회 소비·만료·승인 후 재개 API는 아직 미완료입니다. 현재 `approved`는 서버 권한으로 사용되지 않습니다.
- persistent DB는 지원하지만 기본 테스트는 in-memory이며, 운영 trace 완전성·실패 일반 예외·SSE·브라우저 E2E는 추가 검토가 필요합니다.
- FastAPI/React/TypeScript 전환 여부, NAT/Nemotron live adapter, Skill API 확인은 별도 blocker입니다.
- 이 수정 작업에서는 후보 생성, workflow interpreter, 검증/활성화 등 M2를 시작하지 않았습니다.
