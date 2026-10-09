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
| 보호글 | `section.protected` | `s_article_protected` | `tt-body-page` — **전용 body_id가 없다.** 일반 글과 CSS로 구분되지 않는다 |
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
자리는 **왼쪽**이다(결정 30). 방명록은 1단이라 끈다.

⚠ **보호글은 끄지 못한다.** 공식 body_id는 6종뿐이고 보호글도 글 URL이라
`tt-body-page`로 나온다 — 일반 글과 CSS로 구분할 수단이 없다. 레일이 서는 것이
정상이며, `.protected`는 `margin: 0`으로 본문과 같은 x에 세운다. `margin: 0 auto`면
보호글만 144px 오른쪽으로 뛴다(2026-08-27 실측).

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

**1024px 이하에서는 레일이 본문 아래로 내려가고, 헤더 안 `nav.cat-chips`가 상위 카테고리 14종을
한 줄로 낸다**(§5.9, 결정 50). 레일 자체는 그대로 아래에 남는다 — 하위 21종과 최근 글은 거기에 있다.

**`--page-w`는 레일 페이지에서 전부 `--wrap`(1520px)이다.** 페이지마다 폭이 다르면
컨테이너가 다른 폭으로 가운데 정렬되어 레일 x좌표가 달라진다 — 홈에서 글로 넘어갈 때
카테고리가 옆으로 뛴다. 본문은 `--content-w`(800px)로 잠그고 남는 자리는 비워 둔다.

실측 1440px (2026-08-27): 레일 **x=24** 폭 240, 본문 **x=312.5** — 홈·글(목차 유/무)·
카테고리·보관함 **다섯 페이지 전부 같다.** 글 본문은 목차 유무와 무관하게 정확히 **800.0px**.

⚠ **레일 x는 폭에 따라 움직인다.** 1600px부터 래퍼(1520)가 뷰포트보다 좁아져
가운데 정렬이 살아나기 때문이다(1600 → 56.5, 1920 → 216.5). 계약은 「x가 고정」이
아니라 **「같은 폭에서 페이지끼리 같다」**이다 — 그것이 결정 30이 요구한 것이다.

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
| `.post-link[aria-labelledby]` | **JS가 붙인다**(`cards.js`). 링크 이름을 안쪽 `.post-title`로 좁힌다 — 카드 전체가 링크라 이름이 카테고리·제목·발췌·날짜 약 500자였다. `.post-title`에 id가 없으면 `post-title-N`을 만든다(`util.uniqueId`로 문서 안에서 겹치지 않게). `.post-title`이 없거나 비면 건드리지 않는다 |
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
    <div class="entry-meta"><time class="entry-date">…</time>
      <!-- .entry-rp는 <s_rp_count> 안이고 라벨이 마크업에 있다 -->
      <a class="entry-rp" href="#comments">댓글 3</a></div>
  </header>
  <div class="entry-layout">
    <aside class="entry-aside">              <!-- DOM은 목차가 먼저 — 1400px~ CSS order로 오른쪽 열 -->
      <nav class="toc" id="toc" aria-label="목차">…</nav>
    </aside>
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
  </div>
