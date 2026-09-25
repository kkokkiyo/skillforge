# SkillForge MVP 요구사항

상태: 설계 기준 v0.1 / 구현 전. 기간: 2026-09-20~09-28. EARS 방식의 조건→행동으로 기술한다.

## 용어와 가정

- 운영자: 로컬 모의 서비스 담당자. 고객/주문/정책은 합성 데이터다.
- 성공: 문장의 그럴듯함이 아니라 독립 상태 oracle이 expected outcome과 DB 상태 일치를 판정한 경우.
- 안전 사례: 정상 환불뿐 아니라 정당한 거절·승인 대기·중복 처리 방지를 포함한다.
- 승인: 운영자 세션이 서버에 남긴 단회 사용 기록. 모델 출력이나 주문 메모는 승인이 아니다.
- 목표 수치: 아직 실측 결과가 아니다. 평가 규약은 docs/03-evaluation.md 참조.

## REQ-01 모의 업무와 변경 불변식 — P0

CS 운영자로서 정상 환불과 예외를 재현하고 싶다.

- WHEN 유효한 고객이 자신의 주문을 조회하면 THE SYSTEM SHALL 해당 고객의 주문만 반환한다.
- WHEN 환불이 요청되면 THE SYSTEM SHALL 소유권, 반품 수령, 정책, 기환불 상태, 정수 KRW 금액을 서버에서 검증한다.
- IF 금액이 0 이하이거나 잔여 결제액보다 크거나 정책이 불일치하면 THE SYSTEM SHALL 환불을 거부한다.
- WHEN 같은 주문에 동시 또는 반복 환불이 들어오면 THE SYSTEM SHALL 전액 환불 레코드를 최대 하나만 확정한다.
- WHEN 테스트가 시작되면 THE SYSTEM SHALL 격리된 seed snapshot을 사용한다.

## REQ-02 실제 NVIDIA 실행과 경계 — P0

개발자로서 실제 에이전트 실행을 입증하고 싶다.

- WHEN live 모드에서 요청하면 THE SYSTEM SHALL 확인된 NVIDIA 모델을 호출하고 모델 ID, 요청 시간, 사용량 가용 여부를 남긴다.
- WHEN 모델이 도구를 요청하면 THE SYSTEM SHALL allowlist와 입력 스키마를 검증한 뒤 공통 gateway로 전달한다.
- IF 12회 모델 턴 또는 총 90초 예산을 초과하면 THE SYSTEM SHALL 종료 상태와 원인을 반환한다. 각 모델 요청 timeout은 최대 30초, 일시 오류 재시도 1회는 총예산 안에서만 허용한다.
- IF API 인증/제한/도구 JSON 오류가 발생하면 THE SYSTEM SHALL 실제 실패를 표시하며 몰래 mock 성공으로 전환하지 않는다.

## REQ-03 실행 기록 — P0

- WHEN 실행 이벤트가 발생하면 THE SYSTEM SHALL run ID, 순서, 도구/인자 출처, 결과 상태, 시간, 모델 호출 수, 정책 버전을 기록한다.
- WHEN 실행이 실패하거나 거절되면 THE SYSTEM SHALL 실패 원인과 DB oracle 결과도 보존한다.
- WHERE API가 token usage를 제공하지 않으면 THE SYSTEM SHALL null 및 사유를 남기며 0으로 기록하지 않는다.
- THE SYSTEM SHALL API 키·실제 개인정보·숨은 추론 전문을 trace에 저장하지 않는다.

## REQ-04 기록에서 후보 유도 — P0

- WHEN 동일 정책·도구 버전·업무 유형의 독립 성공 기록이 5건 이상 같은 전체 도구 순서를 보이면 THE SYSTEM SHALL 해당 source trace ID를 가진 후보를 생성할 수 있다.
- WHEN 인자를 일반화하면 THE SYSTEM SHALL 입력 또는 이전 단계의 타입이 맞는 출력 참조로만 바인딩한다.
- IF 참조가 모호하거나 필수 단계가 누락되면 THE SYSTEM SHALL 자동 추측 대신 후보를 거절한다.
- THE SYSTEM SHALL support 분모(해당 버킷의 모든 성공 기록)와 count를 표시하고 이를 업무 성공률과 구별한다.

## REQ-05 제한된 실행 DSL — P0

- WHEN 후보가 컴파일되면 THE SYSTEM SHALL 선형 단계, 입력 스키마, 참조, 도구 버전, 정책 해시, 전/후조건을 포함한 불변 JSON을 생성한다.
- IF 임의 코드, 앞으로의 참조, 알 수 없는 도구/필드, 타입 불일치가 있으면 THE SYSTEM SHALL 실행 전 거절한다.
- WHEN 단계를 실행하면 THE SYSTEM SHALL 최신 도구 결과를 읽으며 과거 결과값을 재사용하지 않는다.

## REQ-06 검증과 활성화 — P0

- WHEN 후보 검증을 요청하면 THE SYSTEM SHALL 생성에 쓰지 않은 validation 사례를 독립 DB에서 재실행한다.
- IF 유효 정상 사례 성공률 ≥95%, 안전 사례 기대 판정 100%, unauthorized mutation 0, trace 완전성 100%이면 THE SYSTEM SHALL VERIFIED로 바꿀 수 있다.
- WHEN 운영자가 VERIFIED 후보를 활성화하면 THE SYSTEM SHALL 검증 보고서와 artifact hash를 고정하고 ACTIVE로 전환한다.
- IF 정책·도구 계약이 변경되면 THE SYSTEM SHALL 이전 ACTIVE 버전을 STALE로 표시하고 신규 자동 실행을 막는다.

