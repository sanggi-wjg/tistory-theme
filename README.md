# 상쾌한기분 티스토리 스킨

[sanggi-jayg.tistory.com](https://sanggi-jayg.tistory.com)의 커스텀 티스토리 스킨 소스.

`src/`의 CSS 조각·JS 모듈을 빌드해 `dist/`에 배포 산출물을 만든다. 티스토리에 API로 올리지 않고,
**위 셋은 편집기에 붙여넣고, 아래 둘은 파일업로드 탭에 올린다.**

| 산출물 | 티스토리에서의 위치 |
|---|---|
| `dist/skin.html` | 스킨 편집 → HTML |
| `dist/style.css` | 스킨 편집 → CSS |
| `dist/index.xml` | 스킨 편집 → index.xml (올리면 **스킨 설정이 초기화된다**) |
| `dist/images/script.js` | 스킨 편집 → 파일업로드 |
| `dist/preview.gif` · `preview256/560/1600.jpg` | 스킨 편집 → 파일업로드. 관리 화면·스킨 보관함의 미리보기 |

## 빠른 시작

Node 20+와 Python 3이 필요하다 (파이썬 스크립트는 표준 라이브러리만 쓴다).

```bash
npm install
npm run check   # 빌드 → 린트 → 프리뷰
open _preview/index.html
```

명령과 작업 흐름은 [USAGE.md](./USAGE.md)에 있다.

## 구조

```
src/skin.html             치환자가 든 스킨 마크업 (빌드가 변환하지 않고 그대로 복사)
src/index.xml             스킨 정보·옵션 변수
src/styles/*.css          tokens → base → layout → content → tistory → components 순으로 합쳐진다
src/js/*.js               index.js를 진입점으로 esbuild 번들
src/assets/placeholders/  카테고리 기본이미지 SVG (data: URI로 CSS에 인라인된다)
src/preview/              관리 화면용 미리보기 이미지 4종 (dist/ 루트로 복사된다)
scripts/build.mjs         빌드
data/*.json               블로그 실측 결과. 인라인색 보정 CSS와 프리뷰 픽스처의 근거
docs/hooks.md             마크업 ↔ CSS ↔ JS 경계면 계약
```

## 이 프로젝트의 전제

**티스토리에는 컴파일러가 없다.** 치환자 오타는 무시되고, CSS 선택자 불일치는 에러를 내지 않으며,
JS 셀렉터는 `null`을 반환하고 끝난다. 셋 다 조용히 실패한다. 그래서 배포 전 린트와 로컬 프리뷰가
필수이고, 배포 후에는 프로덕션 실물을 한 번 더 확인한다.

## 문서

| 문서 | 내용 |
|---|---|
| [USAGE.md](./USAGE.md) | 명령·작업 흐름·배포 절차 |
| [DECISIONS.md](./DECISIONS.md) | 확정 결정과 근거, 플랫폼 제약, 실측 수치 |
| [DESIGN.md](./DESIGN.md) | 디자인 토큰·타이포·컴포넌트 |
| [CLAUDE.md](./CLAUDE.md) | Claude Code 작업 규칙 (worktree·PR) |
