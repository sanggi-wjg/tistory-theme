---
name: skin-preview
description: "티스토리 스킨을 로컬 브라우저에서 확인하는 mock 렌더러. src/skin.html의 치환자를 data/posts.json의 실제 275편 데이터로 치환해 홈·글(목차 유/무 2종)·카테고리·검색·태그(목록/클라우드 2종)·보관함·방명록·검색결과0건·보호글 11개 페이지를 생성한다. 스킨을 수정한 뒤 '어떻게 보이는지 보자', '프리뷰', '미리보기', '렌더링해봐', '화면 확인', '브라우저로 열어봐' 요청 시 반드시 이 스킬을 사용할 것. 티스토리 API를 쓰지 않으므로 이것이 유일한 확인 수단이다."
---

# 로컬 프리뷰 — 치환자 mock 렌더러

브라우저는 `<s_list_rep>`를 모른다. `skin.html`을 그냥 열면 깨진 화면이 나온다. 이 스킬은 티스토리 서버가 하는 치환을 로컬에서 흉내내, **실제 글 275편 데이터**로 렌더링한다.

## 실행

```bash
# 빌드 먼저 (style.css, images/script.js가 있어야 제대로 보인다)
npm run build

# 11개 페이지 전부
python3 .claude/skills/skin-preview/scripts/render.py

# 일부만
python3 .claude/skills/skin-preview/scripts/render.py --page index,page

open _preview/index.html
```

출력은 `_preview/pages/{타입}.html`, 목차는 `_preview/index.html`이다.

## 생성되는 페이지

| 타입 | body_id | 확인할 것 |
|---|---|---|
| `index` | `tt-body-index` | 홈 그리드. 카드 12개 중 2개가 대표이미지 없음(실제 비율) |
| `page` | `tt-body-page` | 글 본문. 인라인 오염·코드블록·표·figure가 모두 들어 있다 |
| `category` | `tt-body-category` | 목록 2단. 20개 중 17개 썸네일 |
| `search` | `tt-body-search` | 검색 결과 |
| `tag` | `tt-body-tag` | 태그 목록 |
| `archive` | `tt-body-archive` | 보관함 |
| `guestbook` | `tt-body-guestbook` | 방명록 |
| `empty` | `tt-body-search` | **검색 결과 0건.** `<s_list_empty>` 확인용 |
| `page_toc` | `tt-body-page` | 소제목 3개 이상이라 **목차가 생기는 글.** `page`와 body_id가 같지만 `body.no-toc` 유무로 레이아웃이 갈린다 — 실측 68%가 이쪽이다 |
| `tag_cloud` | `tt-body-tag` | `/tag` **클라우드.** `tag`(=`/tag/이름` 목록)와 body_id가 같고 렌더되는 영역이 다르다 |
| `protected` | `tt-body-page` | **보호글.** 비밀번호 폼만 나온다. **전용 body_id가 없어** 일반 글과 CSS로 구분되지 않는다 — 레일이 그대로 서므로 `.protected`가 본문과 같은 x에 서는지 본다 |

## 본문 픽스처가 재현하는 것

`page` 페이지의 본문(`ARTICLE_BODY`)은 실제 글에서 관찰된 패턴을 그대로 담고 있다. 여기서 안 깨지면 실물에서도 대체로 안 깨진다.

- 래퍼 `<div class="tt_article_useless_p_margin contents_style">`
- 인라인 `color: #000000` `#333333` `#252525` — 다크에서 죽는 색
- 인라인 `color: #eeffff` — **라이트에서 죽는 색**
- 인라인 `color: #006dd7` `#ee2323` — **강조색.** 빌드 생성기가 죽이지 않고
  `--link`·`--error`로 **옮기는** 쪽이다. 나머지 색은 전부 `--ink-body`로 눌리므로
  이 둘이 없으면 생성기의 **두 갈래 중 한 갈래가 한 번도 안 그려진다.**
  2026-08-27에 채웠다 — 그 구멍 때문에 결정 44가 `--error`를 "쓰는 데가 없다"고
  잘못 적었다(그 토큰의 유일한 사용처가 바로 이 경로다)
- 인라인 `background-color: #f8f8f8` — 다크에서 흰 상자
- 인라인 `font-family: AppleSDGothicNeo`
- `data-ke-language="javascript"`인데 내용은 셸 — **라벨을 믿으면 안 되는 사례**
- 언어 미지정 코드블록
- **마크다운 펜스 3종** — `<code class="language-python">`(칠하고 라벨) ·
  `language-typescript`(번들에 없어 **라벨만**) · `language-info`(언어가 아니라
  표식·오타 부류라 **라벨도 안 붙는다**). 결정 43의 세 갈래를 화면에서 가른다
- **12줄짜리 코드블록** — `code.js`의 `LINES_FOR_NUMBERS`(8)를 넘겨 줄번호 거터를
  켠다. 2026-08-27까지 픽스처 최대가 5줄이라 `.code-wrap.has-lines`와
  `.code-lines`의 CSS `counter` 번호가 **로컬에서 한 번도 그려진 적이 없었다**