</article>
```

| 훅 | 메모 |
|---|---|
| `.entry-head` `.entry-cat` `.entry-title` `.entry-meta` `.entry-date` `.entry-rp` | display-lg 제목 |
| `.entry-layout` | 본문 + 목차 2칸. 1399px 이하에서 1칸으로(목차는 본문 위 접이식). **DOM은 목차(`.entry-aside`)가 먼저다** — 1399px 이하에서는 화면 순서와 같고, 1400px 이상에서는 CSS `order`로 목차가 오른쪽 열에 서지만 Tab·낭독은 목차를 먼저 지난다(결정 64). DOM 순서를 다시 뒤집지 않는다 |
| `.entry-main` | 본문 칸. **`min-width: 0`을 반드시 준다** — 안 주면 1,777자짜리 코드 줄이 그리드를 밀어 페이지가 가로 스크롤한다 |
| `.entry-body` | 본문 래퍼. **`.contents_style`은 이 안에 티스토리가 넣는다.** 실제 클래스는 `tt_article_useless_p_margin contents_style`이므로 **부분일치**로 잡을 것 (`.contents_style`, 절대 `[class="contents_style"]` 금지) |
| `.entry-aside` | 목차 칸. **DOM에서 `.entry-main` 앞** — 1400px 이상에서 CSS `order`로 오른쪽 열(결정 64). `position: sticky`는 여기 또는 `.toc`에 |
| `.entry-tags` | 안의 `<a>`는 티스토리가 만든다 (`[##_tag_label_rep_##]`). `.entry-tags a`로 스타일 |
| `.entry-admin` | 관리자 전용 링크 줄. 조용히 작게 |
| `.related` `.related-title` `.related-list` `.related-item` `.related-link` `.related-thumb` `.related-thumb-img` `.related-text` `.related-date` `.related-more` | 같은 카테고리 다른 글. `.related-item`에 티스토리가 주는 `text_type` / `thumb_type` 클래스가 **함께** 붙는다. `.related-thumb` 상자는 **항상 있고** `.related-thumb-img`만 대표이미지가 있을 때 존재한다 — 홈 카드 `.thumb`/`.thumb-img`와 같은 구조(결정 57) |
| `.postnav` `.postnav-item` `.postnav-prev` `.postnav-next` `.postnav-label` `.postnav-title` `.postnav-thumb` `.postnav-thumb-img` | 이전/다음 글. `.postnav-item`에도 `text_type`/`thumb_type`이 붙지만 칸을 그걸로 켜고 끄지 않는다 — `.postnav-thumb` 상자는 **항상 있고** `.postnav-thumb-img`만 대표이미지가 있을 때 존재한다(결정 57, 린트 `BND011`) |
| `.comments` `#comments` | `[##_comment_group_##]` 한 줄. 안은 전부 `tt-*` (DESIGN §5.4) |
| *(없음)* `.menu_toolbar` | **스킨 마크업이 아니다.** 티스토리가 **모든 페이지**에서 우리 `script.js` 태그 뒤에 서버 HTML로 넣는 툴바(「구독하기」 알약 `.btn_subscription` + ⋮ `#menubar_wrapper[data-tistory-react-app="Menubar"]`, ⋮만 React가 채운다). 규칙은 티스토리 `static/style/tistory.css` — `position: fixed; top: 20px; right: 20px; z-index: 9999`, `max-width: 1260px`에서 숨김. 우리는 툴바를 꾸미지 않고 **헤더가 자리를 비운다**(`.header-inner`의 1261px~ `padding-right`, 토큰 `--tt-toolbar-reserve`, 결정 59). 인쇄에서는 `components.css` 인쇄 블록이 지운다. 클래스 이름 `#menubar`는 리터럴 `#`이 붙은 class 값이다(id 아님) |
| *(없음)* `[data-tistory-react-app="Namecard"]` | **스킨 마크업이 아니다.** 티스토리가 글 페이지의 `<s_rp>` 출력 **앞**에 클래스 없는 빈 div를 주입하고 React가 채운다 — `.tt_box_namecard > .tt_cont(.tt_tit_cont .tt_desc .tt_btn_subscribe > .tt_txt_g) + .tt_wrap_thumb > .tt_thumb_g`. 방명록·홈에는 없다(2026-09-10 라이브 실측). `tistory.css`가 `.entry-main [data-tistory-react-app="Namecard"] .tt_box_namecard` 접두로 덮는다(결정 53, 린트 `TIS005`). `<s_rp>` 안쪽은 티스토리가 `#entryNComment`로 한 번 더 감싼다 |

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
| CSS 기본값 | **`.toc { display: none }` · `.toc.is-ready { display: block }`** — 조건 미달·JS 실패 시 빈 상자가 남지 않는다 (자리 예약은 바로 아래 행) |
| **레이아웃 신호** | 목차를 **못 만들었을 때만** `<body>`에 **`.no-toc`**를 붙인다. `.is-ready`의 반대이며 붙는 곳도 다르다(`body`). **붙이는 곳은 둘이고 조건은 같아야 한다** — `skin.html`의 `.entry-body` 직후 인라인 스크립트가 첫 페인트 전에 판정하고(결정 48), `toc.js`의 `markNoToc()`가 폴백이다. 임계·선택자가 같은지는 린트 `BND010`이 대조한다 |
| **첫 페인트 자리** | **`html.js`이고 `body:not(.no-toc)`이면 1399px 이하에서 CSS가 `.entry-aside`에 목차 바 높이를 미리 잡는다** — `.toc`가 `.is-ready` 전까지 `display:none`이라 바가 페인트 뒤에 끼어들며 본문을 밀던 것을 막는다(결정 62). `.no-toc`는 인라인이 첫 페인트 전에 판정하므로 목차 없는 글은 예약하지 않는다 — HTML을 다 받은 뒤 처음 그릴 때의 이야기다. `.entry-aside`가 인라인보다 먼저 파싱되므로(결정 64), 느린 망에서 본문 중간에 페인트가 나면 목차 없는 글은 예약이 먼저 그려졌다가 50.5px 접힌다. `script.js` 로드가 실패하면 `js`가 지워져 예약도 풀린다(§5.4). **toc.js가 `.is-ready`를 못 붙이고 끝나면 — 조기 반환이든 실행 중 예외든 — `markNoToc()`로 `no-toc`를 붙여 예약을 푼다**(`try…finally`로 한 곳에서). 실행 중 예외는 `html.js`가 못 보는 경로라 toc.js가 스스로 풀어야 빈 띠가 안 남는다 |
| 스크롤스파이 | 현재 위치 링크에 **`.is-current`** (`--link` + 좌측 2px 바) + **`aria-current="location"`**. 둘은 같은 자리에서 함께 옮긴다 — 이전 항목에서는 둘 다 지운다. 떠 있는 목차 시트(§5.1b)가 있으면 **그 목록의 같은 번호 링크에도 같은 자리에서** 옮긴다 |
| 상자 따라가기 | 1400px~에서 `.toc.is-ready`는 `max-height` + `overflow-y: auto` 상자다. 현재 항목이 **바뀔 때만**, 상자가 실제로 스크롤될 때(`scrollHeight > clientHeight`)만 **`#toc`의 `scrollTop`만** 옮겨 현재 항목을 위아래 여유(최대 48px)를 두고 보이게 한다. `scrollIntoView`는 쓰지 않는다 — 페이지까지 움직인다. 사용자가 상자를 직접 굴리는 동안에는 항목이 안 바뀌므로 싸우지 않는다 |
| 모바일 접이식 | 1399px 이하에서 `.toc-toggle`이 보이고, JS가 `aria-expanded`를 토글하며 `#toc`에 **`.is-open`**을 붙인다. CSS는 `.toc:not(.is-open) .toc-list { display: none }` (1399px 이하에서만 — 3단 경계 1400과 같다, 결정 48) |
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

### 5.1b 떠 있는 목차 — `.toc-fab` · `#toc-sheet`

1399px 이하에서 목차는 글 머리 접이식뿐이라, 긴 글을 읽는 도중에는 목차로 돌아갈 길이 없었다(결정 65 —
390px 「타이밍 어택」 문서 16,412px, 1,500px만 내려가도 목차가 화면 밖). 마크업에 자리가 없다 — JS가 만든다(`src/js/toc-sheet.js`, toc.js가 부른다).

```html
<!-- <body> 끝. 버튼 다음에 시트 -->
<button type="button" class="toc-fab" aria-haspopup="dialog" aria-controls="toc-sheet" aria-expanded="false">
  <svg class="icon" …></svg><span class="toc-fab-label">목차</span>
</button>
<dialog id="toc-sheet" class="toc-sheet" aria-labelledby="toc-sheet-title">
  <div class="toc-sheet-head">
    <h2 class="toc-sheet-title" id="toc-sheet-title">목차</h2>
    <button type="button" class="toc-sheet-close" aria-label="목차 닫기"><svg class="icon" …></svg></button>
  </div>
  <ol class="toc-sheet-list"><li class="toc-item toc-h2"><a class="toc-link" href="#toc-h-1">…</a></li>…</ol>
</dialog>
```

| 계약 | 내용 |
|---|---|
| 만드는 조건 | toc.js가 목차를 **실제로 만들었을 때만**(`#toc.is-ready` — 소제목 3개 이상). `body.no-toc`인 글, 글 페이지가 아닌 곳에는 버튼도 시트도 없다. `HTMLDialogElement.showModal`이 없는 브라우저에서도 만들지 않는다 — 글 머리 목차는 그대로다 |
| 항목 | 글 머리 `#toc-list`의 `li`를 **복제**한다 — 같은 목록·같은 순서·같은 클래스(`.toc-item` · `.toc-h2`/`.toc-h3` · `.toc-link`). 소제목을 따로 세지 않는다(결정 38의 「같은 목록」). CSS는 `.toc-sheet .toc-link`로 따로 칠한다 |
| 보이는 조건 | **`.toc-fab.is-visible`만 토글한다**(§5.3 맨 위로와 같은 방식 — CSS 기본값은 보이지 않게, `display`로 감추지 않는다). 붙는 때: 접이식 구간(toc.js `COLLAPSIBLE_MQ`, ≤1399px)이고 글 머리 `#toc`가 화면 **위로** 완전히 지나갔을 때 — **`#toc.getBoundingClientRect().bottom <= 0`**. 아직 아래에 있어 안 보이는 것과 가른다. **재는 때**: 스크롤(rAF로 프레임당 한 번, toc.js 스크롤스파이와 같은 `rafThrottle`) · `resize` · `load` · `COLLAPSIBLE_MQ` 변화 · 만든 직후 한 번(해시 착지·새로고침 복원). **교차 변화(`IntersectionObserver`)에 기대지 않는다** — 목차가 첫 화면 아래인 글(폰은 거의 늘)에서 아래 → 위로 한 번에 넘어가는 스크롤(「댓글」 링크·페이지 안 찾기·모션 축소의 「맨 위로」)은 「교차 안 함 → 교차 안 함」이라 알림이 없어, 버튼이 안 뜨거나 맨 위에 남았다(1차 체크포인트). 1400px 이상으로 넘어가면 지운다. **폭 경계를 새로 적지 않는다** — 판정은 JS 몫이고 린트 `BND010`은 toc.js의 그 상수와 CSS 블록 셋(components 둘·layout 하나)만 대조한다. CSS가 그 폭에서 따로 감추려면 새 숫자를 쓰지 말고 기존 3단 블록(`.toc.is-ready`의 min-width 블록) 안에 둔다 |
| 열기 | 버튼 click → 버튼에 포커스(닫을 때 브라우저가 돌려줄 곳을 고정한다 — Safari·iOS는 눌러도 버튼에 포커스를 안 준다) → **`showModal()`**. 포커스 가두기·Esc·뒤 페이지 inert는 브라우저가 한다. `aria-expanded="true"`. **열림 상태 클래스는 없다** — CSS는 `[open]`·`::backdrop`을 본다. 포커스는 **현재 항목 링크**(없으면 첫 링크)로, 그 항목이 보이게 **`.toc-sheet-list`의 `scrollTop`만** 즉시 옮긴다(`util.revealInBox`). 굴러가는 상자는 목록이고 머리는 서 있다 — CSS가 목록에 `overflow-y: auto`를 건다. 시트 자신을 굴리게 바꾸면 이 줄도 같이 바꾼다 |
| 닫기 | 닫기 버튼 · Esc · 배경 클릭 · 시트 링크 · 1400px 이상으로 넘어감. 배경 클릭은 **dialog 사각형 밖 좌표**일 때만이다 — `::backdrop` 클릭과 dialog 안쪽 여백 클릭은 둘 다 target이 dialog라 좌표로 가른다. `close` 이벤트에서 `aria-expanded="false"`, 포커스는 **버튼으로** 돌아온다. 버튼이 안 보이면(visibility hidden은 포커스를 못 받는다) 그 자리에 보이는 목차로 — 3단이면 옆 칸 목차의 현재 항목, 접이식이면 `.toc-toggle` |
| 착지 | 시트 링크를 누르면 시트를 닫고 **같은 번호의 글 머리 링크를 `click()`**한다 — toc.js 목록 핸들러 하나가 착지를 정한다(접기 → 스크롤 → 소제목 포커스, 모션 축소면 즉시 — 결정 59). 두 벌로 만들지 않는다. 먼저 닫는 이유는 열린 동안 뒤 페이지가 inert라 소제목이 포커스를 못 받아서다. `close` 이벤트는 그 뒤 태스크에 오므로 거기서 포커스를 버튼으로 도로 뺏지 않는다 |
| 현재 위치 | toc.js 스크롤스파이가 글 머리 목록과 시트 목록의 **같은 번호 링크**에 `.is-current` + `aria-current="location"`을 함께 옮긴다(결정 63) |
| 배경 스크롤 | 잠그지 않는다. 시트 안 스크롤이 배경으로 새는 것은 CSS가 굴러가는 상자(`.toc-sheet-list`)에 `overscroll-behavior: contain`으로 막는다 |
| 탭 순서 | 버튼은 `<body>` 끝이라 Tab으로는 페이지 끝(맨 위로 다음)에서 닿는다. 키보드 사용자의 목차 길은 본문 앞의 글 머리 목차다(결정 64). 이 버튼은 그 목차가 화면 밖일 때 손가락·마우스로 돌아오는 길이다 |

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

- 이 `<script>`가 스니펫의 **정본**이다. 바꿔야 하면 skin-behavior가 새 코드를 skin-markup에게 넘기고, skin-markup이 **이 블록만 교체**한다. 별도 파일에 두지 않는다.
  (빌드는 skin.html을 그대로 복사할 뿐 주입하지 않는다 — `scripts/build.mjs` 확인함.)
- **동기 스크립트여야 하고, `./style.css` 링크보다 먼저 있어야 한다.** 지금 자리가 그렇다.
- 해야 할 일 세 가지:
  1. `try { localStorage.getItem('theme') } catch {}` → `'dark'`/`'light'`면
     `document.documentElement.setAttribute('data-theme', v)`. 값이 없으면 **아무것도 찍지 않는다**
     (= 시스템 따름. 세 번째 상태다).
  2. `document.documentElement.classList.add('js')` — 아래 「`html.js`의 뜻」.
  3. **`script.js` 로드 실패 감지** — `window`에 **capture 단계** `error` 리스너를 걸고, 대상이
     `<script>`이고 `src`에 **`/images/script.js`**가 들어 있으면 `classList.remove('js')`.
     ```js
     window.addEventListener('error',function(e){var s=e.target;if(s&&s.tagName==='SCRIPT'&&s.src.indexOf('/images/script.js')!==-1)document.documentElement.classList.remove('js')},true);
     ```
     - **capture인 이유**: 리소스 로드 오류는 버블되지 않는다. 요소에서 난 `error`는 `window`의
       capture 단계에서만 잡힌다. 런타임 예외의 `error`는 대상이 `window`라 `tagName`이 없어 걸러진다.
     - **`/images/script.js`인 이유**: 라이브 `src`는
       `https://tistory1.daumcdn.net/tistory/3356137/skin/images/script.js?_version_=…`, 프리뷰는
       `../../dist/images/script.js`다. `s.src`는 해석된 절대 URL이라 둘 다 이 조각을 품는다.
       GA(`gtag/js`) 같은 다른 스크립트의 실패는 건드리지 않는다.
     - **head-inline에 두는 이유**: `<body>` 끝 `<script src="./images/script.js">`보다 먼저 걸려야 하고,
       `js`를 붙이는 쪽과 한자리에 있어야 그 뜻이 한 곳에서 정해진다.
- 되도록 3줄을 넘기지 않는다(지금 정확히 3줄). 여기서 실패하면 페이지 전체가 흰 화면에서 시작한다.
- `localStorage` 키 이름은 **`theme`**, 값은 **`dark` | `light`** 로 고정한다. (`images/script.js`의 토글도 같은 키를 쓴다.)

**`html.js`의 뜻 — 「스크립트가 실제로 도는 중」** (결정 62)

「브라우저가 JS를 켰다」가 아니다. CSS가 **JS가 만들 결과의 자리를 미리 잡는** 규칙 —
카테고리 미리 접기(§5.6 「카테고리 접기」), 목차 바(§5.1 「첫 페인트 자리」), 칩 줄(§5.9) — 은
전부 `.js` 아래에만 쓴다. 그 자리를 채울 스크립트가 안 오면 예약이 거짓말이 되기 때문이다.

| 경로 | `html.js` | 화면 |
|---|---|---|
| 정상 | 있다 | 예약된 자리에 JS가 결과를 채운다. 페인트 뒤 밀림 없음 |
| `script.js` 로드 실패(404·네트워크·차단) | **head-inline이 지운다** | 예약이 풀려 펼친 트리·칩 없음·목차 자리 없음으로 물러난다. 실패가 늦게 오면 그때 한 번 밀린다 — 실패 경로뿐이다 |
| JS 꺼짐 | 처음부터 없다 | 위와 같다. 레이아웃은 `@media (scripting: none)`이 받는다(§5.1) |
| 받았는데 **실행 중 예외** | **남는다 — 못 잡는다** | 모듈마다 `safe()`가 감싸 다른 모듈은 돈다. 목차는 `markNoToc()`(§5.1), 칩은 `.is-off`(§5.9)로 모듈이 스스로 예약을 푼다. **카테고리 트리만 접힌 채 토글 없이 남는다** — 하위 카테고리는 상위 카테고리 페이지에서 선택된 가지로 펼쳐져(§5.6 「카테고리 접기」 3번) 한 번 더 누르면 닿는다 |

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
| `.toc-item` · `.toc-h2` · `.toc-h3` · `.toc-link` | 목차 항목. `<li class="toc-item toc-h2">` 안에 `<a class="toc-link">`. 계약 본문은 §5.1 | `#toc-list` 안. 떠 있는 목차 시트의 `.toc-sheet-list` 안에도 같은 이름으로(복제, §5.1b) |
| `.toc-fab` · `.toc-fab-label` · `.toc-sheet` · `.toc-sheet-head` · `.toc-sheet-title` · `.toc-sheet-close` · `.toc-sheet-list` | 떠 있는 목차 — 버튼(`button.toc-fab` > `svg.icon` + `span.toc-fab-label`)과 시트(`dialog#toc-sheet.toc-sheet` > `.toc-sheet-head`(`h2#toc-sheet-title.toc-sheet-title` + `button.toc-sheet-close` > `svg.icon`) + `ol.toc-sheet-list`). 계약 본문은 §5.1b(결정 65) | `<body>` 끝에 버튼, 그 뒤 시트. 목차가 생긴 글(`#toc.is-ready`)에만 |
| `.code-wrap` | 코드블록 감싸는 상대위치 컨테이너. **첫 페인트 뒤 유휴 시간에** 블록 단위로 붙는다(결정 51) — 동기가 아니다. 20,000자 넘는 블록은 **자동 감지가 꺼져** 래퍼·복사 버튼만 받는다(글쓴이 `language-*`가 있으면 그대로 칠한다) | `.contents_style pre`를 감싼다 |
| `.code-lang` | 언어 라벨 (우상단). 값의 출처는 **글쓴이가 쓴 `<code class="language-X">` 우선, 없으면 자동 감지**다 (결정 43). **자동 감지가 신뢰도 미달이거나, 글쓴이가 쓴 이름이 언어인지 모를 때는 만들지 않는다** | `.code-wrap` 안 |
| `.code-copy` | 복사 버튼 (우상단, 호버 노출). **성공**: 1.5초 동안 `.is-copied` + 아이콘이 체크로 바뀌고(같은 15px·viewBox 20·stroke 1.6 — 버튼 크기 불변) `aria-label`이 「복사됨」, 지나면 셋 다 되돌린다 — 색만으로 알리지 않는다. **실패**: 조용히 넘어가지 않는다 — 그 블록의 코드를 `Range`로 선택해 두고 알린다. **알림 영역**: 문서에 하나뿐인 `<div class="a11y-hidden" role="status">`를 처음 알릴 때 만들어 `<body>` 끝에 붙인다(새 클래스 없음 — §7 유틸). 같은 문구도 다시 읽히게 비웠다가 100ms 뒤 채운다. 문구는 「코드를 복사했습니다」 / 「복사하지 못했습니다. 코드를 선택해 두었으니 직접 복사하세요」 | `.code-wrap` 안 |
| `.code-wrap.has-lines` | 줄번호를 켠 상태 | 일정 줄 수 이상 |
| `.code-lines` | 줄번호 거터. **JS는 줄 수만큼 빈 `<span>`만 놓는다 — 숫자는 CSS가 `counter`로 그린다.** `aria-hidden="true"` | `.code-wrap` 안. **DOM 순서는 `pre` 뒤**이지만 `position: absolute`라 화면에서는 왼쪽 거터다 |
| `.hljs` · `.hljs-*` | highlight.js 출력. `<code>`에 `.hljs`가 붙고(자동 감지일 때는 `.language-<감지결과>`도 함께 — **글쓴이가 쓴 경우엔 그 클래스가 이미 있으므로 더하지 않는다**), 안쪽 토큰이 `.hljs-keyword` 류를 받는다. **팔레트는 `tokens.css` 기존 변수만 쓴다.** 신뢰도 미달이면 아무것도 붙지 않는다. ⚠ **CSS 쪽 규칙은 반드시 `.hljs ` 접두를 단다** — 티스토리가 `atom-one-light`을 우리 `style.css` 뒤에 실어서, 접두가 없으면 특이도가 같아(0,1,0) 순서로 밀린다. `code.js`가 `.hljs`를 직접 붙이므로 항상 참인 구조다. 린트 `HLJS001` | `.contents_style pre > code` |
| `.table-scroll` | `overflow-x:auto` 래퍼 | `.contents_style table`을 감싼다 |
| `.lightbox` `.lightbox-img` `.lightbox-close` `.lightbox-backdrop` | 이미지 확대 **폴백**. 티스토리 phocus 뷰어가 그 클릭을 받았으면(`body.with-phocus`) 만들지 않는다 — 아래 「라이트박스 — phocus가 먼저」(결정 60). `.lightbox-img`의 `src`는 **본문 `<img>`의 `src` 속성**이다 — 티스토리가 `srcset`에 1280px 축소본을 싣어 `currentSrc`는 축소본이 된다(결정 56) | `<body>` 끝에 1개. phocus가 받지 않은 클릭에서만 |
| `.cat-chip` · `.cat-chip-count` · `.cat-chip.is-all` | 모바일 카테고리 칩. `<a class="cat-chip">인프라<span class="cat-chip-count">42</span></a>`. 「전체」는 `.is-all`. 계약 본문은 §5.9 | `#cat-chips` 안 |
| `body.is-lightbox-open` | 배경 스크롤 잠금 | |
| `.external-link` | 외부링크임을 표시하는 **상태 클래스**. JS가 `<a>`에 붙이고 `target="_blank" rel="noopener noreferrer"`를 함께 건다. **표시는 `.external-icon`이 담당하므로 이 클래스에 CSS 규칙이 없는 것이 정상이다** (중복 처리를 막는 표식 겸용) | `.contents_style a` |
| `.external-icon` | 외부링크 아이콘 SVG. 실제 스타일은 여기에 | `.external-link` 끝 |
| `.heading-anchor` | 소제목 퍼머링크. **글자 없는 `<a>`** — 보이는 `#`은 CSS `::before`가 그린다(소제목 `textContent`가 목차 라벨이자 색인 제목이라 오염시키면 안 된다). `aria-label`에 소제목 이름 + `" 링크"`. 앵커가 소제목 안에 있어 그 라벨이 소제목 이름에 합쳐지므로 **소제목 자신에도 `aria-label`(소제목 텍스트)**을 준다. 계약은 §5.8 | 본문 `h2`·`h3` 안쪽 끝 |
| `.cat-toggle` | 카테고리 하위목록 접기/펼치기 **버튼**. `<button type="button">`, `aria-expanded` + `aria-controls`, 안에 `.a11y-hidden` 이름("Python 하위 카테고리") + `.cat-toggle-icon` | 하위목록을 가진 `li` 안, 링크 뒤·하위 `ul` 앞 |
| `.cat-toggle-icon` | 셰브런 SVG (`.icon`도 함께 붙는다). 펼침 상태에서 90° 회전 | `.cat-toggle` 안 |
| `li.has-toggle` | 토글이 실제로 붙은 `li`. 링크·버튼·하위목록을 한 줄에 세우는 flex 훅 | 사이드바 카테고리 `li` |
| `li.is-collapsed` / `li.is-expanded` | 접힘/펼침. **둘은 항상 배타적이고, `aria-expanded`와 같은 함수에서 함께 갱신된다** | `li.has-toggle`과 같은 `li` |
| `.cat-tree` | 토글이 하나라도 생긴 목록(`ul`). 토글 없는 형제 항목의 글 수 정렬용 | 상위 카테고리들이 늘어선 `ul` |

**CSS 규칙이 없는 것이 정상인 클래스** — 린트 `BND006`은 이 목록만 건너뛴다.
이름 뒤에 `—`와 이유를 쓴다. **이름만 적은 줄은 예외로 치지 않는다** — 이유가 없으면
"정상"과 "아직 안 한 일"을 구분할 수 없고, 구분 못 하는 예외는 상시 경고와 같다.

- `.external-link` — 표시는 `.external-icon`이 맡는다. 이쪽은 JS가 같은 링크를 두 번
  손대지 않으려고 붙이는 **표식**이라 스타일이 붙을 자리가 없다.
- `.toc-item` — `<li>` 자체에 줄 것이 없다. 여백·목록기호는 `.toc-list`가, 글자·패딩·
  현재 표시는 `.toc-link`가 맡는다. 이 이름은 `.toc-h3 .toc-link` 같은 **층 선택자의
  발판**으로 쓰인다.
- `.toc-h2` — h2가 **기본 층**이라 보정할 것이 없다. 들여쓰기는 `.toc-h3 .toc-link`
  한 곳에서만 준다. 여기에 규칙을 만들면 기본값을 다시 적는 죽은 규칙이 된다.

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
3. **미리 접기는 `html.js` 아래에서만 한다**(결정 62). 펼친 채 그려졌다가 category.js가
   접으면 데스크톱 모든 페이지에서 레일이 페인트 뒤 줄어든다 — 그래서 CSS가 첫 페인트부터
   접어 둔다. 단 `.js` 없이 접으면 JS가 안 도는 독자도 토글 없는 접힌 트리를 받는다.
   `html.js`는 「스크립트가 실제로 도는 중」이고 `script.js` 로드가 실패하면 head-inline이
   지우므로(§5.4), 그때는 **펼친 트리**(category.js가 손대기 전 모양)로 물러난다. 미리 접는 대상은
   **category.js가 토글을 달 `li`와 같은 집합**이어야 한다:
   - **래퍼 `li`(「분류 전체보기」)는 접지 않는다.** `pickList()`가 한 단계 내려가는 바로 그 층이다 —
     여기를 접으면 첫 페인트에 트리 전체가 사라지고, JS는 그 `li`에 토글을 안 다므로 영영 안 펴진다.
   - **현재 가지(`li.selected` 또는 `.selected`를 품은 `li`)는 접지 않는다.** JS가 펼친 채 시작하는
     가지라, 접어 두면 카테고리 페이지에서 반대 방향으로 한 번 밀린다.
   - **`li.is-expanded`가 붙으면 풀린다.** 그 뒤로는 1번의 `li.is-collapsed > ul` 규칙이 맡는다.
   - **어긋나면 펼친 채로 남는 선택자여야 한다** — 1번과 방향이 반대다. 접기 규칙은 안 먹으면 버튼이
     고장 나지만, 미리 접기는 안 먹으면 페인트 뒤 한 번 밀릴 뿐 트리는 읽힌다. 그래서 래퍼를 건너뛴
     층을 좁게 짚고, `.side-category li:not(.is-expanded) > ul`처럼 넓게 잡지 않는다 — 그건 래퍼까지 접는다.

   category.js가 **실행 중 예외**로 죽으면 `html.js`가 남아 트리가 접힌 채 토글 없이 남는다 —
   `html.js`가 못 보는 경로다(§5.4 표). 그래도 길이 끊기지는 않는다: 상위 카테고리 페이지에서는
   그 가지가 `li.selected`라 위 둘째 예외로 펼쳐져 있다.

**JS가 지키는 것** — 클래스 이름에 의존하지 않고 "중첩 `ul`을 가진 `li`"라는 구조로 고른다.
구조가 예상과 다르면 아무것도 하지 않고 조용히 물러난다. 상위 카테고리 링크는 가로채지 않는다
(접기는 별도 버튼). 현재 보고 있는 가지는 펼친 채로 시작한다 — **`li.selected`를 먼저 보고**,
없으면 `location.pathname`과 링크 `href`를 대조한다. 둘 다 두는 이유는 `selected`가
카테고리 페이지에만 붙기 때문이다. 글 페이지 URL(`/entry/…`)은 카테고리 경로와 겹치지 않아
둘 다 안 걸리고, 그때는 트리가 접힌 채로 시작한다 — 의도한 동작이다.

**현재 카테고리의 `aria-current="page"`** — 티스토리가 붙인 `li.selected` 중 **그 `li` 자신의 링크가
지금 경로를 가리킬 때만**(`isHere()` — 끝 `/`를 뗀 디코딩 경로가 같을 때, 칩과 같은 함수) 그 링크에 붙인다. 하위 카테고리 페이지의
상위 링크, URL 대조로 펼친 가지에는 붙이지 않는다 — 「이 가지 아래」이지 「이 페이지」가 아니다.
토글을 다는 일과 무관하게 돈다(하위가 없는 카테고리도 현재일 수 있다).

**라이트박스 — phocus가 먼저, `.lightbox`는 폴백** (결정 60, `src/js/lightbox.js`)

티스토리 `static/pc/dist/index.js`가 DOMContentLoaded에 `span[data-phocus] > img`마다 click을
img에 직접 걸어 자기 뷰어(phocus)를 띄운다. 이미지블록은 2019~2026년 글 전부 `data-phocus`를 단다.
둘 다 뜨면 phocus가 위에 겹치고, phocus를 닫으면 우리 것이 아래에 남아 스크롤이 잠긴 채가 된다.

| 계약 | 내용 |
|---|---|
| phocus 열림 표시 | `body.with-phocus`. **티스토리가 붙이는 상태다. 우리는 읽기만 한다** — 우리 JS가 만드는 이름이 아니라 위 표와 §8 표에 넣지 않는다. `BND006`·`BND007`은 §5.6·§8 표의 **첫 칸**을 우리 JS 생성 이름으로 읽으므로, 이 이름을 어느 표의 첫 칸에도 적지 않는다. phocus는 이 클래스를 자기 click 핸들러 안이 아니라 **그 직후 마이크로태스크**에서 붙인다(2026-10-06 라이브 이벤트 추적) |
| 물러나는 조건 | `lightbox.js`는 `.contents_style` 루트의 click에서 `preventDefault`만 바로 하고, `body.with-phocus` 판정은 **`setTimeout(0)`으로 미룬** 자리에서 본다. 참이면 `.lightbox`를 만들지 않는다. 바로 읽으면 답이 클릭의 출처에 따라 갈린다 — 신뢰된 클릭은 브라우저가 리스너 사이마다 마이크로태스크를 돌려 참이지만, 키보드 경로의 합성 `img.click()`은 우리 keydown이 끝날 때까지 마이크로태스크가 미뤄져 거짓이다(라이브에서 두 겹이 실제로 떴다). 매크로태스크는 phocus의 마이크로태스크가 다 돈 뒤라 둘이 같은 답을 낸다. **판정을 동기로 되돌리면 키보드에서 두 겹이 돌아온다** |
| 폴백이 도는 때 | phocus가 그 클릭을 받지 않았을 때 — `data-phocus` 없는 이미지, phocus가 아직 안 걸린 시점, 티스토리가 phocus를 꺼 둔 환경 |
| 키보드 | Enter(keydown, 반복 무시)·Space(keyup)는 **`img.click()`**을 부른다 — 무엇을 띄울지는 click 경로 하나가 정한다. phocus는 click만 받는다. phocus가 이미 열려 있으면 아무것도 하지 않는다 |
| 포커스 복귀 | phocus는 닫힐 때 포커스를 돌려주지 않는다. phocus로 열렸으면 그 img를 기억하고 `<body>`의 class를 `MutationObserver`로 보다가 `with-phocus`가 빠지면 `img.focus({ preventScroll: true })`. `preventScroll`은 phocus가 막 되돌린 스크롤을 덮지 않으려는 것이다 |
| 못 고치는 것 | phocus 뷰어에 `role="dialog"`·`aria-modal`이 없고, 모바일 레이아웃에서 포커스가 뒤 페이지로 샌다(트랩 없음). 티스토리 소관이다 |

---

### 5.7 공지 본문 정규화 — `.notice-body`

| 계약 | 내용 |
|---|---|
| 마크업 | `skin.html`이 그릇에 **처음부터** 단다 — `<div class="notice-body contents_style">`. 린트 `BND012`가 본다 |
| 하는 일 | 티스토리가 **안쪽에** `.contents_style` 래퍼를 달아 왔으면 그릇의 `contents_style`을 **뗀다.** 안 달아 왔으면 아무것도 하지 않는다 |
| 순서 | **다른 본문 모듈보다 먼저 돈다.** code·tables·lightbox·inline-fix가 `contentRoots()`(= `.contents_style`)로 대상을 찾기 때문이다 |
| 왜 필요한가 | `[##_notice_rep_desc_##]`가 `.contents_style` 래퍼를 달고 오는지 **확인할 방법이 없다**(라이브에 공지가 없다). 안 달고 오면 `content.css`(전부 그 스코프)와 빌드가 만든 인라인색 보정이 통째로 비껴간다 — 에러 없이 무스타일 본문 + 다크에서 묻힌 옛 글 색. 달고 왔는데 그릇에도 있으면 두 겹이라 `contentRoots()`가 같은 본문을 두 번 낸다 — 루트마다 click 리스너를 거는 `lightbox.js`가 라이트박스를 두 번 연다 |
| 왜 마크업인가 | 처음에는 `notice.js`가 **없을 때 붙였다.** 그러면 첫 페인트 뒤에 본문 시트가 걸려 공지마다 문단 여백(24px)만큼 아래가 밀렸다 — 프리뷰 공지 2건에 48px, 3페이지 × 4폭 12경우 전부(이슈 #97, `script.js`를 붙잡고 잰 기하). 지금은 두 경우 모두 0이다 — 안쪽 래퍼가 같은 시트를 받으므로 바깥 것을 떼도 기하가 그대로다. 결정 62의 예약과 달리 `html.js`에 걸지 않는다: JS가 오지 않아도 맞는 모양이라서다 |
| 확인 방법 | 프리뷰 `index.html` · `page.html` · `page_toc.html`에 공지 2건이 렌더된다. **1번은 래퍼 없이, 2번은 티스토리 래퍼를 안쪽에 달아** 낸다 — 두 경로를 한 화면에서 본다. 첫 페인트 밀림은 프리뷰가 재현하지 않는다(로컬 `script.js`가 페인트 전에 끝난다) — 그 축은 `BND012`가 원인 쪽에서 막는다 |

### 5.8 소제목 앵커 — `.heading-anchor`

```html
<h2 id="toc-h-1" aria-label="커넥션 유효성 검사">커넥션 유효성 검사<a class="heading-anchor" href="#toc-h-1" aria-label="커넥션 유효성 검사 링크"></a></h2>
```

| 계약 | 내용 |
|---|---|
| JS가 만드는 것 | 본문 `h2`/`h3` **끝에** 빈 `<a class="heading-anchor">`. `href`는 그 소제목의 `#id` |
| 렌더 조건 | **없다.** 소제목이 하나라도 있으면 붙는다 — 목차의 3개 조건과 무관하다 |
| id | `util.headingsWithIds()`가 만든다. **목차와 같은 함수다** (`toc-h-1`, `toc-h-2`…) |
| `#` 글자 | **CSS `::before`가 그린다.** 텍스트 노드로 넣지 않는다 |
| 이름 | **앵커**: `aria-label`에 소제목 텍스트 + `" 링크"` — 링크 목록으로 훑으면 `#`은 전부 같은 이름이 된다. **소제목**: 앵커를 붙이기 전에 읽은 같은 텍스트를 소제목 자신의 `aria-label`로 준다(글쓴이가 `aria-label`·`aria-labelledby`를 이미 줬으면 그대로 둔다). 앵커가 소제목 **안**에 있어 그 라벨이 소제목 이름에 합쳐져 헤딩이 「개요 개요 링크」로 두 번 읽혔다(라이브 접근성 트리). `aria-label`은 `textContent`에 들지 않으므로 목차 라벨·색인 제목은 그대로다. **택하지 않은 것**: 앵커를 `aria-hidden`·`tabindex="-1"`로 숨기기(키보드 사용자가 소제목 링크를 잃는다), 소제목 밖 형제로 빼기(content.css의 `h2:hover .heading-anchor` 노출 규칙과 본문의 인접 선택자가 깨진다) |
| CSS 기본값 | `opacity: 0` → 소제목 `:hover` · 앵커 `:focus-visible` · `@media (hover: none)`에서 1 |
| 특이도 | `.contents_style .heading-anchor`(0,2,0)가 `.contents_style a`(0,1,1)를 이겨야 밑줄·`--link`가 벗겨진다 |

**왜 `#`을 텍스트 노드로 넣지 않는가.** 소제목의 `textContent`는 두 곳에서 다시 쓰인다 —
목차 링크의 라벨(`toc.js`)과 검색결과에 실리는 제목이다. 텍스트로 넣으면 목차에 `개요#`이
뜨고 색인에도 그대로 들어간다. `::before`로 그리면 복사·선택에도 딸려오지 않는다.

**왜 목차와 id 만드는 자리를 합쳤는가.** 둘이 따로 세면 — 한쪽만 빈 소제목을 거르면 —
그 뒤 번호가 전부 한 칸씩 밀린다. 목차는 그대로 뜨고 앵커도 그대로 보이므로
**눌러 보기 전에는 아무 신호가 없다.** `util.headingsWithIds()` 하나만 부른다.

### 5.9 모바일 카테고리 칩 — `#cat-chips`

```html
<header class="site-header">
  <div class="header-inner">…</div>
  <nav class="cat-chips" id="cat-chips" aria-label="카테고리"></nav>   <!-- ← JS가 채운다. 한 줄에 붙여 둔다 -->
</header>
```

| 계약 | 내용 |
|---|---|
| JS가 만드는 것 | `<a class="cat-chip" href="/category/인프라">인프라<span class="cat-chip-count">42</span></a>` × 상위 카테고리 수. 맨 앞에 「전체」(`.is-all`, `/category`) |
| 출처 | 사이드바 트리(`.side-category .side-body ul`) — **`category.js`와 같은 파서**(`pickList`·`ownAnchor`·`labelOf`). 둘이 각자 세면 레일과 칩이 다른 목록을 낼 수 있고 화면에 신호가 없다 |
| 렌더 조건 | 트리를 못 찾으면(폴더형·구조 다름) **아무것도 넣지 않고 그릇에 `.is-off`를 붙인다**(결정 62). 칩을 하나도 못 넣고 끝나는 경로는 전부 같다 — 조기 반환이든 모듈 안 예외든(`try…finally`로 한 곳에서). 그릇은 비어 있고 CSS가 감춘다 |
| CSS 기본값 | `.cat-chips { display: none }` → `@media (max-width: 1024px)`에서 `.cat-chips:not(:empty)`만 flex. **`html.js`이면 빈 그릇에도 칩 줄 높이를 미리 잡는다 — `.js .cat-chips:empty:not(.is-off)`**(결정 62). 빈 `<nav>`를 페인트 뒤에 채우며 헤더가 55px 늘던 것을 막는다. `.is-off`가 붙으면 예약을 풀어 다시 감춘다 — 그때 한 번 밀리는 것은 실패 경로뿐이다. `script.js` 로드가 실패하면 `js`가 지워져 예약도 풀린다(§5.4). **1025px~에서는 항상 감춤**(레일이 있다). DOM은 폭과 무관하게 항상 만든다 |
| 현재 가지 | 티스토리 `li.selected`(카테고리 페이지) 또는 URL 대조 → `.is-current` + `aria-current`. 하위 카테고리 페이지에서는 **그 상위 칩**이 켜진다. `aria-current`는 칩 링크가 **지금 페이지 자체**면 `"page"`, 하위 카테고리 페이지라서 가지만 현재면 `"true"`다 — 「이 페이지」 판정은 레일과 같은 `category.isHere()`(결정 63). 글 페이지에서는 아무것도 안 켜진다(URL이 `/entry/…`) |
| 스크롤 | 현재 칩이 오른쪽 밖이면 `nav.scrollLeft`만 옮긴다. `scrollIntoView`는 쓰지 않는다 — 페이지를 세로로 움직일 수 있다 |
| 왜 마크업에 그릇을 두나 | §5 원칙. JS가 `<nav>`째 만들면 CSS가 붙잡을 자리를 JS가 정하는 셈이고, 실패 시 흔적 없이 사라져 "원래 없던 것"과 구분이 안 된다 |

⚠ **`:empty` 가드는 여는 태그와 닫는 태그가 붙어 있을 때만 참이다** — 사이에 줄바꿈을 넣는
순간 공백 노드가 생겨 빈 줄(border-top + 패딩)이 모바일 헤더에 영영 남는다. `.ad`와 같은 함정이다.

## 6. 사이드바 — `aside.sidebar`

모듈 7개. 전부 같은 뼈대다.

⚠ **마크업은 7개지만 라이브에 나오는 것은 2개다** — 카테고리와 최근 글.
티스토리는 `<s_sidebar_element>`를 **블로그에 등록된 슬롯 수만큼** 렌더한다.
사용자가 관리 → 꾸미기 → 사이드바에서 그렇게 정했고, **결함이 아니다**
(결정 41). 나머지 5개 마크업은 그대로 둔다 — 슬롯을 늘리면 다시 나온다.

```html
<div class="side-mod side-category">
  <h2 class="side-title">카테고리</h2>
  <div class="side-body">…</div>
</div>
```

| 모듈 클래스 | 내용 | 안쪽 훅 |
|---|---|---|
| `.side-category` | `[##_category_list_##]` 한 줄 — **폴더형 `[##_category_##]`이 아니다**(결정 31, 린트 `CAT001`) | **티스토리 고정 마크업.** `.tt_category` `.link_tit` `.category_list` `.link_item` `.sub_category_list` `.link_sub_item` `.c_cnt`, 현재 가지에 `li.selected`, 새 글이 있는 가지의 앵커 끝에 `img[alt="N"]`(결정 58) (DESIGN §5.3) |
| `.side-notice` | 최근 공지 | `.side-list` `.side-item` `.side-link` |
| `.side-recent` | 최근 글 | `.side-list` `.side-item` `.side-link` `.side-thumb` `.side-thumb-img` `.side-text` `.side-meta` `time.side-date` `.side-rp`. `.side-thumb` 상자는 **항상 있고** `.side-thumb-img`만 대표이미지가 있을 때 존재한다(결정 57) |
| `.side-popular` | 인기글 | 위와 동일 |
| `.side-comments` | 최근 댓글 | `.sidecmt-list` `.sidecmt-item` `.sidecmt-link` `.sidecmt-name` `.sidecmt-date` |
| `.side-tags` | 태그 클라우드 | `.tagcloud-list` `.tagcloud-item` `.tagcloud-link` + 티스토리가 주는 `cloud1`~`cloud5` |
| `.side-count` | 방문자 수 | `.count-list` `.count-item` `.count-label` `.count-num` (`tabular-nums`) |

**`.side-category`의 트리는 `html.js`이면 CSS가 첫 페인트부터 미리 접어 둔다**(결정 62) — 래퍼 `li`와
현재 가지는 빼고, `script.js` 로드가 실패하면 펼친 트리로 물러난다. 대상·예외는 §5.6 「카테고리 접기」 3번.

`.tagcloud-link`은 `/tag` 페이지(`section.tagcloud`)와 **같은 클래스를 공유한다.** 한 번만 쓰면 된다.

---

## 7. 나머지 영역

| 영역 | 훅 |
|---|---|
| 태그 클라우드 페이지 | `section.tagcloud` `.tagcloud-title` `.tagcloud-list` `.tagcloud-item` `.tagcloud-link` |
| 페이징 | `nav.paging` `.paging-prev` `.paging-next` `.paging-nums` `.paging-num` `.paging-icon` `.paging-label` — 이전·다음 앵커 안은 우리 마크업이다: `svg.icon.paging-icon`(꺾쇠, `aria-hidden`)과 `span.paging-label`(「이전」·「다음」), 순서는 이전이 아이콘→글자, 다음이 글자→아이콘. **글자는 767px 이하에서 화면에서만 숨기고 앵커의 이름으로 남긴다 — 아이콘은 그때만 보인다**(결정 66). 그 밖은 티스토리가 내보내는 것 셋(2026-09-10 라이브 실측, 결정 53): ① `[##_paging_rep_link_num_##]`은 숫자가 아니라 **`<span class="selected">N</span>`**(현재 페이지) / `<span class="">N</span>`이다 — 현재 위치 신호는 이 `span.selected`뿐이다 ② 생략 부호 `···`도 `a.paging-num`인데 **href가 없다** ③ 더 갈 곳이 없을 때 붙는 클래스는 **`no-more-prev` / `no-more-next`(하이픈)** 이고 그 앵커에도 href가 없다. 2026-09-10까지 CSS·이 문서가 `no_more_prev`(밑줄)로 적혀 있어 라이브에서 한 번도 매칭된 적이 없었다. href 없는 앵커는 `.paging a:not([href])`가 한 번에 잡는다 |
| 공지 | `article.notice` `.notice-head` `.notice-badge` `.notice-title` `.notice-date` `.notice-body`(그릇 자신이 `.contents_style` — 티스토리가 안쪽에 달아 오면 그쪽, §5.7) |
| 보호글 | `section.protected` `.protected-title` `.protected-desc` `.protected-form` `.protected-label` `.protected-input` `.protected-submit` |
| 방명록 | `section.guestbook` `.guestbook-title` — 본체는 `[##_guestbook_group_##]`, 안은 `tt-*` |
| 광고 | `.ad` `.ad-upper` `.ad-lower` — 비어 있을 때 여백이 생기지 않게 (자식이 없으면 높이 0) |
| 푸터 | `footer.site-footer` `.footer-inner` `.footer-brand`(안이 `a.footer-title` · `p.footer-desc`) `.footer-links` `.footer-copy` |
| 헤더 | `header.site-header` `.header-inner` `.site-brand` `.brand-title` `.brand-desc` `.site-nav` `.header-util` · `nav.cat-chips`(§5.9, 1024px 이하 전용) |
| 유틸 | `.a11y-hidden` (스크린리더 전용 텍스트) · `.skip-link` · `.icon` (모든 인라인 SVG) |

`nav.site-nav` 안은 `[##_blog_menu_##]`가 만든 **티스토리 고정 마크업**이다.
클래스를 기대하지 말고 `.site-nav ul` `.site-nav li` `.site-nav a`로 잡는다.
현재 메뉴에 붙은 항목 클래스는 티스토리 설정에 따라 달라진다.
**메뉴를 설정하지 않으면 빈 문자열이 아니라 빈 `<ul></ul>`이 온다**(2026-09-14 라이브 실측) —
"비었다"는 `.site-nav:has(> ul:empty)`로 잡는다. `:empty`는 폴백이다(결정 57).

### CSS 규칙이 없는 것이 정상인 마크업 클래스

린트 `BND009`는 `skin.html`이 내보내는 클래스에 CSS 규칙이 있는지 본다.
**마크업에서 이름을 바꾸고 CSS를 안 고치면 아무 에러도 안 난다** — 선택자가
매칭되지 않을 뿐이고 화면에는 스타일 없는 날것이 뜬다. `BND004`는 JS가 *찾는*
이름만, `BND006`은 JS가 *만드는* 이름만 봐서 **마크업이라는 가장 큰 표면
(140종 남짓)이 어느 쪽에도 안 걸려 있었다.**

아래는 규칙이 없는 것이 **정상**인 이름이다. §5.6의 예외 목록과 같은 형식이고
같은 규칙이 걸린다 — **이름 뒤에 `—`와 이유를 쓴다. 이름만 적은 줄은 예외로
치지 않는다.** 이유가 없으면 "정상"과 "아직 안 한 일"을 구분할 수 없다.

**부모·형제가 맡는다**

- `.entry` — 글 영역 루트. 폭·배치는 `.entry-layout`·`.entry-main`·`.entry-head`가 나눠 갖는다.
- `.list` — 목록 영역 루트. 안쪽 `.list-head`·`.post-list`가 전부 정한다.
- `.tagcloud` — 태그 클라우드 영역 루트. `.tagcloud-title`·`.tagcloud-list`가 맡는다.
- `.side-item` · `.related-item` · `.tagcloud-item` — `<li>`. 항목 간격은 각 목록
  컨테이너(`.side-list`·`.related-list`·`.tagcloud-list`)의 `gap`이, 내용은
  `.side-link`·`.related-link`·`.tagcloud-link`가 맡는다.
- `.entry-date` · `.post-date` · `.side-date` — 색·크기·정렬을 `.entry-meta`·
  `.post-meta`·`.side-meta`가 한 번에 정한다. 날짜만 다르게 할 이유가 아직 없다.
- `.paging-prev` · `.paging-next` — `.paging a`가 번호와 같은 알약으로 그린다.
  "더 갈 곳 없음" 상태는 티스토리가 붙이는 `.no-more-prev`/`.no-more-next`(하이픈)와
  **href 부재**가 가른다(§7 페이징 행). `.paging-num`은 이 목록에 없다 — 생략 부호·현재
  페이지(결정 53)와 767px 이하의 번호 줄이기(결정 66)가 그 이름에 직접 규칙을 건다.
- `.side-body` — 안이 `[##_category_list_##]`의 **티스토리 고정 마크업**이라
  `tistory.css`가 `.tt_category` 쪽 이름으로 잡는다.
- `.toc-title` — `.toc-toggle`이 flex 배치와 글자를 정한다. 라벨 자체에 줄 것이 없다.
- `.notice-body` — `skin.html`이 같은 요소에 `.contents_style`을 함께 달아(§5.7)
  `content.css`가 통째로 맡는다.

**기본 층이라 보정할 것이 없다** (변형 쪽만 규칙을 갖는다)

- `.postnav-prev` — `.postnav-item`의 기본 배치가 곧 이전 글 모양(썸네일 왼쪽)이다.
  좌우를 뒤집는 `.postnav-next`만 규칙을 갖는다. 여기에 규칙을 만들면 기본값을
  다시 적는 죽은 규칙이 된다.

**자리·모듈을 가르는 이름. 공통 클래스가 일을 한다**

- `.side-notice` · `.side-comments` · `.side-tags` · `.side-count` — 모듈 구분용.
  치장은 `.side-mod`가 공통으로 한다. 개별 치장이 필요해지면 붙일 자리다
  (`.side-category`·`.side-recent`·`.side-popular`는 이미 자기 규칙이 있다).
- `.ad-upper` · `.ad-lower` — 상·하단 자리 구분용. 여백은 `.ad:not(:empty)`가
  둘을 같이 다룬다. 위아래를 다르게 할 일이 생기면 붙일 자리다.

---

## 8. 상태 클래스 한눈에

| 클래스 | 붙는 곳 | 붙이는 주체 |
|---|---|---|
| `html[data-theme="dark"|"light"]` | `<html>` | head 인라인 + `#theme-toggle` |
| `html.js` | `<html>` | head 인라인 — 붙이고, **`script.js` 로드가 실패하면 지운다**. 뜻은 「스크립트가 실제로 도는 중」(§5.4, 결정 62) |
| `.toc.is-ready` | `#toc` | toc.js |
| `body.no-toc` | `<body>` | `skin.html` 인라인(첫 페인트 전, 결정 48) + toc.js 폴백 (**목차를 못 만들 때만**. 글 페이지가 아니면 붙이지 않는다) |
| `.toc.is-open` | `#toc` | toc.js (**1399px 이하에서만**. 3단으로 넘어가면 지운다) |
| `.toc-link.is-current` | 목차 링크 | toc.js 스크롤스파이 (`aria-current="location"`도 같이 옮긴다. 글 머리 목차와 떠 있는 목차 시트의 같은 번호 링크에 함께) |
| `.to-top.is-visible` | `#to-top` | progress.js |
| `.toc-fab.is-visible` | 떠 있는 목차 버튼 | toc-sheet.js (**1399px 이하이고 글 머리 `#toc`가 화면 위로 지나갔을 때만**. 3단으로 넘어가면 지운다, §5.1b) |
| `.code-copy.is-copied` | 복사 버튼 | code.js |
| `.code-wrap.has-lines` | 코드 래퍼 | code.js |
| `body.is-lightbox-open` | `<body>` | lightbox.js |
| `.external-link` | 본문 외부링크 `<a>` | links.js |
| `.heading-anchor` | 본문 `h2`/`h3` **안쪽 끝** | heading-anchor.js (**상태가 아니라 새 요소다.** 조건 없이 항상 붙는다) |
| `li.has-toggle` · `li.is-collapsed` / `li.is-expanded` | 사이드바 카테고리 `li` | category.js |
| `.cat-tree` | 상위 카테고리가 늘어선 `ul` | category.js |
| `.cat-chip.is-current` | 모바일 카테고리 칩 | cat-chips.js (현재 가지 — `li.selected` 또는 URL 대조. `aria-current`도 같이 — 자기 링크가 지금 페이지면 `"page"`, 가지만 맞으면 `"true"`) |
| `.cat-chips.is-off` | `#cat-chips` 그릇 | cat-chips.js (**칩을 하나도 못 넣고 끝날 때** — 트리를 못 읽었거나 모듈 안 예외. CSS 칩 줄 예약 `.js .cat-chips:empty:not(.is-off)`를 푸는 신호, §5.9·결정 62) |

`body.with-phocus`는 이 표에 없다 — 티스토리 phocus 뷰어가 붙이고 `lightbox.js`는 **읽기만** 한다(§5.6 「라이트박스 — phocus가 먼저」, 결정 60).

**`aria-current` — 색으로만 보이던 「현재 위치」를 스크린리더에도 알리는 자리.** 클래스가 아니라 속성이라
위 표에 넣지 않는다(표 첫 칸은 린트 `BND006`·`BND007`이 우리 JS가 만드는 **클래스**로 읽는다).
**`"page"`는 그 링크가 지금 페이지 자체일 때만 쓴다**(레일·칩 공통, 판정은 `category.isHere()` — 디코딩하고 끝 `/`를 뗀
경로가 같을 때). 지금 페이지를 품은 가지는 `"page"`가 아니다 — 칩은 하위가 없어 상위 칩이 가지를 대표하므로 `"true"`,
레일은 하위 링크가 따로 있어 상위 링크에는 붙이지 않는다(결정 63).

- 목차 — `.toc-link.is-current`와 같은 링크에 `aria-current="location"`. toc.js 스크롤스파이가 둘을 같은 자리에서 옮긴다(§5.1). 떠 있는 목차 시트의 같은 번호 링크도 함께(§5.1b)
- 사이드바 카테고리 — 티스토리 `li.selected` 중 **자기 링크가 지금 경로인 `li`의 그 링크**에 `aria-current="page"`. category.js(§5.6 「JS가 지키는 것」). URL 대조로 펼친 가지·하위 페이지의 상위 링크에는 붙이지 않는다
- 목록 페이징 — 티스토리 `span.selected`(현재 페이지 표시, 결정 53)를 품은 `.paging` 안의 앵커에 `aria-current="page"`. paging.js
- 모바일 카테고리 칩 — `.cat-chip.is-current`와 함께 `aria-current`. 칩 링크가 지금 페이지면 `"page"`, 하위 카테고리 페이지라서 가지만 현재면 `"true"`. cat-chips.js(§5.9, 위 표)

### `.toc-toggle`의 `aria-expanded` — 뷰포트에 따라 존재 자체가 달라진다

`skin.html`의 `.toc-toggle`은 `aria-expanded="false"`를 하드코딩하지만 **그 값이 사용자에게 도달하는 경로는 없다**
(`.toc`는 `.is-ready` 없이는 `display:none`이고 `.is-ready`는 toc.js만 붙인다). 실제 값은 toc.js가 정한다.

| 뷰포트 | `aria-expanded` | `tabindex` | 이유 |
|---|---|---|---|
| ~1399px (접이식 활성) | `"false"` / `"true"` — `.is-open`과 동기 | 없음(=0) | 눌리고, 눌리면 목록 높이가 바뀐다 |
| 1400px~ (3단, 목차가 옆 칸) | **속성 없음** | `"-1"` | CSS가 `pointer-events:none`으로 라벨화한다. 목록은 항상 펼쳐져 있으므로 "축소됨"은 거짓말이고, 아무 일도 못 하는 탭 정거장도 만들지 않는다 |

`matchMedia('(max-width: 1399px)')`를 구독하므로 창 크기를 바꾸면 따라온다.
**CSS의 `1399px` 경계를 옮기면 `toc.js`의 `COLLAPSIBLE_MQ`도 같이 옮겨야 한다** — 린트 `BND010`이 넷(toc.js · components.css max/min · layout.css 3단)을 대조한다. 이 경계는 레일 경계(1025)가 아니라
`layout.css`의 3단 경계(1400)다 — 둘을 섞어 썼던 것이 1280px에서 목차가 본문 위에 펼쳐진 채 고정된 원인이었다(결정 48).

---

## 9. 확정하지 못한 것 (QA가 실블로그에서 확인해야 함)

1. **`s_notice_rep`의 정체.** 공식 문서가 두 가지로 읽힌다 — (a) 공지 글 퍼머링크 영역, (b) 홈 상단 공지 반복.
   빈 화면을 피하려고 **본문(`[##_notice_rep_desc_##]`)까지 넣었다.** (b)라면 홈 맨 위에 공지 전문이 깔린다.
   테스트 블로그에 공지를 하나 만들어 확인하고, (b)면 `#tt-body-index .notice-body`를 접거나
   마크업에서 desc를 빼야 한다.
2. ~~**홈에서 `s_list`가 함께 렌더되는지.**~~ **해결 (2026-08-25)** — 렌더된다. 그래서 홈 목록을
   `s_index_article_rep`로 따로 그리지 않고 `s_list` 한 벌로 홈까지 그린다(결정 29, §2 「카드는 s_list_rep 한 벌뿐이다」).
3. ~~**`index.xml`의 `<tree>` 색이 다크모드에서 어떻게 나오는지.**~~ **해결 (2026-08-25)** —
   `[##_category_list_##]`(리스트형)로 바꾸면서 `<tree>` 설정이 닿지 않는 형식이 되어 인라인 `style`이
   0개가 됐다. `!important`도 `index.xml` 수정도 필요 없다 (DECISIONS.md 결정 31).

   **대신 다른 경로로 같은 종류의 문제가 있었다** — 본문 에디터 컴포넌트다. 티스토리가 인라인이 아니라
   **자기 스타일시트**에서 라이트 전용 색을 칠하고, 상당수가 `#tt-body-page` ID 스코프라 클래스로는
   못 이긴다. `tistory.css`에서 덮는다 (DESIGN.md §5.2b, 결정 32).
4. **헤더의 `s_search`.** 공식 문서 예시는 사이드바 안이다. 헤더에서도 동작하는지 실블로그 확인.
