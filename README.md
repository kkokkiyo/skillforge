# SkillForge

**정책이 바뀌면, 자동화의 근거도 다시 검증합니다.** 팀 TraceMakers.

환불 에이전트의 독립 성공 기록에서 동일한 전체 도구 순서와 인자 참조를 확인하고, 별도 검증과 운영자 활성화를 거쳐 새 주문에 재사용하는 로컬 데모입니다. 합성 주문만 사용하며 실제 결제는 없습니다.

[3분 설명 영상](output/video/SkillForge-evidence-walkthrough.mp4) · [실제 평가 원본](artifacts/eval/eval-dc5a773edccd641d/report.md)

영상은 실제 실행 증거를 시각화한 자막형 재생 자료입니다. 브라우저 화면 녹화가 아니며, 영상 안에서도 이를 표시합니다.

## 빠른 실행 (WSL Ubuntu 24.04 / Python 3.12)

```bash
git clone https://github.com/kkokkiyo/skillforge.git
cd skillforge
python3 setup_runtime.py
.runtime/bin/python -m backend.cli serve
```

브라우저 `http://127.0.0.1:8090`을 엽니다. 다른 포트는 `PORT=8096 .runtime/bin/python -m backend.cli serve`로 설정합니다. 포트 번호는 실행 환경에 맞게 선택합니다.

처음 실행할 때 운영자 토큰이 없으면 `.env.local`에 임의 토큰을 생성합니다. 해당 파일의 `SKILLFORGE_OPERATOR_SESSION` 값을 콘솔의 비밀번호 입력에 넣고 연결합니다. 토큰은 콘솔 메모리에만 남고 새로고침하면 해제됩니다. API 키와 운영자 토큰은 서로 다릅니다.

NVIDIA 키는 프로젝트 `.env`, `.env.local`, `.env.API`, `.enc.API` 중 하나 또는 프로세스 환경의 `NVIDIA_API_KEY`에 설정합니다. 파일을 Git에 넣지 마세요. `.env.example`에는 변수 이름만 있습니다. 키가 없어도 Mock 기능을 사용할 수 있습니다. Live 실패를 Mock 성공으로 바꾸지 않습니다.

## 새 환경 설치

```bash
python3 -m venv .runtime
.runtime/bin/python -m pip install -r requirements-lock.txt
.runtime/bin/python -m pip install -e .
```

Ubuntu에서 ensurepip가 없으면 python3-venv가 필요합니다. sudo 없이 설치할 때는 `python3 setup_runtime.py`가 공식 uv 바이너리를 내려받아 프로젝트 전용 `.runtime` 환경을 만듭니다. Linux x86_64 전용 보조 스크립트입니다. 설치 후 위 실행 명령을 사용합니다.

프런트 소스는 `web/src`의 React/TypeScript입니다. Node와 pnpm이 있는 환경에서:

```bash
cd web
pnpm install --frozen-lockfile
pnpm run build
```

빌드 결과 `web/dist`를 FastAPI가 제공합니다. 제출 압축에는 빌드 결과를 포함하므로 Python 설치 후 별도 Node 빌드 없이 실행할 수 있게 준비합니다. TypeScript/Vite 빌드와 잠금 파일은 유지합니다.

## 데모 순서

1. 운영자 토큰 연결 -> 새 정상 반품 주문 생성.
2. Live + 에이전트 직접 실행 -> 공개 도구 이벤트와 DB oracle 확인.
3. 워크플로 랩에서 출처 기록·DSL·Validation 결과 확인.
4. 검증 후보 활성화 -> 새 정상 주문을 auto 경로로 실행.
5. 고액 승인 -> 승인 발급·재개 -> 중복 시 차단 확인.
6. 정책 영향 미리보기: 승인 기준 500,000원 → 300,000원. 35만원 주문이 자동 환불에서 승인 필요로 바뀌는지 확인.
7. 정책 적용 → 이전 절차 STALE → 새 정책 후보 → 분리·경계 검증 → 활성화.
8. 새 35만원 반품을 실행하고 운영자 단회 승인 후 재개.

