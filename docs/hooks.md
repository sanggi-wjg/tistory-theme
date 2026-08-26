# hooks.md — 훅 계약 (skin-markup → skin-style · skin-behavior)

`src/skin.html`이 내보내는 클래스·id·data 속성의 **단일 출처**다.
여기 없는 이름은 CSS·JS에게 존재하지 않는다. 반대로 여기 있는 이름은 마크업이 보장한다.

**변경 규칙** — 이름을 바꾸려면 이 문서를 먼저 고치고 skin-style·skin-behavior에게 알린다.
말없이 바꾸면 CSS 선택자와 JS 쿼리가 동시에, 그리고 조용히 죽는다.

버전: 2026-08-25 초판 (skin.html v1)

---

## 0. 한눈에 보기

```
html[data-theme]                       ← JS가 찍는다 (없으면 시스템 따름)
└ body#tt-body-*                       ← [##_body_id_##]
  ├ a.skip-link
  ├ header.site-header
  │  └ .header-inner
  │     ├ .site-brand > a.brand-title · p.brand-desc
  │     ├ nav.site-nav          ← [##_blog_menu_##] (티스토리 고정 마크업)
  │     └ .header-util
  │        ├ .search > label.a11y-hidden · input#search-input.search-input · button.search-btn
  │        └ button#theme-toggle.theme-toggle > svg.icon-sun · svg.icon-moon
  ├ .ad.ad-upper                       ← [##_revenue_list_upper_##]
  ├ main#main.layout
  │  ├ .content
  │  │  ├ article.notice           (공지)
  │  │  ├ section.list             (홈·카테고리·검색·태그·보관함)
  │  │  │   └ .post-list > article.post
  │  │  ├ section.tagcloud         (/tag 클라우드)
  │  │  ├ article.entry            (글)
  │  │  ├ section.protected        (보호글)
  │  │  ├ section.guestbook        (방명록)
  │  │  └ nav.paging
  │  └ aside.sidebar > .side-mod × 7
  ├ .ad.ad-lower                       ← [##_revenue_list_lower_##]
  ├ footer.site-footer
  └ button#to-top.to-top
```

---

## 1. 페이지별 최상위 컨테이너

`skin.html`은 **한 장**이다. 페이지별 영역은 치환자가 지우고 남긴다.
아래 표의 "존재"는 그 body_id에서 **DOM에 실제로 남는가**를 뜻한다.

| 영역 | 클래스 | 감싸는 치환자 | 존재하는 body_id |
|---|---|---|---|
| 공지 | `article.notice` | `s_notice_rep` | 공지 글 (그리고 홈에 노출될 수 있음 — §9 미확인) |
| 목록 | `section.list` | `s_list` | **`tt-body-index`** `tt-body-category` `tt-body-search` `tt-body-tag` `tt-body-archive` |
| 태그 클라우드 | `section.tagcloud` | `s_tag` | `tt-body-tag` (`/tag`) |
| 글 | `article.entry` | `s_article_rep` > `s_permalink_article_rep` ⚠️ | `tt-body-page` |
| 보호글 | `section.protected` | `s_article_protected` | 보호글 |
| 방명록 | `section.guestbook` | `s_guest` | `tt-body-guestbook` |
| 페이징 | `nav.paging` | `s_paging` | 홈·목록 |
| 사이드바 | `aside.sidebar` | `s_sidebar` | **모든 페이지** ⚠️ |

### ⚠️ `<s_permalink_article_rep>`는 `<s_article_rep>` 안에 있어야 한다

`s_permalink_article_rep`와 `s_index_article_rep`는 **독립 영역이 아니라 `s_article_rep`의
하위 영역**이다. 바깥에 두면 티스토리가 통째로 버린다 — 에러도, 빈 껍데기도 없이 사라진다.
2026-08-25 배포에서 실제로 겪었다: 글 페이지에 본문·제목·목차·관련글이 전부 없었고,
홈은 `s_list`가 대신 그려 준 덕에 멀쩡해 보였다. 린트 `SUB008`이 지킨다.

```html
<s_article_rep>            <!-- 글 하나당 한 번. 자기 마크업은 없다 -->
  <s_permalink_article_rep>
    <article class="entry">…</article>
  </s_permalink_article_rep>
</s_article_rep>
```

### ⚠️ CSS 게이트 두 개

**① `.sidebar`** — `s_sidebar`가 페이지를 가리지 않아 **모든 페이지 DOM에 남는다.**
빈 채로 여백만 차지하지 않도록 body_id로 잠근다. 켜는 곳은 홈·글·목록 4종이고,
자리는 **왼쪽**이다(결정 30). 방명록·보호글은 1단이라 끈다.

**② `.post-list`** — `s_list`는 홈에서도 렌더된다(2026-08-25 실측). 지우는 게이트가
아니라 **모양을 가르는 게이트**가 필요하다. 홈은 카드 그리드, 목록 4종은 세로 행이다.
범위를 안 걸면 홈 카드에 밑줄이 깔리고 썸네일이 180px로 눌린다.

