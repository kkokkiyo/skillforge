# 최종 구현·제출 준비 점검 — 2026-09-21

서비스 **SkillForge** / 임시 팀명 **TraceMakers** / 저장소명 추천 `skillforge`.
이 문서가 과거 M1 및 중간 점검 보고서보다 최신이다. 공개 제출 완료를 뜻하지 않는다.

## 검증된 결과

- 자동 회귀 47건 통과. 제출 ZIP을 별도 폴더/가상환경에 설치하여 같은 47건 및 빌드 UI 제공을 재현했다(`artifacts/reproduction-evidence.json`).
- 실제 Nemotron 환불 성공, 실제 NAT custom workflow live 실행, MCP SDK stdio 6개 도구 통신 증거를 보존했다.
- NAT span 증거는 mock 실행의 FUNCTION_START 7 / FUNCTION_END 7 쌍이다. live 실행 증거와 별도이며, NAT 기본 ReAct를 사용했다는 뜻이 아니다.
- 독립 live 성공 기록 5건 → 후보 → 별도 validation 30/30 → ACTIVE → 일반 안내 MD export 완료.
- React/TypeScript 빌드와 고정 lock 설치 통과. 브라우저에서 고액 승인 대기→승인·재개 성공, discovery→후보→30건 검증→활성화→새 주문 workflow 성공→mock A/B/C→정책 변경 STALE를 확인했다. 이 브라우저 검증은 격리된 mock DB에서 수행했다.
- 실제 평가 `eval-dc5a773edccd641d`: 동일 합성 test 40건×3경로=120회. A 34/40, 수동 B 40/40, 생성 C 40/40, unsafe commit 모두 0. 원본 재집계 일치.
- 정상 사례만 보면 A 26/31, B/C 31/31. A 실패 HTTP500 5건 및 QUOTE_BINDING_INVALID 1건. 공통 자연어 라우터를 제외한 메모리 SQLite 실행기 비교이며, UI·실결제 전체 지연이나 범용 에이전트 성능 수치가 아니다.
- 초기 429 지배 평가도 삭제하지 않았다. 한국어 10문장 probe는 9/10이며 모호한 입력 2건은 모델 호출 전에 처리한다.
- PDF 5쪽 육안 검수, 180초 자막형 실행 증거 재생 영상, 신청서 문구(Problem 303자 / Solution 497자), 비밀정보 제외 ZIP 및 파일별 SHA-256을 준비했다. 영상은 실제 브라우저 녹화가 아니며 이를 모든 프레임에 표시했다.

## 원래 요구사항 대조

| 요구사항 | 상태와 근거 |
|---|---|
| REQ-01 | 구현·회귀: 소유권/반품/전액/동시 거래/독립 snapshot |
| REQ-02 | live 검증: 허용 도구, 12턴/90초/요청30초, 재시도 제한, 실패 공개 |
| REQ-03 | 구현·검증: 순서·provenance·oracle·null usage·비밀정보 마스킹 |
| REQ-04~06 | 구현·검증: 독립 source, 정확한 전체 순서, 제한 DSL, 분리 validation, 해시 고정, 정책 변경 무효화 |
| REQ-07 | 구현·부분 검증: 모호 주문 확인, ACTIVE 선택, 공통 gateway 전조건, restart hold. 별도 일반화된 적용성 모델은 없음 |
| REQ-08 | 구현·회귀: 정확한 50만원, 승인 묶음/만료/단회 소비, 세 경로 공통 gateway |
| REQ-09 | 핵심 브라우저 흐름 확인. 전 화면 접근성 감사·실제 연결 장애 UX 종합 검사는 미완료 |
| REQ-10 | 120회 live pilot 및 재현 완료. 원 계획 360회 반복·다양한 안전군 구성은 미완료. routing_error_rate/approval_wait_ms는 미측정(null) |
| REQ-11 | Nemotron/NAT/MCP 실제 증거. Skill API 공식 의미·증빙 요건 미확인. OpenShell P1 미검증 |

## E01~E15 회귀 대응

