---
name: skin-preview
description: "티스토리 스킨을 로컬 브라우저에서 확인하는 mock 렌더러. src/skin.html의 치환자를 data/posts.json의 실제 275편 데이터로 치환해 홈·글(목차 유/무 2종)·카테고리·검색·태그(목록/클라우드 2종)·보관함·방명록·검색결과0건 10개 페이지를 생성한다. 스킨을 수정한 뒤 '어떻게 보이는지 보자', '프리뷰', '미리보기', '렌더링해봐', '화면 확인', '브라우저로 열어봐' 요청 시 반드시 이 스킬을 사용할 것. 티스토리 API를 쓰지 않으므로 이것이 유일한 확인 수단이다."
---

# 로컬 프리뷰 — 치환자 mock 렌더러

브라우저는 `<s_list_rep>`를 모른다. `skin.html`을 그냥 열면 깨진 화면이 나온다. 이 스킬은 티스토리 서버가 하는 치환을 로컬에서 흉내내, **실제 글 275편 데이터**로 렌더링한다.

## 실행

```bash
# 빌드 먼저 (style.css, images/script.js가 있어야 제대로 보인다)
npm run build

# 10개 페이지 전부
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

## 본문 픽스처가 재현하는 것

`page` 페이지의 본문(`ARTICLE_BODY`)은 실제 글에서 관찰된 패턴을 그대로 담고 있다. 여기서 안 깨지면 실물에서도 대체로 안 깨진다.

- 래퍼 `<div class="tt_article_useless_p_margin contents_style">`
- 인라인 `color: #000000` `#333333` `#252525` — 다크에서 죽는 색
- 인라인 `color: #eeffff` — **라이트에서 죽는 색**
- 인라인 `background-color: #f8f8f8` — 다크에서 흰 상자
- 인라인 `font-family: AppleSDGothicNeo`
- `data-ke-language="javascript"`인데 내용은 셸 — **라벨을 믿으면 안 되는 사례**
- 언어 미지정 코드블록
- `<figure class="imageblock">` · 4열 `<table>` · `<blockquote data-ke-style>` · 인라인 `<code>` · 외부링크

## 경고를 읽어라

렌더러는 stderr로 두 종류의 경고를 낸다. **둘 다 실제 버그의 신호다.**

| 경고 | 의미 | 조치 |
|---|---|---|
| `값이 없는 치환자: [##_xxx_##]` | 치환자 이름 오타이거나 렌더러 미지원 | 화이트리스트 확인. 실재하는 치환자면 `globals_for()`에 추가 |
| `처리 규칙이 없는 그룹 치환자: <s_xxx>` | `handle_group()`에 규칙 없음 | 규칙 추가 |

값이 없는 치환자는 출력에 **빨간 점선 테두리**로 표시되므로 브라우저에서도 눈에 띈다.

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

렌더러를 고친 뒤에는 **10개 페이지를 모두 다시 생성**해 경고가 늘지 않았는지 확인한다.

## 주의

- `_preview/`는 산출물이므로 커밋하지 않는다 (`.gitignore`)
- `data-cat` 값에는 **공백이 들어간다**(`코드 품질/Clean Code`, `개발 도구/Git`). 선택자는 반드시 따옴표로 감싼다 — `[data-cat^="코드 품질/"]`. 2026-08-25 개편으로 `&`는 사라졌지만, 이스케이프되는 문자가 다시 생기면 **CSS 속성 선택자는 파싱된 값과 매칭**한다는 점을 기억한다 (HTML에 `&amp;`로 나와도 선택자에는 `&`를 쓴다)
- 프리뷰가 깨졌을 때 **스킨이 아니라 렌더러가 문제**일 수 있다. 경고를 먼저 읽는다