```css
/* ① 사이드바 — 좌측 레일. 홈·글·목록 4종 */
.sidebar { display: none; }
#tt-body-index .sidebar, #tt-body-page .sidebar,
#tt-body-category .sidebar, … { display: block; }

/* 1025px~ : DOM은 .content → .sidebar 순서다. 왼쪽에 세우려면 명시 배치가 필요하다 */
#tt-body-index .layout, … { grid-template-columns: var(--sidebar-w) minmax(0, 1fr); }
#tt-body-index .sidebar, … { grid-column: 1; grid-row: 1; }
#tt-body-index .content, … { grid-column: 2; grid-row: 1; }

/* ② 목록의 모양 — 홈은 그리드 */
#tt-body-index .post-list { display: grid; }
#tt-body-category .post-list, … { display: flex; flex-direction: column; }
```

`:empty`로는 잡히지 않는다. 치환자가 사라져도 줄바꿈 공백이 남아 `:empty`가 거짓이 된다.

### 레이아웃 (DESIGN.md §4)

`main#main.layout`이 `.sidebar` + `.content` 2칸 그리드다. **사이드바가 1칸이다.**
마크업에서는 `.content`가 먼저 오므로(스크린리더·JS 없는 경로에서 본문이 먼저 읽혀야
한다) 좌측 배치는 `grid-column`으로 명시한다. auto placement에 맡기면 오른쪽에 남는다.

⚠️ **1단 페이지에는 이 규칙을 걸지 않는다.** `.content`에 `grid-column: 2`를 주면
1칸짜리 그리드에 **암묵 열이 생겨** 본문이 오른쪽으로 밀린다.

| body_id | 구성 (1025px~) |
|---|---|
| `tt-body-index` | 레일 + `.post-list` (1240px~ 3열, **`.post:first-child`가 주목 글**) |
| `tt-body-category` `tt-body-search` `tt-body-tag` `tt-body-archive` | 레일 + 목록 |
| `tt-body-page` | 레일 + 본문 + 목차 (`.entry-aside`는 1400px~ 우측) |
| `tt-body-guestbook` 외 | 1단, 레일 없음 |

**`--page-w`는 레일 페이지에서 전부 `--wrap`(1400px)이다.** 페이지마다 폭이 다르면
컨테이너가 다른 폭으로 가운데 정렬되어 레일 x좌표가 달라진다 — 홈에서 글로 넘어갈 때
카테고리가 옆으로 뛴다. 본문은 `--content-w`(800px)로 잠그고 남는 자리는 비워 둔다.
실측 1440px: 레일 x=44 폭 240 (홈·글·목록 동일), 글 본문 x=316 폭 800 (**목차 유무 무관**).

**주목 글에 별도 클래스가 없는 이유**: 반복 치환자는 첫 항목을 구분해 주지 않는다.
`#tt-body-index .post-list > .post:first-child`로 잡고 `grid-column: 1 / -1`을 준다.
그래서 **`.post-list`의 자식은 `.post`뿐이어야 한다** — 광고·공지를 안에 넣으면 `:first-child`가 깨진다.

---

## 2. 카드 — `.post` (홈·목록 공용)

**홈과 목록이 같은 구조·같은 클래스를 쓴다. 다른 것은 치환자 접두사뿐이다.**

```html
<article class="post" data-cat="IT/Clean Code">
  <a class="post-link" href="…">
    <span class="thumb">
      <!-- 대표이미지가 없으면 이 img가 통째로 사라진다 -->
      <img class="thumb-img" src="…" alt="" loading="lazy" decoding="async">
    </span>
    <span class="post-text">
      <span class="post-cat">IT/Clean Code</span>
      <strong class="post-title">글 제목</strong>
      <span class="post-excerpt">요약…</span>
      <span class="post-meta">
        <time class="post-date">2026.08.12</time>
        <span class="post-rp">3</span>
      </span>
    </span>
  </a>
</article>
```

| 훅 | 뜻 |
|---|---|
| `.post` | 카드 루트. **`data-cat`이 여기 붙는다** |
| `.post[data-cat]` | 상위/하위 전체 경로 (`"IT"` 또는 `"IT/Clean Code"`). DESIGN §6.2의 기본이미지 선택자가 이 값에 붙는다 |
| `.post-link` | 카드 전체를 덮는 단일 `<a>`. **안에 다른 `<a>`가 없다** (중첩 앵커 금지) |
| `.thumb` | 16:10 비율 상자. **기본이미지 배경은 여기에** |
| `.thumb-img` | 대표이미지. **있을 때만 존재한다** — `.thumb:has(.thumb-img)` / `:not(:has())`로 분기 |
| `.post-text` | 텍스트 묶음 |
| `.post-cat` `.post-title` `.post-excerpt` `.post-meta` `.post-date` `.post-rp` | caption / display-sm 2줄 클램프 / body-sm / caption |

