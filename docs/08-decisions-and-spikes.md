# 결정 기록과 기술 검증 대장

## 확정한 제품 결정

| ID | 결정 | 이유 |
|---|---|---|
| ADR-01 | SkillForge 환불 단일 업무 | 제한 일정에서 상태 변경과 안전·효율을 함께 시연 |
| ADR-02 | 전체 순서 그룹화 | 부분수열의 검증 생략 위험과 구현 부담 축소 |
| ADR-03 | 제한 JSON DSL interpreter | 임의 코드 실행 배제, 바인딩 검증 가능 |
| ADR-04 | 수동 workflow 비교군 | 기존 자동화 대비 기여를 정직하게 설명 |
| ADR-05 | SQLite 원본·JSONL export | 소규모 재현과 거래 일관성 |
| ADR-06 | 명시적 gate와 운영자 활성화 | 임의 종합 점수로 안전 실패를 상쇄하지 않음 |
| ADR-07 | 쓰기 이후 reconciliation | fallback에서 중복 실행 방지 |
| ADR-08 | 모의 데이터와 원격 추론 | 실제 결제·GPU 환경 구축 범위를 피하고 핵심 검증 집중 |

## T00 기술 검증 표 — 현재 미실행

| 검증 | 상태 | 성공 조건 | 실패 시 조치 |
|---|---|---|---|
| Skill API 요구 해석 | 미확인 | 공식 정의/대상/증빙 URL 또는 주최 측 답변 | 요건 충족 표기 금지, 팀이 문의 |
| NVIDIA 계정 API 접근 | 미실행 | 실제 요청과 model ID 확인 | 키 준비, 독립 mock 개발 진행 |
| tool calling/JSON | 미실행 | schema 맞는 도구 요청과 응답 연결 | 지원 모델 재선정·재평가 |
| 한국어 10문장 | 미실행 | 주문 ID 누락/오인 없이 intent 구분 | 명시적 입력 UI와 언어 한계 기록 |
| NAT 함수 실행·profiling | 미실행 | 최소 예제 및 실제 trace export | 4h 이내 호환 버전 조합 확인 |
| WSL OpenShell | 미실행 | allow/deny 실험, 버전·policy 증거 | 6h 상한 후 격리 미검증 표기 |
| 실제 예산 | 미확인 | rate limit/credit 확인, 10건 pilot 추산 | 동등 평가 규모 축소 |

작업 중 WSL Ubuntu-24.04와 Python 3.12.3 접근은 확인했다. Docker/NAT/모델/API 키의 존재·가용성은 아직 확인하지 않았다. 이 문서 작성 작업에서 모델 추론·결제·배포를 실행하지 않았다.

## 초기 팀 확인 사항

팀명·인원·가용 시간·CS 경험·NVIDIA 계정 준비가 미정이다. 작업을 멈추기보다 2인 합계 80~95h 가정으로 계획했다. 실제 팀 사정 확인 후 docs/04 일정과 task owner를 바꾼다.

## Skill API 확인용 문의 초안 — 발송하지 않음

“온라인 사전 챌린지 안내의 build.nvidia.com Skill API가 구체적으로 어떤 API/제품을 의미하는지 확인 부탁드립니다. Nemotron hosted inference의 tool calling 활용을 의미하는지, 별도 Skill API 사용이 필요한지, 필수 모델 및 제출 시 필요한 사용 증빙이 있는지 알고 싶습니다. 접수 마감 시각도 함께 안내 부탁드립니다.”

## 기록 템플릿

날짜 / 담당 / 확인한 버전 또는 URL / 실행 명령(비밀값 제외) / expected / actual / 증거 파일 / 결정 / 다음 행동을 남긴다. 실패를 성공으로 수정하지 말고 새로운 시도를 별도 기록한다.

## 구현 검증 갱신 (2026-09-20)

| 항목 | 현재 확인 | 증거 |
|---|---|---|
| NVIDIA API / tool calling | 실제 성공 | artifacts/live-evidence.json |
| NAT 1.9.0 | custom workflow live 실행, 공개 Context 함수 span 연계 | artifacts/nat-live-evidence.json, nat-telemetry.jsonl |
| MCP 2.2.0 | 실제 stdio 서버·클라이언트 호출 | artifacts/mcp-evidence.json |
| FastAPI/React/TS | 구현 및 빌드·SSE·타입 검사 | backend/api.py, web/src, tests/test_api.py |
| 키 로딩 | .env.local / .enc.API / .env.API / .env 지원, 출력 금지 | backend/config.py, test_boundaries.py |
| API 제한 | 초기 429 30건 확인, 간격 2.1초 + 제한 retry 추가 | 초기 및 paced 평가 보고서 |
| OpenShell | docker/openshell 실행 파일 없음 | 실제 OS 격리 미검증 유지 |
| Skill API | 공식 검색에서도 세부 정의 확인 못함 | 별도 요구 충족 표기 금지 |

NAT 자체 ReAct를 사용하는 것이 아니라 자체 bounded loop를 NAT custom workflow로 호스팅한다. NAT Context span으로 도구 시작/종료를 기록한다. CLI 경로는 concurrency 1이며, 앱 HTTP 경로는 별도 worker pool을 사용한다.

구체적 성능 수치는 artifacts/eval/eval-dc5a773edccd641d에 기록했다. 40개 동등 사례에서 A 34/40, B 40/40, C 40/40, unsafe commit 0. A의 실패는 provider 500 5건과 견적 참조 오류 1건이다. 이는 로컬 SQLite 모의 업무의 executor-only, 1회 반복 결과이며 공통 자연어 라우팅·외부 결제 비용·운영자 대기 시간을 포함하지 않는다. 일반 서비스 성능으로 확대하지 않는다.
