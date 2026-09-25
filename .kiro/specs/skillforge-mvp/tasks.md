# 구현 태스크

모든 체크박스는 구현 전이다. 시간은 2인 팀용 사람-시간 추정이며 실측 생산성이나 납기 보장이 아니다. A=backend/agent, B=frontend/evaluation 역할 가칭. 같은 사람이 담당하면 의존 순서대로 진행한다.

## T00 — 제출 요건과 기술 검증 [P0, 5h, A+B, 선행 없음]

- [ ] Skill API 명칭·endpoint·필수 모델·증빙 방법을 공식 안내/문의로 확인하고 docs/08에 근거 기록.
- [ ] NVIDIA 키는 환경변수로만 주입하여 모델 tool call 1회, 한국어 refund intent 10문장, JSON schema 성공 여부 확인.
- [ ] Python/NAT/MCP 호환 조합과 lock 전략 확인. NAT 최소 실행·프로파일 산출물 확보.
- [ ] WSL Docker 및 OpenShell 프로필 설치 가능성만 제한 시간 내 조사. 유료 자원은 생성하지 않음.
- 산출물: docs/08 검증 표, redacted sample run, 선택 모델/버전.
- 완료: 핵심 live 경로 성공 또는 구체적 blocker·대안 기록. 요건 불확실하면 제출 적합 판정 보류.
- 요구사항: REQ-02, REQ-11.

## T01 — 최소 프로젝트 골격 [P0, 2h, A, T00]

- [ ] Python 패키지/FastAPI와 web React/TS/Vite 골격, env example, lockfiles.
- [ ] health endpoint 및 로컬 실행 안내. API 키 없는 테스트 모드 분리.
- 완료: 깨끗한 환경에서 정해진 설치/실행 명령 성공. 무의미한 빈 모듈 대량 생성 금지.
- 요구사항: REQ-02, REQ-09.

## T02 — 모의 DB와 환불 거래 [P0, 5h, A, T01]

- [ ] orders/returns/policies/quotes/refunds/approvals와 seed fixture.
- [ ] 전액 환불, quote 만료, 소유권, 정수 금액, DB transaction, unique 제약.
- 완료: E01/E02/E07/E08/E09의 DB 불변식 검사 통과.
- 요구사항: REQ-01, REQ-08.

## T03 — 정책·승인 Broker [P0, 4h, A, T02]

- [ ] ALLOW/DENY/REQUIRE_APPROVAL와 reason code, bound approval, 단회 소비.
- [ ] 모델에 operator endpoint 노출하지 않음. 승인 시 최신 상태 재검증.
- 완료: E03~E06, 허용하지 않는 조건의 승인 우회 실패 검증.
- 요구사항: REQ-08.

## T04 — 공통 도구와 MCP 계약 [P0, 3h, A, T03]

- [ ] 설계의 6개 tool과 공통 gateway, schema/hash, structured errors.
- 완료: ReAct/Executor에서 같은 정책 함수를 거치며 MCP 입력 조작·잘못된 tool을 거절.
- 요구사항: REQ-01, REQ-02, REQ-05.

## T05 — Trace 저장과 export [P0, 3h, A, T01]

- [ ] SQLite events/runs, monotonic seq, usage null, failure, provenance, redaction.
- 완료: 성공/실패 모두 replay 가능한 이벤트 보존, 비밀정보 제외 검사.
- 요구사항: REQ-03.

## T06 — Nemotron + NAT ReAct [P0, 5h, A, T04/T05]

- [ ] bounded loop, 모델 adapter, timeout/retry, NAT event 연결, mock/live 분리.
- 완료: live 정상 환불 1건과 실패 1건의 redacted 증거. E14 통과.
- 요구사항: REQ-02, REQ-03, REQ-11.

## T07 — 데이터 분할과 상태 Oracle [P0, 4h, B, T02/T05]

- [ ] discovery/validation/test 합성 사례 및 고정 manifest.
- [ ] 최종 DB/예상 판정 기반 독립 oracle, 오류/인젝션/동시성 fixture.
- 완료: split 누출 없음, E15처럼 문장과 DB가 다를 때 잡힘.
- 요구사항: REQ-06, REQ-10.

## T08 — 전체 순서 그룹화와 바인딩 [P0, 5h, A, T06/T07]

- [ ] discovery 실제 trace 수집, 지원 버킷 그룹화, support 출처.
- [ ] 입력·이전 출력·trusted context 참조 유도, 모호성 거절.
- 완료: 새 order ID에서 이전 ID를 복사하지 않음; 최소 5개 독립 source 요구.
- 요구사항: REQ-04.

## T09 — Workflow DSL과 Interpreter [P0, 5h, A, T04/T08]