**전부 인라인 요소다** (`span` `strong` `time`). `<a>` 안이라 블록을 쓸 수 없다.
CSS에서 `display: block` / `flex` / `grid`를 직접 지정해서 쓴다.

**카테고리가 링크가 아닌 이유**: 카드 전체를 하나의 `<a>`로 만들었다. 중첩 앵커는 무효 HTML이고
`:has()` 없이는 클릭 영역이 갈라진다. 카테고리로 가는 링크는 사이드바 트리와 글 페이지에 있다.

### 카드는 `s_list_rep` 한 벌뿐이다

홈도 목록도 같은 `s_list_rep` 마크업을 쓴다. 예전에는 홈을 `s_index_article_rep`로
따로 그렸는데, 그 영역이 `s_article_rep` 밖에 있어 통째로 죽어 있었다(§1 경고).
`s_list`가 홈에서도 정상 동작하는 것을 확인하고 한 벌로 합쳤다.

| 자리 | 치환자 |
|---|---|
| `data-cat` | `[##_list_rep_category_##]` |
| 링크 | `[##_list_rep_link_##]` |
| 썸네일 조건 | `s_list_rep_thumbnail` |
| 썸네일 src | `[##_list_rep_thumbnail_##]` |
| 제목 | **`[##_list_rep_title_text_##]`** (`_title_`엔 New 아이콘 img가 섞인다) |
| 요약 | `[##_list_rep_summary_##]` |
| 날짜 | `[##_list_rep_regdate_##]` |
| 댓글 수 | `[##_list_rep_rp_cnt_##]` |

⚠️ 글 페이지 안에서는 `[##_article_rep_*_##]`를 쓴다. 목록 치환자와 섞으면 빈 화면이 된다.

---

## 3. 목록 페이지 — `section.list`

```html
<section class="list">
  <div class="list-banner" style="background-image:url('…')"></div>  <!-- 대표이미지 있을 때만 -->
  <header class="list-head">
    <h1 class="list-title">'Kotlin &amp; Java/Spring'</h1>
    <span class="list-count">24</span>
    <p class="list-desc">…</p>
  </header>
  <div class="post-list list">        <!-- 두 번째 클래스는 [##_list_style_##] -->
    <article class="post" …>…</article>
  </div>
  <div class="list-empty">…</div>     <!-- 결과 0건일 때만 -->
</section>
```

| 훅 | 메모 |
|---|---|
| `.list-banner` | `<s_list_image>` 안. **`#tt-body-category`에서만 보이게 CSS가 감춘다** (결정 7 — 검색·태그에선 블로그 대표이미지가 나와 무의미) |
| `.list-head` `.list-title` `.list-count` `.list-desc` | `[##_list_conform_##]` · `[##_list_count_##]` · `[##_list_description_##]` |
| `.post-list` | 카드 목록 컨테이너. 두 번째 클래스는 `[##_list_style_##]` — 지금은 빈 문자열 (index.xml에 `<liststyle>` 없음) |
| `.list-empty` | `<s_list_empty>` 안. `#tt-body-search`의 0건 화면. 안쪽에 `.list-empty-title`(안내 문구) · `.list-empty-desc`(홈 링크를 품은 보조 문구) |

**카테고리 목록에서 기본이미지 반복 억제** (DESIGN §6.2):
```css
#tt-body-category .post:not(:has(.thumb-img)) .thumb { display: none; }
```
(DESIGN 원문의 `.thumb img`는 `.thumb-img`로 이름이 생겼다. 둘 다 매칭되지만 클래스를 쓴다.)

---

## 4. 글 페이지 — `article.entry`

```html
<article class="entry">
  <div class="reading-progress" id="reading-progress"><span class="reading-progress-bar"></span></div>
  <header class="entry-head">
    <a class="entry-cat" href="…">Infrastructure/MSA</a>
    <h1 class="entry-title">…</h1>
    <div class="entry-meta"><time class="entry-date">…</time><span class="entry-rp">3</span></div>
  </header>
  <div class="entry-layout">
    <div class="entry-main">
      <div class="entry-body">
        <!-- 여기부터 티스토리 고정 마크업 -->
        <div class="tt_article_useless_p_margin contents_style">…</div>
      </div>
      <div class="entry-tags">…</div>       <!-- s_tag_label -->
      <div class="entry-admin">…</div>      <!-- s_ad_div, 관리자에게만 -->
      <section class="related">…</section>
      <nav class="postnav">…</nav>
      <div class="comments" id="comments">…</div>
    </div>
    <aside class="entry-aside">
      <nav class="toc" id="toc" aria-label="목차">…</nav>
    </aside>
  </div>
</article>
```