## REQ-07 라우팅과 중단 — P0

- WHEN 요청 의도와 입력이 확인되고 ACTIVE 절차 버전이 현재와 일치하면 THE SYSTEM SHALL 실행 전 조건 확인 후 해당 절차를 사용한다.
- IF 주문 식별이 모호하면 THE SYSTEM SHALL 사용자 확인을 요구하며 임의 주문을 선택하지 않는다.
- IF 적용 가능한 절차가 없으면 THE SYSTEM SHALL 제한된 ReAct로 처리한다.
- IF 쓰기 시도 전 적용 조건이 맞지 않으면 THE SYSTEM SHALL 사유를 남기고 예외 안내 또는 ReAct로 전환할 수 있다.
- IF 쓰기 시도 이후 오류/timeout이 발생하면 THE SYSTEM SHALL NEEDS_RECONCILIATION으로 이동하고 상태 조회 외 추가 쓰기를 막는다.

## REQ-08 정책과 승인 — P0

- WHEN 환불액이 500,000 KRW 이상이고 다른 조건은 유효하면 THE SYSTEM SHALL 승인 대기로 전환한다. 이 경계는 데모용 정책이다.
- WHEN 승인하면 THE SYSTEM SHALL operator ID, order ID, amount, policy hash, order version, expiry를 묶어 단회 승인한다.
- IF 승인 이후 주문/금액/정책이 변경되거나 10분이 지나면 THE SYSTEM SHALL 승인 재사용을 거부한다.
- IF 소유권 위반·반품 미수령·기환불이면 THE SYSTEM SHALL 승인으로도 우회할 수 없는 거절을 반환한다.
- THE SYSTEM SHALL ReAct·고정·자동 생성 경로 모두 동일 정책을 적용한다.

## REQ-09 콘솔과 증거 — P0

- WHEN 사용자가 실행하면 THE SYSTEM SHALL 실행 방식, 진행 상태, 도구 타임라인, 판정 이유를 표시한다.
- WHEN 후보 상세를 열면 THE SYSTEM SHALL source trace, DSL 단계, validation 결과, 버전을 연결해서 보여준다.
- WHERE 지표가 없으면 THE SYSTEM SHALL “미측정”을 표시한다.
- WHEN 오류·빈 목록·연결 끊김·승인 대기가 발생하면 THE SYSTEM SHALL 각각 구별되는 상태와 다음 행동을 보여준다.
- THE SYSTEM SHALL 키보드 탐색, 텍스트 상태 배지, 1280px 화면에서 핵심 흐름을 지원한다.

## REQ-10 평가와 재현 — P0

- WHEN benchmark를 실행하면 THE SYSTEM SHALL 같은 데이터/정책/모델 설정으로 ReAct·수동 workflow·자동 workflow를 비교한다.
- THE SYSTEM SHALL 성공률, 모델/도구 호출, token usage, p50/p95 지연, 라우팅 오류, unsafe attempt/commit을 분리해 보고한다.
- THE SYSTEM SHALL 생성/검증/최종 평가 데이터를 분리하며 측정 오류와 실패를 제외하지 않는다.
- WHEN live 증거를 제출하면 THE SYSTEM SHALL 재현 설정과 run ID를 포함하고 synthetic input 및 replay 여부를 밝힌다.

## REQ-11 NVIDIA 통합 증거 — P0/P1

- P0: WHEN 통합 검증이 완료되면 THE SYSTEM SHALL Nemotron 요청 및 NAT 실행/평가 증빙을 보고서에 연결한다.
- P0 제출 게이트: THE TEAM SHALL 주최 측 Skill API 요구의 의미와 사용 증빙을 확인한다. 일반 NIM API 성공만으로 충족했다고 표시하지 않는다.
- P1: WHEN OpenShell 프로필이 켜져 있으면 THE SYSTEM SHALL 허용/차단 실험 로그와 실제 버전을 표시한다. 미실행이면 “격리 미검증”으로 표시한다.

## 비목표

실제 결제, 개인정보 처리 서비스 운영, 주소 변경, 부분 환불, 임의 코드 생성, 임의 DAG, 온라인 모델 학습, 멀티테넌트 운영 인증, 자동 배포/신청서 제출은 이번 범위 밖이다.


## REQ-12 정책 변경 영향과 재승격 (2026-09-26)

- WHEN 운영자가 승인 기준 변경을 미리보기하면 THE SYSTEM SHALL 활성 절차를 구·신 정책의 격리 DB에서 실행하고 기대/실제 판정·위험 변경·정상 오차단을 비교한다.
- THE SYSTEM SHALL 운영 DB의 주문·환불·승인·run을 미리보기로 변경하지 않는다. 비교 보고서는 별도 저장한다.
- WHEN 미리보기 후 적용하면 THE SYSTEM SHALL 기본 정책 해시를 거래 안에서 재확인하고 이전 후보·검증·활성 절차를 STALE로 바꾼다.
- WHEN 재사용 절차를 새 정책에 연결하면 THE SYSTEM SHALL 원본을 수정하지 않고 부모 artifact hash와 원래 출처 정책을 가진 새 CANDIDATE를 만든다.
- THE SYSTEM SHALL 현재 정책 기대 판정의 validation 30개 및 경계 6개를 통과하고 운영자가 활성화하기 전에는 새 후보를 재사용하지 않는다.
- IF 도구 계약이 바뀌면 THE SYSTEM SHALL 기존 절차의 정책 재연결을 거절하고 새 기록 수집을 요구한다.
- REQ-08의 500,000원은 초기 기준이다. 운영자 변경 이후에는 현재 활성 정책의 정수 기준을 적용한다.