정책 기준만 바뀌면 이전 검증 절차의 출처·부모 해시를 보존한 새 후보를 생성하고 재검증합니다. 도구 계약 변경은 새 기록을 수집해야 합니다. 이전 주문을 다시 정상 환불 데모에 사용하면 중복 차단됩니다.

## 검증 명령

```bash
SKILLFORGE_DB=:memory: .runtime/bin/python -m unittest discover -s tests -v
SKILLFORGE_DB=:memory: PYTHONPATH=. .runtime/bin/python tests/http_lifecycle_smoke.py
.runtime/bin/python tests/mcp_smoke.py
.runtime/bin/python -m backend.cli demo
.runtime/bin/python -m backend.cli live
.runtime/bin/nat run --config_file configs/nat-live.yml --input order-001
```

`live`와 NAT live 명령은 실제 NVIDIA API를 사용합니다. `run_live_evaluation.py`는 40개 사례의 실제 모델 비교를 수행하므로 데모 한 번을 위해 실행할 필요는 없습니다. API 호출 간격 기본 2.1초, 총 실행 예산 90초, 요청 timeout 최대 30초, 일시 오류 재시도 1회입니다.

## 증거와 한계

- 실제 Nemotron 및 NAT custom workflow 실행, 실제 MCP stdio 통신 증거: `artifacts/*-evidence.json`.
- 생성 30 / 검증 30 / 테스트 40 사례는 합성 환불 상태이며 산업 데이터 일반화 증거가 아닙니다.
- 초기 live A/B/C 평가에서 429가 많았습니다. 실패도 보존하며 이를 속도 개선 근거로 쓰지 않습니다.
- 57개 회귀 테스트 및 별도 가상환경에서 제출 ZIP 설치·테스트·빌드 UI 제공 재현 통과. 최종 결과는 `docs/reviews/implementation-audit.md`에서 확인합니다.
- NAT는 custom workflow를 호스팅합니다. 자체 bounded loop를 NAT 기본 ReAct agent라고 소개하지 않습니다.
- OpenShell OS 격리와 대회의 ‘Skill API’ 세부 요건은 미확정입니다. 앱의 업무 정책 검사를 OS 격리라고 표시하지 않습니다.
- 루프백 개발용 인증입니다. 인터넷 배포나 멀티테넌트 운영용 인증이 아닙니다.

## 문서

요구사항·설계·태스크는 `.kiro/specs/skillforge-mvp/`에, 화면 설계와 평가 방법은 `docs/02-ux-design.md`, `docs/03-evaluation.md`에 있습니다. Kiro 구조를 참고했으며 Kiro 내부 검증을 실행한 것은 아닙니다. 최신 구현 점검은 `docs/reviews/implementation-audit.md`에서 확인합니다.

공개 GitHub 저장소: https://github.com/kkokkiyo/skillforge. 영상은 위 링크에서 다운로드할 수 있습니다. API 키·운영자 토큰·개인정보는 공개 저장소에 포함하지 않습니다.


## 정책 변화에 대응하는 자동화

핵심 흐름은 `기록 → 출처 바인딩 → 독립 검증 → 활성화 → 정책 영향 비교 → 재검증`입니다. 범용 에이전트 메모리나 세계 최초 자동화라는 주장을 하지 않습니다. 환불 운영자가 어떤 변경으로 어떤 사례의 판정이 바뀌는지 확인할 수 있게 만든 데모입니다.

- [새 구현과 검증](docs/reviews/policy-change-release.md)
- 재현: `PYTHONPATH=. .runtime/bin/python scripts/policy_change_demo.py` (mock)
- 실제 NVIDIA 재현: 위 명령에 `--collect-live --live` 추가. API 호출과 사용량이 발생합니다.
- 기존 A/B/C 수치는 이전 버전의 pilot입니다. 새 정책 실험과 동일한 측정으로 합치지 않습니다.