- [ ] schema/enum predicates, allowlist, 타입·참조 검증, immutable artifact hash.
- [ ] 순차 실행, 단계 실패 중지, 쓰기 이후 reconciliation.
- 완료: E11/E13 통과, 수동 B workflow도 같은 interpreter 사용.
- 요구사항: REQ-05, REQ-07.

## T10 — 검증·승격 Registry [P0, 4h, A, T07/T09]

- [ ] validation 실행, 수치 gate, VERIFIED/ACTIVE/STALE/DISABLED 전이.
- 완료: 실패 후보 활성화 불가, hash 불일치 활성화 불가, 정책 변경 E10 통과.
- 요구사항: REQ-06.

## T11 — Router와 예외 복구 [P0, 3h, A, T06/T10]

- [ ] intent/order 추출, ACTIVE 버전 확인, pre-write fallback, post-write 조정.
- 완료: 모호 주문 확인 요청, 상태 변경으로 적용 불가, 중복 쓰기 없음.
- 요구사항: REQ-07.

## T12 — 화면 골격과 상태 컴포넌트 [P0, 4h, B, T01]

- [ ] 3개 내비게이션, 사례 입력, 타임라인, evidence panel, 배지.
- [ ] loading/empty/error/pending/replay/missing metric.
- 완료: 1280px·키보드 동작, 색만으로 상태 구분하지 않음.
- 요구사항: REQ-09.

## T13 — 운영 API와 UI 연결 [P0, 6h, B, T05/T10/T11/T12]

- [ ] SSE, 실행 상세, trace 출처, 후보 검증/활성화, 승인 상세 연결.
- 완료: 정상→후보→검증→활성→새 요청 재사용 E2E. 중복 클릭/이벤트 차단.
- 요구사항: REQ-06, REQ-08, REQ-09.

## T14 — A/B/C 평가와 보고서 [P0, 5h, B, T07/T11]

- [ ] 동일 조건 paired runs, random order, 지표 정의, JSON/MD report.
- [ ] 360 final runs 목표로 실행하되 API 예산 확인 후 동등 축소 가능.
- 완료: 모든 집계 숫자가 run ID에서 재계산됨, 실패/누락 usage 포함.
- 요구사항: REQ-10.

## T15 — 보안·실패 회귀 [P0, 4h, A+B, T13/T14]

- [ ] E01~E15, 승인 우회/동시 요청/정책 변경/commit 후 응답 손실.
- 완료: unauthorized commit=0, 쓰기 후 blind retry 없음, 알려진 한계 문서화.
- 요구사항: REQ-01~REQ-10 중 관련 항목.

## T16 — NemoClaw/OpenShell 데모 [P1, 최대 6h, A, T00/T06]

- [ ] 검증 가능한 환경에서 inference/MCP allowlist와 read-only artifact 경계 설정.
- [ ] 허용 서비스 연결, 비허용 네트워크, 금지 파일 읽기/쓰기의 실제 판정 기록.
- 완료: 실제 버전·정책·allow/deny 로그. 불가하면 “미검증” 표기와 이유 기록.
- 요구사항: REQ-11. 주최 측 필수 요건으로 확인되면 P0로 올리고 다른 범위를 줄임.

## T17 — 재사용 Skill 안내 export [P1, 2h, A, T10/T16]

- [ ] 활성 workflow에 대해 적용 조건·제외 조건·호출 방법·버전을 담은 MD export.
- 완료: 현재 runtime의 실제 스킬 형식과 호환을 확인하거나 “일반 안내 MD”로 표기.
- 요구사항: REQ-05, REQ-11. 안내 파일이 권한/실행기 역할을 하지 않음.

## T18 — 제출 패키지·3분 영상 [P0, 5h, A+B, T15]

- [ ] 신청서 문구를 완료 기능으로 수정, 실측 표, 출처, 한계 반영.
- [ ] README 실행 가이드, 영상, 링크 담은 PDF/Word 1개 제작 및 육안 확인.
- [ ] 파일명 NVIDIA 해커톤_팀명_SkillForge; GitHub/영상 권한을 비로그인 상태에서 확인.
- 완료: 제출 준비 체크 완료. 신청서 제출·동의는 각 팀원이 직접 수행.
- 요구사항: REQ-10, REQ-11.

## T19 — 제출 전 예비 시간 [P0, 8~16h, A+B, 전 과정]

- [ ] API 장애, NAT 버전 충돌, UX 오류, 제출 파일 수정용 buffer 확보.
- 완료: 9/27 내부 freeze, 9/28 접수 마감 시각 별도 확인.

## 의존성과 범위 절감

핵심 경로: T00→T01→T02→T03→T04→T06→T08→T09→T10→T11→T13→T15→T18.