| 훅 | 메모 |
|---|---|
| `.entry-head` `.entry-cat` `.entry-title` `.entry-meta` `.entry-date` `.entry-rp` | display-lg 제목 |
| `.entry-layout` | 본문 + 목차 2칸. 1024px 미만에서 1칸으로 |
| `.entry-main` | 본문 칸. **`min-width: 0`을 반드시 준다** — 안 주면 1,777자짜리 코드 줄이 그리드를 밀어 페이지가 가로 스크롤한다 |
| `.entry-body` | 본문 래퍼. **`.contents_style`은 이 안에 티스토리가 넣는다.** 실제 클래스는 `tt_article_useless_p_margin contents_style`이므로 **부분일치**로 잡을 것 (`.contents_style`, 절대 `[class="contents_style"]` 금지) |
| `.entry-aside` | 목차 칸. `position: sticky`는 여기 또는 `.toc`에 |
| `.entry-tags` | 안의 `<a>`는 티스토리가 만든다 (`[##_tag_label_rep_##]`). `.entry-tags a`로 스타일 |
| `.entry-admin` | 관리자 전용 링크 줄. 조용히 작게 |
| `.related` `.related-title` `.related-list` `.related-item` `.related-link` `.related-thumb` `.related-thumb-img` `.related-text` `.related-date` `.related-more` | 같은 카테고리 다른 글. `.related-item`에 티스토리가 주는 `text_type` / `thumb_type` 클래스가 **함께** 붙는다 |
| `.postnav` `.postnav-item` `.postnav-prev` `.postnav-next` `.postnav-label` `.postnav-title` `.postnav-thumb` `.postnav-thumb-img` | 이전/다음 글. `.postnav-item`에도 `text_type`/`thumb_type`이 붙는다 |
| `.comments` `#comments` | `[##_comment_group_##]` 한 줄. 안은 전부 `tt-*` (DESIGN §5.4) |

**본문 폭 계약** — `index.xml`의 `<contentWidth>800</contentWidth>`은
`.entry-body`의 실제 콘텐츠 폭이 **800px**라는 선언이다. 에디터 위지윅이 이 값에 맞춰진다.
CSS에서 이 폭을 바꾸면 index.xml도 같이 바꿔야 하고, **index.xml을 바꾸면 스킨 설정이 초기화된다.**
그러니 800px을 먼저 지키고, 바꿔야 한다면 리더에게 알린다.

---

## 5. JS가 채우는 자리 — skin-behavior 계약

마크업이 **빈 그릇을 미리 놓아둔다.** JS는 만들지 말고 채운다 (CSS가 붙잡을 대상이 먼저 있어야 한다).

### 5.1 목차 — `#toc`

```html
<nav class="toc" id="toc" aria-label="목차">
  <button type="button" class="toc-toggle" aria-expanded="false" aria-controls="toc-list">
    <span class="toc-title">목차</span>
  </button>
  <ol class="toc-list" id="toc-list"></ol>   <!-- ← JS가 채운다 -->
</nav>
```

| 계약 | 내용 |
|---|---|
| JS가 만드는 것 | `.toc-list` 안에 `<li class="toc-item toc-h2">` 또는 `toc-h3` → `<a class="toc-link" href="#…">` |
| 렌더 조건 | 본문 `h2`/`h3`가 **3개 이상**일 때만. 조건 충족 시 `#toc`에 **`.is-ready`**를 붙인다 |
| CSS 기본값 | **`.toc { display: none }` · `.toc.is-ready { display: block }`** — 조건 미달·JS 실패 시 빈 상자가 남지 않는다 |
| **레이아웃 신호** | 목차를 **못 만들었을 때만** `<body>`에 **`.no-toc`**를 붙인다. `.is-ready`의 반대이며 붙는 곳도 다르다(`body`) |
| 스크롤스파이 | 현재 위치 링크에 **`.is-current`** (`--link` + 좌측 2px 바) |
| 모바일 접이식 | 1024px 미만에서 `.toc-toggle`이 보이고, JS가 `aria-expanded`를 토글하며 `#toc`에 **`.is-open`**을 붙인다. CSS는 `.toc:not(.is-open) .toc-list { display: none }` (1024px 미만에서만) |
| id 앵커 | 본문 소제목에 id가 없으면 JS가 만든다. 형식 `toc-h-1`, `toc-h-2`… (한글 슬러그를 피한다 — URL 인코딩 문제) |

**왜 `.is-ready`가 아니라 `body.no-toc`가 레이아웃을 정하는가**

목차 유무는 글 폭을 바꾼다(1128px ↔ 848px). 그걸 `.is-ready`로 판단하면 **첫 페인트에서는
모든 글이 목차 없는 폭**이었다가 스크립트가 도는 순간 목차가 있는 글이 넓어진다.
`script.js`는 `</body>` 직전에 `defer` 없이 걸려 있어 네트워크가 느리면 페인트가 먼저다 —
1400px에서 본문이 **144px 밀리는 것을 실측했다.** 소제목 3개 이상인 글이 68%이므로
그 방식은 다수를 민다.