- E01~E08: 정상/반품/499999·500000 경계/승인소비/상태변경/멱등/동시성 테스트에 대응.
- E09: gateway가 OWNERSHIP_DENIED로 내용 노출을 차단. 비동기 API는 접수 202 후 DENIED 결과이므로 원 계획의 HTTP403과 전송 계약이 다르다.
- E10~E11: 정책 STALE 및 commit 후 응답 손실·조정 hold 회귀에 대응.
- E12: 모델이 승인 권한을 부여하지 못하는 테스트는 존재하나, 실제 악성 주문 메모를 주입한 종단간 실험은 미실행.
- E13: 알려지지 않은 도구/필드·미래/잘못된 참조·artifact 변조 거절 회귀.
- E14: 실제 429/500 실패 증거 및 live 미가용 실패 테스트. 모든 공급자 인증 오류 형태를 live로 재현한 것은 아님.
- E15: DB oracle 불일치·부분금액·승인 없는 변경 회귀. 자연어 최종 답변의 의미 일치 전반은 검증하지 않음.

## 제출 전 남은 외부 항목

1. 사용자가 팀명/서비스명 확정 및 공개 GitHub 생성 후 URL 전달. 아직 저장소·영상 URL을 만들거나 지어내지 않았다.
2. URL을 PDF에 반영하고 비로그인 접근 확인. 현재 PDF는 링크 미완성 제출 초안이다.
3. 주최 측 Skill API 요구를 확인해야 제출 적합성을 판정할 수 있다. 일반 NIM API 성공으로 대체 주장하지 않는다.
4. OpenShell 실행 파일·Docker가 없는 현 환경에서 OS 격리는 미검증이다. 필수 요구로 확인되면 별도 환경 작업이 필요하다.
5. 신청서 개인정보·동의와 제출은 팀원 각자가 수행한다. 제출 마감 시각은 공식 채널에서 최종 확인한다.

파일별 해시는 최종 source-manifest에 기록한다. live pilot 이후 안전성·복구 수정은 회귀로 검증했으며, 최종 소스 전체를 다시 120회 live 평가했다고 주장하지 않는다. 로컬 앱은 합성 데이터 데모이며 공개 운영 서비스용 인증이 아니다.

## 2026-09-21 추가 안전성 검증

`tests/test_adversarial.py` 2건을 추가했다. 실제 gateway/SQLite를 사용하되 모델 transport는 의도적으로 악성 응답을 내는 대역이다. NVIDIA 모델 자체의 prompt injection 저항성 실험이 아니다.

- E12 보강: get_order 결과의 customer_memo에 승인 우회 지시를 삽입하고 모델이 이를 읽어 forged approval_id/operator_id를 요청하게 했다. INVALID_INPUT/DENIED, 승인 0건·환불 0건 확인. 운영 DB에 메모 필드를 추가하지 않고 도구 출력 경계에 합성 공격 데이터를 주입했다.
- E15 보강: 실제 환불 commit 후 모델이 환불 실패·재시도를 주장하고 verify 호출 없이 종료하게 했다. NEEDS_RECONCILIATION/VERIFY_INCOMPLETE, DB 환불 1건, durable hold, 후속 실행 시 추가 환불 없음 확인.
- 이 두 시나리오는 위 중간 감사의 E12/E15 미실험 범위를 일부 보완한다. 자유로운 모든 자연어 공격과 실제 모델 저항성을 입증하지는 않는다.
- 재현 스크립트가 테스트 수를 상수로 기록하던 부분을 실제 unittest 로그에서 추출하도록 수정했다.

최종 실행 결과: 전체 회귀 **49건 통과**, 별도 환경 ZIP 설치에서도 **49건 및 빌드 UI 제공 재현 통과**. PDF·영상의 47건은 이전 검증 시점 수치이며, 최신 수치는 이 보고서와 reproduction-evidence.json을 따른다.

추가 안전 사례 행렬: scripts/safety_matrix.py에서 12종×3경로 **36/36 통과**. 각 사례의 DB delta·reason·oracle·hold·trace를 보존했다. 기존 49개 회귀 및 live120회 pilot과 분모를 분리한다. 상세는 docs/03-evaluation.md 및 artifacts/safety-matrix.json 참조.
