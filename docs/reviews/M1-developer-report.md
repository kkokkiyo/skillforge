# M1 개발 완료 보고

- 작성 일시: 2026-09-20 (Asia/Seoul)
- 프로젝트 경로: `/home/dongchan-lee/projects/nvidia-hackothon`
- 대상 commit SHA 또는 Git 미사용 사유: Git 저장소가 초기화되어 있지 않아 SHA 없음
- 미커밋 변경 여부와 목록: Git 미사용. `backend/`, `tests/`, `web/`, `requirements.txt`, `pyproject.toml`, `.env.example`, `README.md`, `.kiro/specs/skillforge-mvp/tasks.md`
- 완료 태스크 / 미완료 태스크: M1 골격의 일부 검증(T02 거래 핵심, T04 gateway 핵심, T05 trace 핵심, T12 화면 핵심) / T00, T01 전체 골격, T03 승인 소비, T04/T05/T07/T12의 전체 완료 조건, T06
- live / mock / replay 구분: 이번 검증은 모두 `mock`; replay는 미구현; NVIDIA live는 실행하지 않음

## M1 수정 라운드 상태

검토 후 F01~F07을 수정했고 상세 근거는 `docs/reviews/M1-fixes.md`에 기록했다. 수정 라운드의 회귀 테스트 8건과 localhost 경계 검증은 통과했다. 승인 객체/운영자 세션, NAT/Nemotron adapter, FastAPI/React 전환, M2 workflow 기능은 아직 완료로 체크하지 않는다.

## 구현과 요구사항

| REQ/T ID | 실제 구현 파일·심볼 | 동작 | 검증 근거 |
|---|---|---|---|
| REQ-01 / T02 | `backend/app.py:Database`, `Gateway` | 합성 주문/반품, 소유권·반품 수령·기환불·정수 KRW, SQLite unique/transaction | `python3 -m unittest discover -s tests -v` 5건 |
| REQ-02 / T00/T06 | `backend/server.py`, `.env.example` | mock/live 표시 경계와 모델 키 이름 안내. live 호출은 아직 없음 | `/health` 결과 `mode=mock`, `nvidia_live=false` |
| REQ-03 / T05 | `backend/app.py:Trace` | run ID, monotonic seq, tool requested/completed, policy, completion, redaction | 정상 run `run-f7a6297449930e`, 단위 테스트 |
| REQ-08 / T03 | `run_refund`, `Gateway._issue_refund` | 500,000원 이상 승인 대기, write 전 차단 | 고액 승인대기 테스트, HTTP 결과 |
| REQ-09 / T12 | `web/index.html`, `web/styles.css`, `web/app.js` | 실행/절차/평가 내비게이션, 사례 입력, timeline/evidence, 미측정·오류 상태, 키보드 focus | 정적 UI 골격 및 HTTP API 연동 |
| REQ-10 / T07 | `split_manifest`, `tests/test_m1.py` | discovery/validation/test 분리 필드와 split hash, leakage flag, 독립 oracle 입력 골격 | manifest endpoint 및 분할 테스트 |

## 재현 방법

- 환경·의존성 버전: WSL Ubuntu-24.04, Python 3.12.3. 현재 환경에는 FastAPI/Uvicorn/Pydantic/pytest가 설치되어 있지 않음. 실제 실행은 Python 표준 라이브러리로 수행.
- 설치/실행 명령과 실행 디렉터리:

  ```text
  cd /home/dongchan-lee/projects/nvidia-hackothon
  python3 -m unittest discover -s tests -v
  SKILLFORGE_MODE=mock python3 -m backend.server
  ```

- 필요한 환경변수 이름(값 제외): `SKILLFORGE_MODE`, `NVIDIA_API_KEY`, `NVIDIA_MODEL`, 선택적으로 `PORT`
- 초기 데이터 생성과 테스트 DB 격리 방법: 각 `Database()`가 in-memory SQLite seed를 새로 생성한다. 외부 결제/고객 데이터 없음.
- UI 주소·동작 확인 순서: 서버 실행 후 `http://127.0.0.1:8090/` → 사례 선택 → `실행` → timeline과 DB oracle 표시 확인.

## 실제 수행한 검증

| 명령 | 결과·종료 코드 | 시각 | 로그/보고서 경로 |
|---|---|---|---|
| `python3 -m unittest discover -s tests -v` | 5 tests, OK, exit 0 | 2026-09-20 | `tests/test_m1.py` |
| `curl http://127.0.0.1:8090/health` | `status=ok`, `mode=mock`, `nvidia_live=false` | 2026-09-20 | 이 보고서 |
| `curl http://127.0.0.1:8090/api/cases` | split hash와 discovery/validation/test 응답 확인 | 2026-09-20 | 이 보고서 |
| HTTP `POST /api/runs` order-001 | `run-f7a6297449930e`, `SUCCEEDED`, `COMMITTED`, 89,000 KRW, exit 0 | 2026-09-20 | `/api/runs/{run_id}/events` |

## 실제 NVIDIA 사용 증거

- 모델 ID·설정 hash·run ID: 실제 NVIDIA 모델 호출 없음. `run-f7a6297449930e`는 `mode=mock`이며 NVIDIA 증거가 아님.
- NAT 실행/평가/프로파일 산출물: 없음. 현재 런타임에 NAT 확인/실행하지 못함.
- Skill API 요구 확인 상태·출처: 미확인. 공식 endpoint·필수 모델·증빙 방법을 확인하지 못했으므로 제출 요건 충족으로 표시하지 않음.
- OpenShell 사용/미사용/미검증 및 근거: 미검증. 실제 버전/allow-deny 로그 없음.

## 실패·한계·남은 작업

- 알려진 결함과 재현 방법: 승인 API/단회 승인 레코드가 아직 없고, `approved=true`도 서버에서 승인 객체를 검증하지 않는 M1 골격이다. live 모델 adapter, NAT event 연결, 12턴/90초/30초 timeout 예산, retry, SSE, candidate compiler, workflow interpreter는 미완료다.
- 환경 제약 때문에 못 한 검증: FastAPI 계열 패키지는 설치되어 있지 않았고 외부 네트워크/API 키가 없어 live NVIDIA/NAT/Skill API를 실행하지 못했다. 100-case split과 독립 DB validation/test도 미완료다.
- 사용자 결정/계정 작업이 필요한 항목: NVIDIA 계정/API 키 주입 및 공식 Skill API 요구 확인, 실제 모델 접근 권한, 팀/제출 계정 확인.
- 스펙 변경 내용과 이유: 설치되지 않은 FastAPI를 런타임 필수로 가정하지 않고 표준 라이브러리 HTTP 서버로 M1 mock 검증을 가능하게 했다. `requirements.txt`에는 예정 조합을 고정했지만 설치 성공이나 호환성을 주장하지 않는다.
