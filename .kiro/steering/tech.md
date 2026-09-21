---
inclusion: always
---
# 기술 방향

WSL Ubuntu-24.04, Python 3.12, FastAPI/Pydantic, SQLite, React/TypeScript/Vite. NVIDIA Build의 Nemotron 원격 추론을 우선 검증한다. NeMo Agent Toolkit(NAT)으로 실행·평가·프로파일링을 연결하고 MCP는 도구 경계로 쓴다. NemoClaw/OpenShell은 T00 결과에 따라 별도 실행 프로필로 연결한다.

모델 버전과 패키지 버전은 T00에서 재현 가능한 조합을 lock한다. JSON workflow는 제한된 참조와 allowlist만 허용한다. 공통 broker와 backend가 권한·정책·동시성·멱등성을 담당한다. LLM의 승인 문구는 권한이 아니다.
