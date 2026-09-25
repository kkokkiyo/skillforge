# Policy change release — 2026-09-26

## 결과

SkillForge의 초점을 “빠른 환불”에서 **실행 경험의 재사용 가능성을 정책 변화에 맞춰 검증하는 운영 콘솔**로 보강했다. 환불 업무·6단계 DSL·공통 gateway 범위는 유지한다. REQ-04/06/09/12, T20에 대응한다.

- 요청·완료 trace로 typed symbol table을 구성하고 실제 값·타입·완료 순서와 provenance를 대조한다. 후보 steps는 관측 요청에서 생성하며 manual_workflow를 호출하지 않는다. 마스킹된 idempotency key는 trusted run context로 재생성한다.
- 현재 정책을 고정한 30개 validation과 6개 경계 검사를 통과해야 VERIFIED가 된다. 검증 중 정책 변경을 거래 종료 직전에 다시 검사한다.
- 정책 변경 미리보기는 42쌍의 격리 합성 실행으로 전후 판정·위험 변경·정상 오차단을 비교한다. 50만원→30만원에서 5개 판정 변화, 위험 변경 0, 정상 오차단 0을 관측했다. 금액이 반복되는 경계 사례를 포함하며 산업 대표 42종이라는 주장은 하지 않는다.
- 정책 적용은 base hash compare-and-swap, 이전 후보/검증/활성 버전 STALE 처리. 새 후보는 부모 artifact hash와 원래 출처 정책을 보존한다. 중복 후보 생성 요청은 같은 hash 버전을 반환한다.
- React 콘솔: 미리보기 → 정책 적용 → 새 후보 → 분리·경계 검증 → 운영자 활성화. 35만원 주문 버튼과 비교 JSON 다운로드.

## 실제 검증

| 구분 | 결과 | 범위 |
|---|---|---|
| unittest | 57/57 통과 | 기존 49 + 신규 8; 타입·auth·stale preview·승인·출처 오염·정책 재검증 |
| 안전 행렬 | 36/36 통과 | 기존 12종 × scripted/manual/compiled, 신규 코드로 재실행 |
| TypeScript/Vite | 통과 | 최신 번들 생성 |
| 브라우저 | 전체 흐름 확인 | 별도 합성 DB, 50만원→30만원, 재활성화 후 35만원 승인 대기→승인→성공 |
| 신규 NVIDIA discovery | 5/5 성공 | 새 컴파일러로 후보 구성·30+6 검증·활성화 |
| 정책 변경 전 live | 최초 실패 | NVIDIA_HTTP_500, 모델 호출 시도 7 / 도구 3. 실패 원본 보존 |
| 정책 변경 후 live | 승인 대기 확인 | 35만원, 모델 5 / 도구 5, APPROVAL_REQUIRED |
| 변경 전 별도 재실행 | 성공 | 새로운 격리 주문 run-d21f531772252805031d. 최초 실패를 지우지 않음 |

브라우저 확인: 승인 대기 run-f6df64233bebb512283d, 승인 재개 성공 run-0912d5b316b28c2391d6. 이는 mock UI 흐름이며 실제 NVIDIA 추론 실행과 별도다.

## 원본과 집계 의미

`artifacts/policy-change-evidence.json`에는 신규 discovery 모든 시도, 출처 이벤트, 원본·새 후보, validation·경계 결과, 42쌍 비교, live 비교 2건, 승인 전후 결과가 있다. 최상위 `passed=false`는 최초 live 비교 중 한 건의 공급자 오류를 포함한 종합 판정이다. 핵심 정책 비교 및 재검증은 통과했다. 실패를 성공으로 덮어쓰지 않았다.

`artifacts/policy-change-live-retry.json`은 별도 재실행 증거다. 두 파일을 함께 읽어야 한다. 신규 live 결과를 “무실패”라고 소개하지 않는다. 기존 A/B/C 120회 pilot은 이전 코드 버전의 측정으로 보존한다. 새로운 유지보수 생산성·실서비스 안전성 지표는 측정하지 않았다.

## 재현

```bash
SKILLFORGE_DB=:memory: .runtime/bin/python -m unittest discover -s tests -v
PYTHONPATH=. .runtime/bin/python scripts/safety_matrix.py
PYTHONPATH=. .runtime/bin/python scripts/policy_change_demo.py
# 실제 API 사용량이 발생하는 추가 검증:
PYTHONPATH=. .runtime/bin/python scripts/policy_change_demo.py --collect-live --live
```

기본 실험 결과는 `artifacts/policy-change-demo-latest.json`에 저장하므로 공개 원본 증거를 덮어쓰지 않는다. `--saved-live`는 로컬 운영 DB에 해당 trace가 있고 최신 종료 oracle 이벤트를 갖춘 경우에만 가능하다. 오래된 9/21 기록 일부는 종료 oracle가 없어 새 컴파일러가 거절한다. 검사를 완화하지 않고 신규 live 기록을 수집했다.

## 한계와 제출

범용 워크플로 학습, selective invalidation, formal verification, OS sandbox, 실제 결제를 구현했다고 주장하지 않는다. 정책 임계값 변경만 기존 도구 절차로 재검증하며 도구 계약 변경은 새 기록이 필요하다. 자동화의 안전성이 영구 보증되는 것도 아니다.

NVIDIA Nemotron/NAT/MCP 통합 증거는 제출한다. 주최측 Skill API의 정확한 요건과 NemoClaw/OpenShell 필수 여부는 답변 미수신 상태를 그대로 표시한다. 개인정보·비밀키를 제외한 공개 소스와 PDF/영상의 링크를 사용하고, 신청서 동의·최종 제출은 각 팀원이 직접 수행한다.


## 제출 묶음 재현

2026-09-26 새 ZIP을 별도 가상환경에 설치하여 **57개 회귀 테스트와 빌드 UI 제공을 재현**했다. 실제 로컬 키 값 대조·비밀키/개인 메일/전화번호 패턴·private 파일명·Git blob 이력을 검사했으며 검출 0건이다. 이는 검사한 규칙과 범위의 결과이며 모든 종류의 개인정보 부재를 수학적으로 보장하지 않는다.

PDF 4쪽은 전 페이지 렌더링을 육안 확인했다. 영상 180초/1280×720은 저장된 실제 실행 증거를 시각화한 자막 자료이며 브라우저 녹화가 아니다. Google Form 실제 제출은 수행하지 않았다.