`.no-toc`는 신호를 뒤집는다. 레이아웃 기본값이 2단이라 **68%는 한 픽셀도 움직이지 않고**,
밀리는 것은 목차가 없는 32%뿐이다. JS가 아예 꺼진 경로는 `layout.css`의
`@media (scripting: none)`이 받는다.

⚠ **두 클래스는 반대말이고 붙는 곳도 다르다.** `.is-ready`는 `#toc`에, `.no-toc`는 `<body>`에
붙는다. 한쪽만 고치면 목차는 나오는데 폭이 안 맞거나 그 반대가 된다.

### 5.2 읽기 진행바 — `#reading-progress`

```html
<div class="reading-progress" id="reading-progress"><span class="reading-progress-bar"></span></div>
```

- 글 페이지에만 존재한다 (`s_permalink_article_rep` 안).
- **JS는 `.reading-progress-bar`의 `style.transform = 'scaleX(p)'`만 건드린다** (p = 0…1).
- CSS는 `.reading-progress-bar { transform-origin: left center; transform: scaleX(0); }`,
  `.reading-progress { position: fixed; top: 0; left: 0; right: 0; }`.
- `width`가 아니라 `transform`인 이유: 레이아웃 재계산 없이 스크롤마다 갱신하기 위해.

### 5.3 맨 위로 — `#to-top`

```html
<button type="button" class="to-top" id="to-top" aria-label="맨 위로">…svg…</button>
```

- **모든 페이지**에 존재한다 (긴 목록에서도 필요).
- JS는 스크롤 임계치에서 **`.is-visible`만** 토글한다.
- CSS 기본값은 **보이지 않게**: `opacity:0; visibility:hidden; pointer-events:none` →
  `.to-top.is-visible`에서 되돌린다. **`display`로 감추지 않는다** (전환이 죽는다).
  JS가 안 돌아도 버튼이 튀어나오지 않는다.

### 5.4 다크모드 초기화 — `<head>` 인라인 스니펫

`skin.html`의 `<head>`에 자리와 마커가 이미 있다:

```html
<!-- head-inline:start -->
<script>/* head-inline */</script>
<!-- head-inline:end -->
```

- skin-behavior가 `_workspace/head-inline.js`에 코드를 쓰고, **그 내용을 위 `<script>` 안에 붙여넣는다.**
  (빌드는 skin.html을 그대로 복사할 뿐 주입하지 않는다 — `scripts/build.mjs` 확인함.)
- **동기 스크립트여야 하고, `./style.css` 링크보다 먼저 있어야 한다.** 지금 자리가 그렇다.
- 해야 할 일 두 가지:
  1. `try { localStorage.getItem('theme') } catch {}` → `'dark'`/`'light'`면
     `document.documentElement.setAttribute('data-theme', v)`. 값이 없으면 **아무것도 찍지 않는다**
     (= 시스템 따름. 세 번째 상태다).
  2. `document.documentElement.classList.add('js')` — JS 없는 환경과 구분할 훅.
- 되도록 3줄을 넘기지 않는다. 여기서 실패하면 페이지 전체가 흰 화면에서 시작한다.
- `localStorage` 키 이름은 **`theme`**, 값은 **`dark` | `light`** 로 고정한다. (`images/script.js`의 토글도 같은 키를 쓴다.)

### 5.5 다크모드 토글 버튼 — `#theme-toggle`

```html
<button type="button" class="theme-toggle" id="theme-toggle" aria-label="다크 모드 전환" aria-pressed="false">
  <svg class="icon icon-sun" …/><svg class="icon icon-moon" …/>
</button>
```

- 아이콘 두 개가 **둘 다 마크업에 있다.** CSS가 현재 테마에 따라 하나만 보인다
  (라이트일 때 달, 다크일 때 해 — 누르면 갈 곳을 보여준다).
- JS는 `<html>`의 `data-theme`를 세 상태로 돌리지 않는다 — **`dark` ↔ `light` 2상태 토글**이고,
  최초 클릭 시의 기준은 `matchMedia('(prefers-color-scheme: dark)')`다.
- `aria-pressed`를 함께 갱신한다.

### 5.6 JS가 새로 만드는 DOM (마크업에 자리 없음)

이름만 여기서 못 박는다. skin-style이 미리 스타일을 써둘 수 있게.