- `<figure class="imageblock">` · 4열 `<table>` · `<blockquote data-ke-style>` · 인라인 `<code>` · 외부링크
- **티스토리 에디터 컴포넌트 6종** (`EDITOR_COMPONENTS`) — 오픈그래프 링크 카드, 인용 `style1`+`cite`,
  인용 `box`, 첨부 파일 블록, 표 `style12`, `.another_category`. 전부 티스토리가 **라이트 전용 색을
  박아 둔** 것들이라 다크에서 사라졌던 요소다 (DESIGN.md §5.2b). `.another_category`는 티스토리가
  페이지 안 `<style>`로 넣는 `!important` 규칙까지 픽스처에 함께 들어 있다

**픽스처는 "열기 + 알맹이 + 닫기"로 조립한다.** 예전에는 `ARTICLE_BODY.replace("</div>", …, 1)`로
목차용 변형을 만들었는데, 알맹이에 `<div>`가 하나라도 생기면 **첫 `</div>`가 안쪽 것**이 되어
추가분이 조용히 엉뚱한 자리에 붙는다. 오픈그래프 카드를 넣으면서 실제로 그렇게 됐다.

## 경고를 읽어라

렌더러는 stderr로 두 종류의 경고를 낸다. **둘 다 실제 버그의 신호다.**

| 경고 | 의미 | 조치 |
|---|---|---|
| `값이 없는 치환자: [##_xxx_##]` | 치환자 이름 오타이거나 렌더러 미지원 | 화이트리스트 확인. 실재하는 치환자면 `globals_for()`에 추가 |
| `처리 규칙이 없는 그룹 치환자: <s_xxx>` | `handle_group()`에 규칙 없음 | 규칙 추가 |

값이 없는 치환자는 출력에 **빨간 점선 테두리**로 표시되므로 브라우저에서도 눈에 띈다.

## 티스토리 스타일시트를 함께 싣는다 — 순서가 곧 검사다

렌더러는 우리 `style.css`만 그리지 않는다. 실제 `<head>`와 **같은 순서로** 티스토리 시트를 끼운다.

```
static/style/content.css      ← 우리보다 앞
../../dist/style.css          ← 우리
atom-one-light.min.css        ← 우리보다 뒤
```

**이것이 없으면 프리뷰는 거짓말을 한다.** 다크에서 인용문이 사라지는 종류의 결함은 원인이
우리 CSS가 아니라 티스토리 CSS와의 특이도 싸움이라, 상대를 안 부르면 멀쩡해 보인다.
이 저장소는 프리뷰가 통과 신호를 위조한 사고를 **이미 두 번** 겪었다(CLAUDE.md 2026-08-25).

순서도 검사의 일부다. `atom-one-light`이 우리 뒤에 와야 `.hljs ` 접두가 정말 필요한지 눈으로 확인된다.
**여기 순서를 바꾸지 말 것.**

네트워크가 없으면 두 시트가 조용히 빠진다. 그때는 화면 하단에 **주황색 경고 띠**가 뜬다 —
띠가 보이면 지금 보고 있는 것은 반쪽이고, 특이도 관련 판단을 내리면 안 된다.

## 렌더러가 재현하지 못하는 것

로컬 프리뷰는 근사값이다. 아래는 **실제 티스토리에서만 확인 가능**하며, QA 리포트에 "미검증"으로 남겨야 한다.

| 항목 | 이유 |
|---|---|
| 댓글·방명록 UI | 티스토리 React가 클라이언트에서 렌더링한다. 프리뷰는 빈 자리만 표시 |
| 카테고리 트리의 실제 마크업 | 재현하지만 티스토리가 클래스를 바꾸면 어긋난다 |
| 광고 삽입 위치 | 티스토리 수익 설정이 런타임에 주입한다 |
| `<s_t3>`가 넣는 공통 JS | 자리만 표시 |
| 페이징 실제 동작 | 링크는 있으나 이동하지 않는다 |
| 스킨 옵션 UI | `index.xml`의 `<default>` 값만 읽는다 |
| 이미지 CDN 리사이징 | placehold.co 더미로 대체 |

## 렌더러를 고쳐야 할 때

새 치환자를 쓰기 시작했는데 렌더러가 모르면 `scripts/render.py`를 고친다.

- **값 치환자** → `globals_for()`(페이지 전역) 또는 `item_scope()`(반복 항목)에 키 추가. 키는 `[##_` 와 `_##]`를 뗀 이름이다
- **그룹 치환자** → `handle_group()`에 분기 추가. 반복이면 `repeat(inner, 항목들, "접두사", ctx, page, posts)`

렌더러를 고친 뒤에는 **11개 페이지를 모두 다시 생성**해 경고가 늘지 않았는지 확인한다.

## 주의

- `_preview/`는 산출물이므로 커밋하지 않는다 (`.gitignore`)
- `data-cat` 값에는 **공백이 들어간다**(`코드 품질/Clean Code`, `개발 도구/Git`). 선택자는 반드시 따옴표로 감싼다 — `[data-cat^="코드 품질/"]`. 2026-08-25 개편으로 `&`는 사라졌지만, 이스케이프되는 문자가 다시 생기면 **CSS 속성 선택자는 파싱된 값과 매칭**한다는 점을 기억한다 (HTML에 `&amp;`로 나와도 선택자에는 `&`를 쓴다)
- 프리뷰가 깨졌을 때 **스킨이 아니라 렌더러가 문제**일 수 있다. 경고를 먼저 읽는다