T05는 backend 작업과, T12는 agent 작업과 독립적으로 사람이 진행할 수 있다. T07은 domain 계약 확정 뒤 착수한다. 추가 인력이 없으면 동시 작업을 전제하지 않는다.

2일째 live ReAct가 안 되면 UI 세부 장식을 줄이고 통합에 집중한다. 4일째 후보 생성이 안 되면 범용 그룹화 확장 대신 정확한 전체 순서 1개만 지원한다. source에서 실제로 유도하지 못한 수동 workflow를 자동 생성이라고 표시하지 않는다. P1은 먼저 삭제하되 공식 제출 필수로 확인된 기능은 삭제하지 않는다.

## M1 수정 라운드 상태

F01~F07 회귀 테스트 통과 및 M1-fixes.md 기록 완료. 전체 태스크는 검토 재승인 전까지 완료 체크하지 않음. M2는 진행하지 않음.

## 최신 구현 상태 (2026-09-20)

아래 상태는 원래 체크박스를 일괄 완료로 바꾸지 않기 위한 증거 대조표다. 과거 문서의 “구현 전”은 최초 계획 시점을 뜻한다.

| Task | 현재 상태 | 근거/잔여 |
|---|---|---|
| T00 | 부분 | 실제 모델/NAT/MCP 확인, Skill API·OpenShell 미확정, 한국어 검사 진행 |
| T01 | 구현·검증 | FastAPI/Pydantic/React/TS/Vite, 잠금 파일. clean-room 재현 최종 점검 필요 |
| T02-T03 | 구현·검증 | 거래·승인·정확한 50만원 경계·단회 소비 회귀 |
| T04 | 구현·검증 | 실제 MCP stdio 6 tools smoke |
| T05 | 구현·검증 | JSONL, provenance, 실패 oracle, 숫자 usage 보존/비밀정보 마스킹 |
| T06 | 구현·검증 | 실제 live/NAT, timeout/retry, NAT tool spans. 기본 NAT ReAct 사용 주장은 하지 않음 |
| T07 | 부분 | 고정 100 fixture 분할·oracle 실행. 계획의 다양한 안전군은 별도 회귀로 검증 |
| T08-T10 | 구현·검증 | 실제 live 5개 source, refs DSL, validation 30, artifact/report hash gate |
| T11 | 부분 | 자연어 의도·모호 주문 확인, 재시작 hold, 읽기 기반 조정. 최종 UI/라우팅 감사 필요 |
| T12-T13 | 구현·검증 중 | React 콘솔, SSE 재접속, expected_hash 활성화, request key. 전체 브라우저 최종 확인 남음 |
| T14 | pilot 완료 | live A/B/C 120회, 원본/manifest/usage/오류 지표. 360회 계획 대비 축소·범위 명시 |
| T15 | 검증 중 | 현재 45개 회귀, 추가 요구사항별 E01-E15 매핑 필요 |
| T16 | 미검증 | docker/openshell 미설치; UI 명시 |
| T17 | 미완료 | 일반 안내 MD export 필요 |
| T18 | 부분 | 문구/대본/PDF 초안 제작. 최종 결과 반영·영상·공개 URL 필요 |
| T19 | 진행 | 제출 준비 audit를 통과하기 전 완료 선언 금지 |

## 2026-09-21 최종 증거 갱신

- T01: ZIP 별도 환경 설치 + 47건 회귀 + 빌드 UI 제공 재현 통과.
- T11~T13: 브라우저에서 승인·후보·검증·활성화·재사용·정책 STALE 흐름 확인(mock 격리 DB). 종합 접근성/장애 UX 감사는 미완료.
- T15: 47건 회귀. E01~E15 대응과 미실험 항목은 docs/reviews/implementation-audit.md에 기록.
- T17: 활성 workflow 일반 안내 MD export 구현·검증 완료. NemoClaw runtime skill 호환 검증 아님.
- T18: PDF 5쪽, 180초 증거 재생 영상, ZIP 준비. 공개 URL·주최 Skill API 확인이 남아 최종 제출 완료 아님.


## T20 — 정책 변화 대응 데모 (2026-09-26, REQ-04/06/09/12)

- [x] 실제 trace 값·타입·완료 순서 검증과 steps 구성, 수동 템플릿 호출 제거.
- [x] 정책 변경 격리 비교와 evidence export, 정책 해시 충돌 방지.
- [x] 불변 부모 계보, 새 후보의 current-policy validation 및 6개 경계 검사.
- [x] React 운영 콘솔에 미리보기 → 적용 → 후보 생성 흐름 추가.
- [x] 신규 8개 회귀 포함 57개 테스트 및 TypeScript/Vite 빌드 통과.
- NVIDIA 새 수집 및 최종 공개 결과는 docs/reviews/policy-change-release.md에 기록한다.