| 클래스 | 무엇 | 어디에 |
|---|---|---|
| `.code-wrap` | 코드블록 감싸는 상대위치 컨테이너 | `.contents_style pre`를 감싼다 |
| `.code-lang` | 자동 감지된 언어 라벨 (우상단). **신뢰도 미달이면 만들지 않는다** | `.code-wrap` 안 |
| `.code-copy` | 복사 버튼 (우상단, 호버 노출). 성공 시 `.is-copied` | `.code-wrap` 안 |
| `.code-wrap.has-lines` | 줄번호를 켠 상태 | 일정 줄 수 이상 |
| `.code-lines` | 줄번호 거터. **JS는 줄 수만큼 빈 `<span>`만 놓는다 — 숫자는 CSS가 `counter`로 그린다.** `aria-hidden="true"` | `.code-wrap` 안, `pre` 앞 |
| `.hljs` · `.hljs-*` | highlight.js 출력. `<code>`에 `.hljs` + `.language-<감지결과>`가 붙고, 안쪽 토큰이 `.hljs-keyword` 류를 받는다. **팔레트는 `tokens.css` 기존 변수만 쓴다.** 신뢰도 미달이면 아무것도 붙지 않는다. ⚠ **CSS 쪽 규칙은 반드시 `.hljs ` 접두를 단다** — 티스토리가 `atom-one-light`을 우리 `style.css` 뒤에 실어서, 접두가 없으면 특이도가 같아(0,1,0) 순서로 밀린다. `code.js`가 `.hljs`를 직접 붙이므로 항상 참인 구조다. 린트 `HLJS001` | `.contents_style pre > code` |
| `.table-scroll` | `overflow-x:auto` 래퍼 | `.contents_style table`을 감싼다 |
| `.lightbox` `.lightbox-img` `.lightbox-close` `.lightbox-backdrop` | 이미지 확대 | `<body>` 끝에 1개 |
| `body.is-lightbox-open` | 배경 스크롤 잠금 | |
| `.external-link` | 외부링크임을 표시하는 **상태 클래스**. JS가 `<a>`에 붙이고 `target="_blank" rel="noopener noreferrer"`를 함께 건다. **표시는 `.external-icon`이 담당하므로 이 클래스에 CSS 규칙이 없는 것이 정상이다** (중복 처리를 막는 표식 겸용) | `.contents_style a` |
| `.external-icon` | 외부링크 아이콘 SVG. 실제 스타일은 여기에 | `.external-link` 끝 |
| `.cat-toggle` | 카테고리 하위목록 접기/펼치기 **버튼**. `<button type="button">`, `aria-expanded` + `aria-controls`, 안에 `.a11y-hidden` 이름("Python 하위 카테고리") + `.cat-toggle-icon` | 하위목록을 가진 `li` 안, 링크 뒤·하위 `ul` 앞 |
| `.cat-toggle-icon` | 셰브런 SVG (`.icon`도 함께 붙는다). 펼침 상태에서 90° 회전 | `.cat-toggle` 안 |
| `li.has-toggle` | 토글이 실제로 붙은 `li`. 링크·버튼·하위목록을 한 줄에 세우는 flex 훅 | 사이드바 카테고리 `li` |
| `li.is-collapsed` / `li.is-expanded` | 접힘/펼침. **둘은 항상 배타적이고, `aria-expanded`와 같은 함수에서 함께 갱신된다** | `li.has-toggle`과 같은 `li` |
| `.cat-tree` | 토글이 하나라도 생긴 목록(`ul`). 토글 없는 형제 항목의 글 수 정렬용 | 상위 카테고리들이 늘어선 `ul` |

**카테고리 접기 — CSS가 지켜야 할 세 가지** (`src/styles/tistory.css`, `src/js/category.js`)

1. **기능 규칙은 `.side-category`로 스코프한다. `.tt_category`가 아니다.**
   `[##_category_list_##]`의 안쪽 클래스 이름(`.tt_category` · `.category_list` ·
   `.sub_category_list` · `.link_item`)은 **공식 레퍼런스에 없다.** 2026-08-25 실측으로
   확정했지만(DESIGN.md §5.3), 확정했다고 기능을 이름에 걸지는 않는다.
   이름이 다르면 치장 규칙은 밋밋해지고 끝이지만, 접기 규칙이 안 먹으면 **버튼을 눌러도
   아무 일도 일어나지 않는다.** 그래서 접기만은 우리가 보장하는 훅에 건다:
   `.side-category li.is-collapsed > ul { display: none }`

   이 선택은 값을 이미 한 번 했다. 스킨이 폴더형을 내보내던 동안 JS는 `ul`을 못 찾아
   조용히 물러났고, **잘못된 DOM에 토글을 억지로 심지 않았다** (DECISIONS.md 결정 31).
2. **대상도 이름이 아니라 자식 `ul` 전체다.** `> .sub_category_list`가 아니라 `> ul`.
3. **기본값을 "접힘"으로 두지 않는다.** JS가 없거나 실패하면 아무 클래스도 붙지 않아
   트리는 전부 펼쳐진 채로 남는다 — 읽을 수는 있다. CSS로 미리 접어 두면
   JS 실패 시 하위 카테고리로 갈 길이 영영 사라진다.

