# 공개 저장소 보안 경계

이 저장소는 합성 주문 환불 데모의 소스와 검토용 문서만 공개합니다.

- `NVIDIA_API_KEY`, `SKILLFORGE_OPERATOR_SESSION` 같은 값은 `.env.API`, `.enc.API`, `.env.local` 또는 프로세스 환경에만 둡니다.
- API 키, 운영자 토큰, 개인정보, 실제 결제 데이터, SQLite 데이터베이스는 커밋하지 않습니다.
- `.gitignore`가 로컬 환경 파일, 런타임, 데이터베이스와 `artifacts/` 작업 산출물을 제외합니다.
- 공개 제출 묶음은 `scripts/package_submission.py`의 credential scan을 통과해야 생성됩니다.
- 키가 노출되었다고 의심되면 NVIDIA 콘솔에서 즉시 폐기하고 새 키를 발급한 뒤 로컬 파일만 교체합니다.

이 데모의 인증은 루프백 운영 콘솔용입니다. 인터넷 공개 운영 서비스의 인증 체계로 사용하지 않습니다.
