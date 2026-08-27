# 사용법

Node 20+ · Python 3. 처음 한 번 `npm install`.

## 명령

| 명령 | 하는 일 |
|---|---|
| `npm run build` | `src/` → `dist/` 배포 산출물 생성 |
| `npm run watch` | 변경 감시 빌드 |
| `npm run lint` | 정적 검증. 오류가 있으면 exit 1 |
| `npm run preview` | 빌드 후 `_preview/`에 11개 페이지 렌더 |
| `npm run check` | 빌드 → 린트 → 프리뷰. **커밋 전에 통과해야 한다** |
| `npm run preview:images` | 관리 화면용 미리보기 이미지 4종 재생성 (macOS + Chrome 필요) |

`dist/`·`_preview/`는 git에 들어가지 않는다. 소스에서 언제든 다시 만든다.

## 작업 흐름

```bash
# 1. 고친다 — src/styles/*.css, src/js/*.js, src/skin.html
# 2. 확인한다
npm run check
open _preview/index.html
# 3. 배포한다 (아래)
# 4. 라이브를 확인한다
```

### 무엇을 어디서 고치나

| 하고 싶은 것 | 파일 |
|---|---|
| 색·간격·폰트 크기 | `src/styles/tokens.css` (리터럴 색은 린트 `TOK001`이 잡는다) |
| 레이아웃·카드·사이드바 | `src/styles/layout.css` · `components.css` |
| 본문 스타일 | `src/styles/content.css` |
| 티스토리 고정 마크업(댓글·카테고리 트리) | `src/styles/tistory.css` |
| 목차·다크모드·코드·라이트박스 등 동작 | `src/js/*.js` |
| 치환자 배치·페이지 영역 분기 | `src/skin.html` |
| 스킨 옵션 변수 | `src/index.xml` |

마크업 ↔ CSS ↔ JS가 공유하는 클래스·속성 이름은 [docs/hooks.md](./docs/hooks.md)가 계약이다.
한쪽만 바꾸면 조용히 끊긴다.

### 린트가 잡는 것

치환자 오타·여닫이 불일치(`SUB*`), 홈/목록 접두사 혼용(`AREA*`), JS 셀렉터 ↔ 마크업 불일치(`BND*`),
토큰 우회(`TOK*`), 인라인색 보정 커버리지(`INL001`), 접근성(`A11Y*`), SEO(`SEO*`).
`INL001`은 보정 CSS가 빌드로 생성되므로 **빌드 후에** 의미가 있다.

### 프리뷰

브라우저는 `<s_list_rep>`를 모른다. 렌더러가 치환자를 `data/posts.json`의 실제 데이터로 바꿔
홈·글(목차 유/무)·카테고리·검색·태그(목록/클라우드)·보관함·방명록·검색결과 0건을 만든다.

```bash
python3 .claude/skills/skin-preview/scripts/render.py --page index,page   # 일부만
```

stderr에 뜨는 `값이 없는 치환자` · `처리 규칙이 없는 그룹 치환자` 경고는 실제 버그 신호다.

## 배포 — 수동

API를 쓰지 않는다(`DECISIONS.md` #15). **첫 배포 전에 현재 스킨을 스킨 보관함에 저장**해 두면
문제가 생겼을 때 되돌릴 수 있다.

```bash
npm run check                                    # 린트 오류 0
python3 .claude/skills/seo-verify-live/scripts/verify.py \
  --base https://<블로그> --save-baseline        # 배포 전 상태를 기준선으로
```

기준선을 찍는 명령은 **오류를 내고 exit 1로 끝나는 것이 정상이다** — 라이브가 아직 이전 스킨이라서다.
단 `V014`가 뜨면 기준선이 저장되지 않은 것이니 원인을 고치고 다시 찍는다.

스킨 편집기에 이 순서로 올린다.

1. `dist/images/script.js` — 파일업로드 (동명 파일이 있으면 먼저 삭제)
2. `dist/preview.gif` · `preview256.jpg` · `preview560.jpg` · `preview1600.jpg` — 파일업로드.
   **바뀌었을 때만.** 이 이름들은 `images/`가 아니라 스킨 **루트**로 간다 —
   목적지가 파일명으로 갈린다(공식 문서에 없는 동작, 2026-08-25 실측).
   없으면 관리 화면과 스킨 보관함에 깨진 이미지가 뜬다
3. `dist/style.css` — CSS 탭
4. `dist/skin.html` — HTML 탭
5. `dist/index.xml` — **바꿀 내용이 없으면 올리지 않는다.** 올리면 스킨 설정이 전부 초기화된다
6. 저장 → 미리보기로 확인 → 적용

zip 업로드는 받지 않는다. 스킨 보관함의 "직접 업로드" 경로는 동작하지 않았다.

### 배포 후

```bash
python3 .claude/skills/seo-verify-live/scripts/verify.py --base https://<블로그> --compare
```

미치환 치환자 잔존, `h1` 개수, 내부링크 렌더, 라이브 CSS ↔ `dist/style.css` 대조, 기준선 대비 회귀를
확인한다. 붙여넣다 잘린 마크업이나 안 올라간 `script.js`는 소스 린트가 원리적으로 잡지 못한다.

스크립트가 못 보는 것은 눈으로 본다 — 댓글 UI, 페이징, 공지 영역, 그리고 **다크모드에서 본문
에디터 컴포넌트가 읽히는가**. 마지막 항목이 이 스킨에서 가장 여러 번 조용히 깨진 자리다:
오픈그래프 링크 카드 제목, 인용문, 첨부 파일, 표, 코드 구문 색. 색이 글에 박힌 것이 아니라
**티스토리 스타일시트**에 있어 인라인 보정이 원리적으로 못 잡고, 라이트에서는 멀쩡해 보인다
(DESIGN.md §5.2b, DECISIONS.md 결정 32).

카테고리 트리는 더 이상 여기 없다 — 리스트형 치환자로 바꾸면서 인라인 색이 사라졌다(결정 31).

## 실측 갱신

설계 결정이 실측에 걸려 있다. 글이 늘면 다시 센다.

```bash
python3 .claude/skills/blog-census/scripts/census.py --posts            # 목록만 (빠르다)
python3 .claude/skills/blog-census/scripts/census.py --posts --bodies   # 본문까지 (느리다)
```

`--bodies`가 있어야 `data/inline-styles.json`이 갱신되고, 그래야 다크모드 인라인색 보정 CSS가
현재 글과 맞는다. `data/*.json`은 git으로 공유되므로 **갱신했으면 커밋한다.**