**JS가 지키는 것** — 클래스 이름에 의존하지 않고 "중첩 `ul`을 가진 `li`"라는 구조로 고른다.
구조가 예상과 다르면 아무것도 하지 않고 조용히 물러난다. 상위 카테고리 링크는 가로채지 않는다
(접기는 별도 버튼). 현재 보고 있는 가지는 펼친 채로 시작한다 — **`li.selected`를 먼저 보고**,
없으면 `location.pathname`과 링크 `href`를 대조한다. 둘 다 두는 이유는 `selected`가
카테고리 페이지에만 붙기 때문이다. 글 페이지 URL(`/entry/…`)은 카테고리 경로와 겹치지 않아
둘 다 안 걸리고, 그때는 트리가 접힌 채로 시작한다 — 의도한 동작이다.

---

### 5.7 공지 본문 정규화 — `.notice-body`

| 계약 | 내용 |
|---|---|
| 하는 일 | `.notice-body`에 `.contents_style`이 **없으면** 붙인다. 이미 있거나 안쪽에 있으면 아무것도 하지 않는다 |
| 순서 | **다른 본문 모듈보다 먼저 돈다.** code·tables·lightbox·inline-fix가 `contentRoots()`(= `.contents_style`)로 대상을 찾기 때문이다 |
| 왜 필요한가 | `[##_notice_rep_desc_##]`가 `.contents_style` 래퍼를 달고 오는지 **확인할 방법이 없다.** 안 달고 오면 `content.css`(전부 그 스코프)와 빌드가 만든 인라인색 보정이 통째로 비껴간다 — 에러 없이 무스타일 본문 + 다크에서 묻힌 옛 글 색 |
| 확인 방법 | 프리뷰 `index.html` · `page.html` · `page_toc.html`에 공지 2건이 렌더된다. 렌더러는 일부러 **래퍼 없이** 낸다(최악의 경우) |

## 6. 사이드바 — `aside.sidebar`

모듈 7개. 전부 같은 뼈대다.

```html
<div class="side-mod side-category">
  <h2 class="side-title">카테고리</h2>
  <div class="side-body">…</div>
</div>
```

| 모듈 클래스 | 내용 | 안쪽 훅 |
|---|---|---|
| `.side-category` | `[##_category_list_##]` 한 줄 — **폴더형 `[##_category_##]`이 아니다**(결정 31, 린트 `CAT001`) | **티스토리 고정 마크업.** `.tt_category` `.link_tit` `.category_list` `.link_item` `.sub_category_list` `.link_sub_item` `.c_cnt`, 현재 가지에 `li.selected` (DESIGN §5.3) |
| `.side-notice` | 최근 공지 | `.side-list` `.side-item` `.side-link` |
| `.side-recent` | 최근 글 | `.side-list` `.side-item` `.side-link` `.side-thumb` `.side-thumb-img` `.side-text` `.side-meta` `time.side-date` `.side-rp` |
| `.side-popular` | 인기글 | 위와 동일 |
| `.side-comments` | 최근 댓글 | `.sidecmt-list` `.sidecmt-item` `.sidecmt-link` `.sidecmt-name` `.sidecmt-date` |
| `.side-tags` | 태그 클라우드 | `.tagcloud-list` `.tagcloud-item` `.tagcloud-link` + 티스토리가 주는 `cloud1`~`cloud5` |
| `.side-count` | 방문자 수 | `.count-list` `.count-item` `.count-label` `.count-num` (`tabular-nums`) |

`.tagcloud-link`은 `/tag` 페이지(`section.tagcloud`)와 **같은 클래스를 공유한다.** 한 번만 쓰면 된다.

---

## 7. 나머지 영역

| 영역 | 훅 |
|---|---|
| 태그 클라우드 페이지 | `section.tagcloud` `.tagcloud-title` `.tagcloud-list` `.tagcloud-item` `.tagcloud-link` |
| 페이징 | `nav.paging` `.paging-prev` `.paging-next` `.paging-nums` `.paging-num` — **티스토리가 `no_more_prev` / `no_more_next` 클래스를 함께 붙인다** (더 갈 곳이 없을 때). 그 상태를 흐리게 |
| 공지 | `article.notice` `.notice-head` `.notice-badge` `.notice-title` `.notice-date` `.notice-body`(안이 `.contents_style`) |
| 보호글 | `section.protected` `.protected-title` `.protected-desc` `.protected-form` `.protected-label` `.protected-input` `.protected-submit` |
| 방명록 | `section.guestbook` `.guestbook-title` — 본체는 `[##_guestbook_group_##]`, 안은 `tt-*` |
| 광고 | `.ad` `.ad-upper` `.ad-lower` — 비어 있을 때 여백이 생기지 않게 (자식이 없으면 높이 0) |
| 푸터 | `footer.site-footer` `.footer-inner` `.footer-brand`(안이 `a.footer-title` · `p.footer-desc`) `.footer-links` `.footer-copy` |
| 헤더 | `header.site-header` `.header-inner` `.site-brand` `.brand-title` `.brand-desc` `.site-nav` `.header-util` |
| 유틸 | `.a11y-hidden` (스크린리더 전용 텍스트) · `.skip-link` · `.icon` (모든 인라인 SVG) |

