# 공개 저장소 검사 — 2026-09-21

기준 소스는 WSL `/home/dongchan-lee/projects/nvidia-hackothon`이다. Windows 작업 사본의 이전 커밋은 원격과 다른 이력이며 push 기준으로 사용하지 않는다.

- 저장소: https://github.com/kkokkiyo/skillforge
- 첫 공개 검증 커밋: `c417ae84833227bb688c70173038ce5d11ad997e`
- 비로그인 GitHub API에서 공개 상태, 커밋 일치, 추적 파일 120개 확인.
- 공개 manifest의 119개 파일 및 이력의 blob 123개 검사 통과. 실제 로컬 NVIDIA 키·운영자 세션 값과 대조했다. 알려진 토큰, 개인 이메일, 전화번호 패턴도 검사했으며 값 자체는 출력하지 않았다.
- `.env.API`, `.enc.API`, `.env.local`, SQLite 파일과 `source-original.txt`는 원격 tree에 없다.
- 검토된 합성 실행 증거와 빌드 UI를 포함했다. 작업용 DB와 나머지 artifacts는 제외했다.
- 독립 환경에서 회귀 49건 및 빌드 UI 제공 재현 통과. 별도 안전 행렬 36/36과 live 120회 pilot은 각각 구분한다.

이 검사는 특정 키·파일·패턴 및 공개 대상에 한정된다. 모든 형식의 개인정보가 없음을 수학적으로 보장하지 않는다. 실데이터나 새 자격증명을 추가하면 공개 전에 같은 검사를 다시 수행한다.

주최 측 Skill API 문의는 사용자가 발송했고 답변 대기 중이다. OpenShell은 미검증이다. 이 두 상태를 실제 NVIDIA 모델/NAT/MCP 실행 성공과 혼동하지 않는다.
