# 제출 manifest

- 팀명: TraceMakers
- 서비스명: SkillForge
- 추천 저장소명: skillforge
- GitHub: https://github.com/kkokkiyo/skillforge (공개 소스·실행 증거 업로드 및 비로그인 조회 확인)
- 영상 URL: 아직 생성하지 않음
- 모델: nvidia/nemotron-3-super-120b-a12b
- 실제 비교 평가: eval-dc5a773edccd641d, 합성 Test 40건 x A/B/C, 1회 반복
- 이전 실패가 많은 평가: eval-1fbaadfc4c465a19, 삭제하지 않고 보존
- 실제 모델/NAT/MCP 증거: artifacts의 evidence JSON
- 공개 대상 파일의 SHA-256: source-manifest.json
- 팀원 개인정보와 .env/.enc.API/운영자 토큰/SQLite DB는 제출 묶음에 포함하지 않음
- 로컬 실행 주소는 심사자용 배포 URL이 아님

PDF에는 공개 GitHub URL을 반영합니다. 영상 링크와 공식 Skill API 요구 확인 후 최종 제출 여부를 판단합니다. Google Form 개인정보와 동의·최종 제출은 각 팀원이 직접 합니다.

## 현재 전달 파일과 제출 순서

1. `output/pdf/NVIDIA 해커톤_TraceMakers_SkillForge.pdf`가 폼에 올릴 문서 초안이다. 링크가 확정되면 PDF를 갱신한다.
2. `submission/SkillForge-review-bundle.zip`은 소스·빌드 UI·증거·문서·영상의 검토용 묶음이다. GitHub에는 묶음의 `skillforge/` 내용을 저장하되 키와 DB를 추가하지 않는다.
3. 서비스명은 `SkillForge`, 신청서 답변은 `final-form-answers.md`에서 복사한다.
4. `output/video/SkillForge-evidence-walkthrough.mp4`는 3분 설명 자료다. 실제 화면 녹화가 아닌 실행 증거 재생 자료로 소개한다.
5. GitHub URL 확정→문서 반영→비로그인 열람 확인→팀원 각자가 같은 프로젝트 자료로 신청서를 작성한다. 각자 개인정보·동의를 확인하고 직접 제출한다.
6. Skill API 공식 요구 확인 전에는 기술 요건 충족을 확정하지 않는다.

2026-09-21 공식 웹 자료 재조회 결과와 주최 측 문의 초안은 `docs/reviews/skill-api-gate.md`에 있다. 교육·행사 페이지 HTTP 200, 신청서 직접 조회 HTTP 401. Skill API 요건 확인 게이트는 해소되지 않았다.