`nav.site-nav` 안은 `[##_blog_menu_##]`가 만든 **티스토리 고정 마크업**이다.
클래스를 기대하지 말고 `.site-nav ul` `.site-nav li` `.site-nav a`로 잡는다.
현재 메뉴에 붙은 항목 클래스는 티스토리 설정에 따라 달라진다.

---

## 8. 상태 클래스 한눈에

| 클래스 | 붙는 곳 | 붙이는 주체 |
|---|---|---|
| `html[data-theme="dark"|"light"]` | `<html>` | head 인라인 + `#theme-toggle` |
| `html.js` | `<html>` | head 인라인 |
| `.toc.is-ready` | `#toc` | toc.js |
| `body.no-toc` | `<body>` | toc.js (**목차를 못 만들 때만**. 글 페이지가 아니면 붙이지 않는다) |
| `.toc.is-open` | `#toc` | toc.js (**1024px 미만에서만**. 데스크톱으로 넘어가면 지운다) |
| `.toc-link.is-current` | 목차 링크 | toc.js 스크롤스파이 |
| `.to-top.is-visible` | `#to-top` | progress.js |
| `.code-copy.is-copied` | 복사 버튼 | code.js |
| `.code-wrap.has-lines` | 코드 래퍼 | code.js |
| `body.is-lightbox-open` | `<body>` | lightbox.js |
| `.external-link` | 본문 외부링크 `<a>` | links.js |
| `li.has-toggle` · `li.is-collapsed` / `li.is-expanded` | 사이드바 카테고리 `li` | category.js |
| `.cat-tree` | 상위 카테고리가 늘어선 `ul` | category.js |

### `.toc-toggle`의 `aria-expanded` — 뷰포트에 따라 존재 자체가 달라진다

`skin.html:283`은 `aria-expanded="false"`를 하드코딩하지만 **그 값이 사용자에게 도달하는 경로는 없다**
(`.toc`는 `.is-ready` 없이는 `display:none`이고 `.is-ready`는 toc.js만 붙인다). 실제 값은 toc.js가 정한다.

| 뷰포트 | `aria-expanded` | `tabindex` | 이유 |
|---|---|---|---|
| ~1024px (접이식 활성) | `"false"` / `"true"` — `.is-open`과 동기 | 없음(=0) | 눌리고, 눌리면 목록 높이가 바뀐다 |
| 1025px~ | **속성 없음** | `"-1"` | CSS가 `pointer-events:none`으로 라벨화한다. 목록은 항상 펼쳐져 있으므로 "축소됨"은 거짓말이고, 아무 일도 못 하는 탭 정거장도 만들지 않는다 |

`matchMedia('(max-width: 1024px)')`를 구독하므로 창 크기를 바꾸면 따라온다.
**CSS의 `1024px` 경계를 옮기면 `toc.js`의 `COLLAPSIBLE_MQ`도 같이 옮겨야 한다.**

---

## 9. 확정하지 못한 것 (QA가 실블로그에서 확인해야 함)

1. **`s_notice_rep`의 정체.** 공식 문서가 두 가지로 읽힌다 — (a) 공지 글 퍼머링크 영역, (b) 홈 상단 공지 반복.
   빈 화면을 피하려고 **본문(`[##_notice_rep_desc_##]`)까지 넣었다.** (b)라면 홈 맨 위에 공지 전문이 깔린다.
   테스트 블로그에 공지를 하나 만들어 확인하고, (b)면 `#tt-body-index .notice-body`를 접거나
   마크업에서 desc를 빼야 한다.
2. **홈에서 `s_list`가 함께 렌더되는지.** `showListOnCategory`의 문서 설명이 "커버 미사용 홈"을 언급한다.
   함께 렌더되면 홈에 카드 그리드와 목록이 둘 다 나온다. 확인 필요.
3. ~~**`index.xml`의 `<tree>` 색이 다크모드에서 어떻게 나오는지.**~~ **해결 (2026-08-25)** —
   `[##_category_list_##]`(리스트형)로 바꾸면서 `<tree>` 설정이 닿지 않는 형식이 되어 인라인 `style`이
   0개가 됐다. `!important`도 `index.xml` 수정도 필요 없다 (DECISIONS.md 결정 31, 미결 14).

   **대신 다른 경로로 같은 종류의 문제가 있었다** — 본문 에디터 컴포넌트다. 티스토리가 인라인이 아니라
   **자기 스타일시트**에서 라이트 전용 색을 칠하고, 상당수가 `#tt-body-page` ID 스코프라 클래스로는
   못 이긴다. `tistory.css`에서 덮는다 (DESIGN.md §5.2b, 결정 32).
4. **헤더의 `s_search`.** 공식 문서 예시는 사이드바 안이다. 헤더에서도 동작하는지 실블로그 확인.
