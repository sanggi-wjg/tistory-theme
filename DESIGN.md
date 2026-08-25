---
version: 1.0
name: sanggi-jayg-tistory-skin
description: "sanggi-jayg.tistory.com 커스텀 티스토리 스킨의 디자인 시스템. getdesign.md의 Vercel 분석을 기반으로 하되, 한글 본문(Pretendard)·티스토리 고정 마크업·기존 글 275편의 인라인 스타일 오염을 반영해 재구성했다. 근백색 캔버스에 잉크 블랙, 촘촘한 그레이 사다리, 색은 링크와 포인트에만. 본문에 이미 코드 하이라이트와 스크린샷 147장이 색을 갖고 있으므로 크롬은 끝까지 조용하게 유지한다."

colors:
  light:
    canvas: "#ffffff"
    canvas-soft: "#fafafa"
    canvas-soft-2: "#f5f5f5"
    surface: "#ffffff"
    hairline: "#ebebeb"
    hairline-strong: "#a1a1a1"
    ink: "#171717"
    ink-body: "#4d4d4d"
    ink-mute: "#707070"
    link: "#0070f3"
    link-deep: "#0761d1"
    link-bg-soft: "#d3e5ff"
    error: "#ee0000"
    warning: "#f5a623"
    accent-cyan: "#29bc9b"
    selection-bg: "#171717"
    selection-fg: "#f2f2f2"
  dark:
    canvas: "#000000"
    canvas-soft: "#0a0a0a"
    canvas-soft-2: "#111111"
    surface: "#0a0a0a"
    hairline: "#2e2e2e"
    hairline-strong: "#454545"
    ink: "#ededed"
    ink-body: "#a1a1a1"
    ink-mute: "#8f8f8f"
    link: "#3291ff"
    link-deep: "#52a8ff"
    link-bg-soft: "#10233f"
    error: "#ff6166"
    warning: "#f7b955"
    accent-cyan: "#50e3c2"
    selection-bg: "#ededed"
    selection-fg: "#171717"

typography:
  families:
    sans: 'Pretendard Variable, Pretendard, -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif'
    mono: '"JetBrains Mono", "D2Coding", ui-monospace, SFMono-Regular, Consolas, monospace'
  scale:
    display-xl: { fontSize: 48px, lineHeight: 1.05, letterSpacing: -0.028em, fontWeight: 700 }
    display-lg: { fontSize: 32px, lineHeight: 1.25, letterSpacing: -0.022em, fontWeight: 700 }
    display-md: { fontSize: 24px, lineHeight: 1.33, letterSpacing: -0.018em, fontWeight: 600 }
    display-sm: { fontSize: 20px, lineHeight: 1.4,  letterSpacing: -0.012em, fontWeight: 600 }
    body-lg:    { fontSize: 18px, lineHeight: 1.75, letterSpacing: 0,        fontWeight: 400 }
    body:       { fontSize: 16px, lineHeight: 1.75, letterSpacing: 0,        fontWeight: 400 }
    body-sm:    { fontSize: 14px, lineHeight: 1.6,  letterSpacing: 0,        fontWeight: 400 }
    caption:    { fontSize: 12px, lineHeight: 1.5,  letterSpacing: 0,        fontWeight: 400 }
    mono:       { fontSize: 13px, lineHeight: 1.7,  letterSpacing: 0,        fontWeight: 400 }

spacing:
  base: 4px
  scale: [4, 8, 12, 16, 24, 32, 48, 64, 96]

radius:
  sm: 4px
  md: 6px
  lg: 8px
  xl: 12px
---

# DESIGN.md — 상쾌한기분 티스토리 스킨

이 문서는 **디자인 일관성의 단일 출처**다. 색·타이포·간격에 대한 판단이 필요할 때 여기를 먼저 본다.
결정의 배경과 근거는 [DECISIONS.md](./DECISIONS.md)에 있다.

---

## 1. 기반과 각색

**기반**: [getdesign.md](https://getdesign.md)의 Vercel 분석 (`npx getdesign@latest add vercel`, 또는 `getdesign` npm 패키지의 `templates/vercel.md`)

**왜 Vercel인가**
이 블로그의 본문은 이미 색을 많이 갖고 있다 — 코드블록 728개의 하이라이팅, 스크린샷 147장. 테마 크롬이 조용할수록 글이 산다. Vercel 시스템은 그레이 사다리가 촘촘해 구분선·비활성·보조 텍스트가 각자 자리를 갖고, 색은 링크에만 쓴다. 다크 팔레트 파생도 이 사다리 덕분에 안정적이다.

**원본에서 바꾼 것**

| 항목 | 원본 | 이 스킨 |
|---|---|---|
| 본문 폰트 | Geist / Inter | **Pretendard** — 한글 본문이므로 |
| 코드 폰트 | (명시 없음) | **JetBrains Mono + D2Coding 로컬 폴백** — 코드블록 33%에 한국어가 섞임 |
| 다크 팔레트 | 없음 (단일 모드 분석) | **파생** — 아래 §2에 정의 |
| 히어로 메시 그라디언트 | 마케팅 히어로 전체 | **쓰지 않음** — 개인 블로그에 과함 |
| 자간 | px 고정 음수값 | **em 기준으로 완화** — 한글은 과한 음수 자간에서 가독성이 떨어짐 |

---

## 2. 색

### 토큰 정의

라이트를 기본으로 정의하고, 다크는 토큰만 재정의한다. **컴포넌트는 언제나 토큰을 통해 색을 참조한다.** 미디어쿼리나 `[data-theme]` 블록 안에서 색을 처음 정의하는 일이 없어야 한다.

```css
:root {
  --canvas:        #ffffff;
  --canvas-soft:   #fafafa;
  --canvas-soft-2: #f5f5f5;
  --surface:       #ffffff;
  --hairline:      #ebebeb;
  --hairline-strong: #a1a1a1;
  --ink:           #171717;
  --ink-body:      #4d4d4d;
  --ink-mute:      #707070;   /* 2026-08-25 #888888에서 내림 — §8.1 참조 */
  --link:          #0070f3;
  --link-deep:     #0761d1;
  --link-bg-soft:  #d3e5ff;
  --error:         #ee0000;
  --warning:       #f5a623;
  --accent-cyan:   #29bc9b;
  --selection-bg:  #171717;
  --selection-fg:  #f2f2f2;

  /* 모서리 — 테마와 무관하므로 여기서 한 번만 정의한다.
     frontmatter의 `radius:`는 YAML 메타데이터일 뿐 CSS가 아니다.
     정의하지 않은 채 var()를 쓰면 폴백이 없어 border-radius가 0으로 조용히 떨어진다. */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-xl: 12px;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { /* 아래 다크 토큰 */ }
}
:root[data-theme="dark"] { /* 동일한 다크 토큰 */ }
```

**다크 토큰**

```
--canvas: #000000        --ink: #ededed        --link: #3291ff
--canvas-soft: #0a0a0a   --ink-body: #a1a1a1   --link-deep: #52a8ff
--canvas-soft-2: #111111 --ink-mute: #8f8f8f   --link-bg-soft: #10233f
--surface: #0a0a0a       --hairline: #2e2e2e   --error: #ff6166
                         --hairline-strong: #454545  --warning: #f7b955
--selection-bg: #ededed  --selection-fg: #171717     --accent-cyan: #50e3c2
```

### 사용 규칙

- **색은 링크와 포인트에만.** 목차 현재 위치, 카테고리 라벨, 태그 호버, 포커스 링.
- **면으로 구분하지 말고 선으로 구분한다.** 카드·사이드바·코드블록은 `--hairline` 1px 테두리로 분리한다. 배경 채우기는 `--canvas-soft`까지만.
- **그림자를 쓰지 않는다.** 깊이는 그레이 사다리와 hairline으로 만든다.
- `--hairline-strong`는 입력 포커스와 강조 구분선에만.
- 다크에서 순검정 `#000000`을 캔버스로 쓰되, 카드·코드블록은 `--canvas-soft`로 한 단 올려 층위를 만든다.

### 다크 모드 동작

- 기본값은 **시스템 설정을 따른다**. 사용자가 토글하면 `localStorage`에 기억하고 `:root[data-theme]`로 고정한다.
- 세 가지 상태를 모두 다뤄야 한다: `data-theme="dark"` / `data-theme="light"` / **stamp 없음(시스템 따름)**.
- `body`에 토큰 배경을 명시적으로 지정한다.

---

## 3. 타이포그래피

### 폰트

```css
--font-sans: "Pretendard Variable", Pretendard, -apple-system,
             "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
--font-mono: "JetBrains Mono", "D2Coding", ui-monospace,
             SFMono-Regular, Consolas, monospace;
```

- **Pretendard는 dynamic subset으로 로드한다** (jsDelivr). 전체 변수폰트는 2.0MB이지만 dynamic subset은 페이지에 실제로 쓰인 글자가 든 조각만 받는다.
- **코드 폰트에서 `D2Coding`이 `JetBrains Mono` 뒤에 오는 이유**: 라틴은 JetBrains Mono가 처리하고, 한글은 로컬에 D2Coding이 설치된 방문자에게 고정폭으로 렌더된다. 코드블록의 33%(239개)에 한국어가 섞여 있다.
- **Font Awesome을 쓰지 않는다.** CSS 102KB + 웹폰트 258KB = 최대 360KB를 아이콘 몇 개에 쓸 이유가 없다. 필요한 아이콘은 인라인 SVG로 넣는다.

### 스케일

| 토큰 | 크기 | 행간 | 자간 | 굵기 | 용도 |
|---|---|---|---|---|---|
| `display-xl` | 48px | 1.05 | -0.028em | 700 | 쓰지 않음 (예비) |
| `display-lg` | 32px | 1.25 | -0.022em | 700 | 글 제목 |
| `display-md` | 24px | 1.33 | -0.018em | 600 | 본문 h2 |
| `display-sm` | 20px | 1.40 | -0.012em | 600 | 본문 h3, 카드 제목 |
| `body-lg` | 18px | 1.75 | 0 | 400 | 리드 문단 |
| `body` | 16px | 1.75 | 0 | 400 | 본문 기본 |
| `body-sm` | 14px | 1.60 | 0 | 400 | 카드 요약, 사이드바 |
| `caption` | 12px | 1.50 | 0 | 400 | 날짜, 메타 |
| `mono` | 13px | 1.70 | 0 | 400 | 코드 |

### 헤딩 구조 — 페이지마다 `h1` 하나

| 페이지 | `h1` | 어디서 오는가 |
|---|---|---|
| 글 | `.entry-title` | `<s_permalink_article_rep>` |
| 목록 4종 | `.list-title` | `<s_list>` |
| 태그 클라우드 | `.tagcloud-title` | `<s_tag>` |
| 방명록 | `.guestbook-title` | `<s_guest>` |
| **홈** | **없다 — 알고 남긴 예외** | — |

**헤더의 블로그 이름은 `h1`이 아니다.** 헤더는 모든 페이지에 있으므로 거기에 `h1`을 두면
글·목록에서 그 페이지의 `h1`과 겹쳐 **마크업에 `h1`이 둘**이 된다. CSS로 감춰도 원시 HTML에는
남고, 크롤러와 `seo-verify-live`의 `V003`은 원시 HTML을 센다 — 감춤 방식으로 만들어 본 결과
홈을 뺀 전 페이지가 `h1` 2개였다.

**홈에 `h1`을 놓을 자리는 티스토리에 없다.** 홈 전용 영역은 `<s_index_article_rep>`(글마다 반복)과
커버뿐이다(`data/substitutions.json`의 `areaScope`). 한 장짜리 스킨에서 "홈은 블로그 이름,
글은 글 제목"을 `h1` 하나로 만드는 것은 구조적으로 불가능하다.

그래서 **글 275편과 목록 4종을 정확히 맞추고 홈 하나를 포기했다.** 홈은 블로그 이름으로 검색되는데
그 이름은 `<title>`과 헤더 링크 텍스트가 이미 담고 있다. `V003`은 홈에서만 경고로 낮췄다 —
배포할 때마다 같은 오류가 뜨면 오류 전체를 무시하게 된다.

- 본문 소제목은 에디터가 만든다. 스킨은 `h2`·`h3`만 상정하고 목차도 그 둘만 모은다.
- 공지 제목은 `h2`다. 공지 영역은 반복이라 `h1`을 쓰면 공지 수만큼 늘어난다.

### 원칙

- **한글에는 음수 자간을 아끼라.** 원본 Vercel은 48px에서 -2.4px(-0.05em)까지 당기지만, 한글은 그만큼 당기면 자소가 붙어 보인다. 이 스케일은 최대 -0.028em으로 완화했다.
- **본문 행간은 1.75.** 본문 길이 중앙값 2,813자, 최대 30,314자. 긴 글을 오래 읽는 블로그다.
- **본문 폭은 68~72자 내외.** 글 페이지는 1단이지만 무한정 넓히지 않는다.
- 대문자 라벨(eyebrow, 사이드바 제목)에만 양수 자간 `0.1em`을 준다.
- 숫자가 세로로 정렬되는 곳(방문자 수, 날짜 목록)은 `font-variant-numeric: tabular-nums`.

---

## 4. 레이아웃

### 골격 (E안)

| 페이지 | `body_id` | 구성 |
|---|---|---|
| 홈 | `tt-body-index` | 주목 글 1 + 3열 카드 그리드 |
| 목록 (카테고리·검색·태그·보관함) | `tt-body-category` 등 | 2단 — 본문 목록 + 우측 사이드바 |
| 글 | `tt-body-page` | 1단 본문 + 우측 목차 |
| 방명록·보호글·공지 | 각 id | 1단, 최소 스타일 |

`body_id`로 CSS를 분기한다. 헤더·푸터는 전 페이지 공유.

### 간격

4px 기준. `4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96`

- 카드 내부 패딩 16px, 카드 사이 간격 24px
- 섹션 사이 48px, 페이지 상하 여백 64px
- 본문 문단 사이 24px, 소제목 위 48px / 아래 16px

### 모서리

`sm 4px` (태그·인라인코드) · `md 6px` (버튼·입력) · `lg 8px` (카드·코드블록) · `xl 12px` (히어로)

### 반응형

단일 반응형 스킨이다. 모바일 전용 스킨은 존재하지 않는다.

| 폭 | 홈 그리드 | 목록 | 글 |
|---|---|---|---|
| ~640px | 1열 | 사이드바 하단으로 | 목차 접이식 |
| 641~1024px | 2열 | 사이드바 하단으로 | 목차 접이식 |
| 1025px~ | 3열 | 2단 | 1단 + 우측 목차 |

넓은 콘텐츠(코드블록·표·다이어그램)는 각자 `overflow-x: auto` 컨테이너 안에서 스크롤한다. **페이지 본문이 가로로 스크롤되면 안 된다.**

---

## 5. 티스토리 고정 마크업 다루기

이 프로젝트에서 CSS 작업의 큰 덩어리는 **내가 클래스를 붙일 수 없는 HTML**을 다스리는 일이다. 아래 세 영역은 티스토리가 통째로 렌더링하며 마크업을 수정할 수 없다.

### 5.1 본문 `.contents_style`

래퍼는 `<div class="tt_article_useless_p_margin contents_style">`. **`class="contents_style"` 정확일치로 찾으면 안 된다** — 오래된 글이 누락된다.

에디터가 만드는 요소: `<figure class="imageblock">` · `<pre data-ke-type="codeblock">` · `<blockquote data-ke-style>` · `<p data-ke-size>` · 인라인 `<code>` · `<table>`

**인라인 `<code>`가 274개(글당 최대 68개)로 코드블록보다 많다.** 본문 CSS의 1급 시민으로 다룬다.

```css
.contents_style code {
  font-family: var(--font-mono);
  font-size: 0.88em;
  background: var(--canvas-soft-2);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  padding: 1px 5px;
  color: var(--ink);
}
```

### 5.2 인라인 스타일 오염 무력화

기존 글 275편에 인라인 스타일이 박혀 있다. **CSS 열거 + JS 안전망 하이브리드**로 처리한다.

**폰트 — 13종 275곳 전부 무력화**

```css
.contents_style [style*="font-family"] { font-family: inherit !important; }
```

값의 실체는 `Script` 106 · `AppleSDGothicNeo-Regular` 75 · `Noto Sans DemiLight` 55 · `Tahoma` 10 · `fixedsys` 6 · `dotum` 4 등으로, 외부에서 붙여넣거나 구버전 에디터가 남긴 것들이다. 본문 타이포를 흐트러뜨릴 뿐 지켜야 할 의도가 없다.

**`inherit`이어야 하는 이유** — 5곳(`Menlo/Consolas/Monaco/monospace` 2 · `monaco` 2 · `hack` 1)은 코드 문맥의 고정폭 지정이다. `var(--font-sans)`로 덮으면 코드가 가변폭이 되어 정렬이 깨진다. `inherit`은 부모에서 물려받으므로, `<pre>`/`<code>` 안이면 우리가 지정한 `--font-mono`를, 본문이면 `--font-sans`를 자동으로 받는다.

**색 — 빌드가 `data/inline-styles.json`에서 생성한다.** 어두운 색 14종 593곳, 밝은 색 3종 16곳, 배경 11종 106곳.

**손으로 쓰지 않는 이유가 두 가지다.**

첫째, **공백**. 실제 블로그의 인라인 스타일은 `style="color: #000000;"` — 콜론 뒤에 공백이 있다. 609곳 중 **608곳이 공백형**이다. CSS 속성 선택자는 문자열을 문자 그대로 매칭하므로 `[style*="color:#000000"]`은 **609곳 중 1곳에만** 걸린다. 두 형태를 모두 써야 한다.

둘째, **동기화**. 색 목록은 글이 늘면 바뀐다. 손으로 관리하면 실측과 어긋나고, 어긋난 사실이 조용히 묻힌다.

`scripts/build.mjs`가 측정 데이터에서 규칙을 생성해 `style.css` 끝에 붙인다. 생성 결과의 모양은 이렇다:

```css
/* ── 인라인 스타일 보정 (data/inline-styles.json에서 생성) ── */

/* 다크에서 죽는 어두운 텍스트 → 본문 색으로 */
:root[data-theme="dark"] .contents_style [style*="color:#000000"],
:root[data-theme="dark"] .contents_style [style*="color: #000000"],
:root[data-theme="dark"] .contents_style [style*="color:#333333"],
:root[data-theme="dark"] .contents_style [style*="color: #333333"],
/* … 14종 × 2형태 … */ { color: var(--ink-body) !important; }

/* 강조색은 죽이지 말고 다크용으로 매핑 */
:root[data-theme="dark"] .contents_style [style*="color:#006dd7"],
:root[data-theme="dark"] .contents_style [style*="color: #006dd7"] { color: var(--link) !important; }
:root[data-theme="dark"] .contents_style [style*="color:#ee2323"],
:root[data-theme="dark"] .contents_style [style*="color: #ee2323"] { color: var(--error) !important; }

/* 라이트에서 대비가 부족한 밝은 텍스트 (지금도 잘 안 보인다) */
:root:not([data-theme="dark"]) .contents_style [style*="color: #eeffff"],
/* … 3종 × 2형태 … */ { color: var(--ink-body) !important; }

/* 밝은 배경 → 다크에서 흰 상자가 뜬다 */
:root[data-theme="dark"] .contents_style [style*="background-color: #ffffff"],
/* … 9종 × 2형태 … */ { background-color: var(--canvas-soft) !important; }

/* 어두운 배경 → 라이트에서 검은 상자가 뜬다 */
:root:not([data-theme="dark"]) .contents_style [style*="background-color: #212121"],
/* … 2종 × 2형태 … */ { background-color: var(--canvas-soft-2) !important; }
```

**강조색 매핑은 생성기가 예외로 둔다.** `#006dd7`(파랑 강조) → `--link`, `#ee2323`(빨강 강조) → `--error`. 나머지는 휘도로 분류한다 — 0.5 미만이면 다크에서, 이상이면 라이트에서 보정한다.

**색 목록이 바뀌면** `/blog-census --bodies`로 `data/inline-styles.json`을 갱신하고 다시 빌드한다. CSS를 손댈 필요가 없다.
**JS 안전망**: 위 목록에 없는 색(앞으로 쓸 새 글)을 위해, 본문 인라인 색의 상대 휘도를 계산해 현재 모드에서 대비가 부족하면 제거한다. CSS가 먼저 적용되므로 깜박임은 없다.

### 5.3 카테고리 트리

`[##_category_##]`가 통째로 렌더링한다. 클래스는 고정이며 마크업은 바꿀 수 없다.

```
ul.tt_category > li > a.link_tit          "분류 전체보기" + span.c_cnt
  ul.category_list > li > a.link_item     상위 카테고리
    ul.sub_category_list > li > a.link_sub_item   하위 카테고리
```

- 접기/펼치기가 필요하면 JS로 DOM을 조작한다.
- `index.xml`의 `<tree>` 설정(색·글자수·글수 표시)도 함께 관리한다.
- **상위 14종 / 하위 21종 → 트리 36줄** (`분류 전체보기` 1 + 14 + 21). 개편 전 48줄(1 + 11 + 36). 전체 목록과 순서는 `DECISIONS.md` §3, 정본은 `data/categories.json`.
- `span.c_cnt`는 `--ink-mute`, `tabular-nums`.

### 5.4 댓글·방명록

`[##_comment_group_##]` / `[##_guestbook_group_##]` 한 줄이면 티스토리 React 앱이 UI 전체를 렌더링한다. 우리는 `tt-*` 클래스에 토큰을 입힌다.

주요 훅: `.tt-comment-cont` · `.tt-box-total` · `.tt-area-reply` · `.tt-list-reply` · `.tt-item-reply` · `.tt-box-thumb` · `.tt-thumbnail` · `.tt-link-user` · `.tt_desc` · `.tt_date` · `.tt-cmt` · `.tt-btn_register`

**직접 마크업을 짜지 않는다.** `<s_rp>` 계열 치환자는 구형이라 핀 고정·프로필 레이어·더보기를 잃는다.

---

## 6. 컴포넌트

### 6.1 카드 (홈 그리드 / 목록)

```
.post
  .thumb        16:10, radius lg, 1px hairline
    img         대표이미지가 있을 때만 (치환자가 없으면 블록째 사라짐)
  .cat          caption, --link
  .title        display-sm, 2줄 클램프
  .meta         caption, --ink-mute, tabular-nums
```

- **제목은 반드시 2줄에서 자른다.** 홈에 노출되는 최신 20편의 제목 중앙값이 49자, 40자 초과가 75%다.
- 카드 높이를 고정해 그리드 정렬을 유지한다.
- **`.thumb`의 CSS는 §6.2가 통째로 갖는다.** 여기서 따로 쓰지 않는다 — 상자 속성(`display` `position` `overflow`)이 §6.2의 기본 이미지 3층 구조를 떠받치고 있어서, 두 곳에서 정의하면 갈라진다.

### 6.2 대표이미지 기본값

대표이미지 보유율은 전체 45%, 홈 노출분 85%다. 없는 글은 **상위 카테고리별 기본 이미지**로 메운다.

```html
<article class="post" data-cat="[##_list_rep_category_##]">
  <span class="thumb">
    <s_list_rep_thumbnail><img src="[##_list_rep_thumbnail_##]" alt=""></s_list_rep_thumbnail>
  </span>
</article>
```

**3층으로 쌓는다.** 격자는 CSS, 모티프는 마스크, 진짜 이미지는 그 위.

```css
/* 0층 — 상자. 위의 세 줄은 장식이 아니라 기계장치다. 지우면 조용히 무너진다.
   · display   — `<span class="thumb">`는 기본이 inline이라 크기를 못 갖는다
   · position  — 없으면 2층 ::before가 .thumb가 아니라 페이지 전체에 붙는다
                 (실측: 높이 1028px짜리 모티프가 화면을 덮었다)
   · overflow  — 모티프와 img를 radius로 잘라낸다 */
.post .thumb {
  display: block;
  position: relative;
  overflow: hidden;
  aspect-ratio: 16 / 10;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-lg);

  /* 1층 — 점격자. 순수 CSS라 SVG 용량이 0이고 토큰을 그냥 따른다 */
  background-color: var(--canvas-soft);
  background-image: radial-gradient(circle, var(--hairline) 1.1px, transparent 1.2px);
  background-size: 8px 8px;
  background-position: -1px -1px;
}

/* 2층 — 모티프. 모양은 마스크가, 색은 토큰이 정한다 */
.post .thumb::before {
  content: ""; position: absolute; inset: 0;
  background-color: var(--ink-mute);
  opacity: .62;
  -webkit-mask: var(--ph-default) center / cover no-repeat;
          mask: var(--ph-default) center / cover no-repeat;
}

/* 상위 14종. 순서는 사이드바 노출 순 (DECISIONS.md §3) */
.post[data-cat="인프라"] .thumb::before,
.post[data-cat^="인프라/"] .thumb::before        { -webkit-mask-image: var(--ph-infra);   mask-image: var(--ph-infra); }
.post[data-cat="Kotlin·Java"] .thumb::before    { -webkit-mask-image: var(--ph-jvm);     mask-image: var(--ph-jvm); }
.post[data-cat="Python"] .thumb::before,
.post[data-cat^="Python/"] .thumb::before       { -webkit-mask-image: var(--ph-python);  mask-image: var(--ph-python); }
.post[data-cat="PHP"] .thumb::before,
.post[data-cat^="PHP/"] .thumb::before          { -webkit-mask-image: var(--ph-php);     mask-image: var(--ph-php); }
.post[data-cat="아키텍처"] .thumb::before,
.post[data-cat^="아키텍처/"] .thumb::before       { -webkit-mask-image: var(--ph-arch);    mask-image: var(--ph-arch); }
.post[data-cat="데이터베이스"] .thumb::before,
.post[data-cat^="데이터베이스/"] .thumb::before    { -webkit-mask-image: var(--ph-db);      mask-image: var(--ph-db); }
.post[data-cat="네트워크"] .thumb::before         { -webkit-mask-image: var(--ph-net);     mask-image: var(--ph-net); }
.post[data-cat="보안"] .thumb::before            { -webkit-mask-image: var(--ph-sec);     mask-image: var(--ph-sec); }
.post[data-cat="AI"] .thumb::before             { -webkit-mask-image: var(--ph-ai);      mask-image: var(--ph-ai); }
.post[data-cat="코드 품질"] .thumb::before,
.post[data-cat^="코드 품질/"] .thumb::before      { -webkit-mask-image: var(--ph-quality); mask-image: var(--ph-quality); }
.post[data-cat="Go"] .thumb::before             { -webkit-mask-image: var(--ph-go);      mask-image: var(--ph-go); }
.post[data-cat="알고리즘"] .thumb::before         { -webkit-mask-image: var(--ph-algo);    mask-image: var(--ph-algo); }
.post[data-cat="개발 도구"] .thumb::before,
.post[data-cat^="개발 도구/"] .thumb::before      { -webkit-mask-image: var(--ph-tool);    mask-image: var(--ph-tool); }
.post[data-cat="기록"] .thumb::before            { -webkit-mask-image: var(--ph-note);    mask-image: var(--ph-note); }

/* 3층 — 진짜 대표이미지가 있으면 앞의 둘을 덮는다. z-index가 있어야 ::before 위로 온다 */
.post .thumb img { position: relative; z-index: 1; width: 100%; height: 100%; object-fit: cover; }

/* 카테고리 목록에서는 같은 그림이 최대 15번 반복되므로 감춘다 */
#tt-body-category .post:not(:has(.thumb img)) .thumb { display: none; }
```

- **한 카테고리에 파일 하나면 된다.** 마스크는 알파만 쓰므로 색이 `background-color`에서, 곧 **토큰에서만** 나온다. §2의 "미디어쿼리 안에서 색을 처음 정의하지 않는다"가 이미지까지 확장된다. 라이트/다크 두 벌을 만들 필요가 없어 **14장 + 기본값 1장 = 15장**이다.
- **대가는 단색이다.** 모티프 안에서 색을 나눌 수 없다. 강약은 SVG 안의 `opacity`로만 준다(`ai.svg`의 간선이 그렇게 흐리다). 링크색 강조는 포기했다 — 카드에서 색을 갖는 것은 `.cat` 라벨 하나로 충분하다.
- **접두사 충돌이 없다** — 상위 14종 중 어느 이름도 다른 이름의 접두사가 아니다. `^=`가 옆 카테고리를 물지 않는다.
- **하위가 없는 7종**(`Kotlin·Java` `네트워크` `보안` `AI` `Go` `알고리즘` `기록`)은 `^=` 줄을 두지 않았다. 하위가 생기면 두 줄짜리로 바꾼다 — 안 바꾸면 새 하위 글이 `--ph-default`로 조용히 떨어진다.
- 이름에 `&`가 없어 이스케이프 걱정은 사라졌지만 **`코드 품질`·`개발 도구`에는 공백이 있으므로** 값은 계속 따옴표로 감싼다.
- **`--ph-*` 변수명은 `src/assets/placeholders/`의 SVG 파일명에서 그대로 나온다** (`arch.svg` → `--ph-arch`). 빌드가 파일을 훑어 `data:` URI로 만들 뿐 이름을 검사하지 않으므로, **파일명을 틀리면 변수가 정의되지 않고 카드는 조용히 `--ph-default`로 떨어진다.** 위 블록의 이름이 곧 파일명 목록이다.
- **도안을 고칠 때는 SVG를 직접 손대지 말고 `scripts/gen-placeholders.py`를 고쳐 다시 돌린다.** 15장이 한 파일에 정의돼 있어 좌표·굵기 규칙을 한눈에 맞출 수 있다.
- **카테고리를 늘리거나 이름을 바꾸면 이 블록과 생성기를 같이 고친다.** 린트 `BND003`이 `data/categories.json`과 대조해 빠진 상위를 잡는다.
- **기본 이미지는 SVG를 `data:` URI로 `style.css`에 인라인한다.** 배포가 수동이므로 업로드할 파일 수를 줄인다. 15장 전부 합쳐 **base64 약 8KB**다.
- **카테고리 목록 상단에는 `<s_list_image>` / `[##_list_image_##]`로 카테고리 대표이미지를 배너 1장으로 깐다.** 다만 이 치환자는 관리 화면에서 카테고리 대표이미지를 설정해야 값이 나오고, 없으면 블록째 사라진다 — **기본 이미지를 배너로 대신 쓸지는 미정**이다(`DECISIONS.md` 미결 12).

### 6.3 코드블록

```css
.contents_style pre {
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.7;
  background: var(--canvas-soft);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-lg);
  padding: 16px;
  overflow-x: auto;          /* 줄바꿈하지 않는다 — 최대 1,777자짜리 줄이 있다 */
}
```

- **언어 라벨은 우상단에 표시**하되, `data-ke-language` 값이 아니라 **자동 감지 결과**를 쓴다. 728개 중 라벨이 있는 것은 285개(39%)뿐이고, `javascript` 44개는 실제로 전부 셸·설정·SQL·한국어 메모다.
- **감지 신뢰도가 낮으면 하이라이팅하지 않고 라벨도 숨긴다.** 한국어 메모 블록이 엉뚱하게 물드는 것을 막는다.
- highlight.js 언어 번들은 필요한 것만: `python bash shell sql java kotlin go json yaml xml`
- 복사 버튼은 우상단, 호버 시 노출. 줄 번호는 일정 줄 수 이상에서만.

### 6.4 목차 (TOC)

본문 `h2`/`h3`를 JS로 스캔해 생성한다. 소제목 3개 이상인 글이 68%, 최대 25개다.

- 현재 위치는 `--link` + 좌측 2px 바
- `position: sticky`, 1024px 미만에서는 본문 상단 접이식으로 전환
- 소제목이 3개 미만이면 목차를 렌더링하지 않는다

### 6.5 링크

```css
.contents_style a {
  color: var(--link);
  text-decoration: underline;
  text-underline-offset: 0.2em;
  text-decoration-thickness: 1px;
}
.contents_style a:hover { color: var(--link-deep); }
```

외부 링크(65개)는 `target="_blank" rel="noopener"`와 작은 아이콘을 JS로 붙인다.

### 6.6 표

표는 7편 14%에 불과하지만 최대 4열이라 모바일에서 반드시 깨진다. JS로 `overflow-x: auto` 컨테이너를 감싼다.

---

## 7. 하지 말 것

- **그림자로 깊이를 만들지 않는다.** hairline과 그레이 사다리로 충분하다.
- **두 번째 유채색을 도입하지 않는다.** 링크 파랑 하나로 간다. 의미색(error/warning)은 예외이며 액센트가 아니다.
- **본문에 배경색 블록을 남발하지 않는다.** 인용은 좌측 보더로, 코드블록만 면을 갖는다.
- **한글 제목에 -0.03em을 넘는 음수 자간을 주지 않는다.**
- **미디어쿼리나 `[data-theme]` 블록 안에서 색을 처음 정의하지 않는다.** 토큰 재정의만 한다.
- **모서리를 12px 넘게 굴리지 않는다.**
- **아이콘 폰트를 도입하지 않는다.** 인라인 SVG를 쓴다.
- **애니메이션을 장식으로 쓰지 않는다.** 상태 변화(호버·포커스·토글)에만, 150ms 이내로. `prefers-reduced-motion`을 존중한다.

---

## 8. 알려진 빈틈

- **다크 팔레트는 파생값이다.** 원본 Vercel 분석은 단일 모드다. 실제 화면에서 대비를 검증한 뒤 조정한다.
- **기본 이미지 도안은 들어왔다** — `src/assets/placeholders/` 15장(상위 14 + 기본값 1), `scripts/gen-placeholders.py`가 정본이다. 마스크 방식이라 라이트/다크가 한 파일로 갈린다. **다만 `src/styles/`가 없어 빌드 산출물로는 아직 확인하지 못했다** — `placeholderVars()`는 CSS 빌드 안에서만 돈다. 스킨 첫 사이클에서 `style.css`에 `--ph-*`가 실제로 박히는지, 린트 `BND003`이 실제로 도는지 확인한다.
- **`preview.gif` / `preview256.jpg` / `preview560.jpg` / `preview1600.jpg`** 스킨 미리보기 이미지가 필요하다.
- **인라인 색 열거 목록은 2026-08-24 기준 275편 전수 조사 결과다.** 새 글이 쌓이면 다시 세야 하며, 그때까지는 JS 안전망이 막는다.
- **인라인 보정 CSS의 스코프는 여섯 상태를 모두 덮어야 한다.** `scripts/build.mjs`가 다크·라이트 각각을 **명시 스코프 + 시스템 스코프** 두 벌로 낸다(§8.1 참조). 새 색이 실측에 추가되면 자동으로 따라가지만, **스코프 구조를 손대면 여섯 상태를 다시 재야 한다** — 명시 다크/라이트 × OS 다크/라이트 4가지 + stamp 없음 × OS 2가지.
- **구문 하이라이팅 색 규정이 없다.** §6.3은 "언어 라벨"과 "신뢰도"만 정하고 `.hljs-*` 토큰 색은 정하지 않는다. 그래서 `components.css`는 기존 토큰만으로 2톤(잉크 사다리 + `--link`) 팔레트를 임시로 짜 두었다. 코드블록 728개가 사실상 무채색으로 보인다는 뜻이다. 제대로 하려면 **코드 전용 색 토큰 4~5종**(문자열·숫자·주석·키워드)을 라이트/다크 양쪽에서 대비를 재고 추가해야 한다.
- **`--accent-cyan`·`--warning`은 라이트 캔버스 위 본문 크기 글자로 쓸 수 없다.** `#29bc9b` on `#fafafa` = **2.30:1**, `#f5a623` on `#fafafa` = **1.94:1**로 WCAG AA(4.5:1)에 크게 못 미친다. 다크에서는 각각 12.4:1 · 11.3:1로 충분하다. 현재 CSS는 이 둘을 텍스트 색으로 쓰지 않는다. **조정안**: 라이트 전용으로 한 단 어둡게 파생한 값을 토큰에 넣고 다크에서 현재 값으로 되돌린다.

## 8.1 해결된 빈틈

| 날짜 | 항목 | 무엇을 했나 |
|---|---|---|
| 2026-08-25 | 🔴 인라인 보정 CSS가 **stamp 없음 + 시스템 다크**를 안 덮었다 | `scripts/build.mjs`가 다크를 `[data-theme="dark"]`와 `@media (prefers-color-scheme: dark) { :not([data-theme="light"]) }` 두 벌로 낸다. 라이트도 같은 이유로 대칭이 필요해 `[data-theme="light"]` + `@media (prefers-color-scheme: light) { :not([data-theme="dark"]) }`로 나눴다 — 그전에는 라이트 보정이 시스템 다크에서도 발화해 다크에서 멀쩡히 읽히던 밝은 글자를 끌어내렸다. 선택자 56 → **112개**. 함께 고친 것: 린트 `TOK002`가 `[style*="color: #000000"]` **선택자 줄**을 선언으로 오인하던 오탐, `TOK001` 상시 경고(생성 주석의 hex) |
| 2026-08-25 | `--ink-mute` 라이트 AA 미달 | `#888888` → **`#707070`**. 흰 캔버스만 보고 `#767676`(4.54:1)으로 내렸다가, `--ink-mute`가 **코드블록 안(`--canvas-soft`)에서도 쓰인다**는 것을 놓친 것을 잡았다 — `.hljs-comment` · `.code-lang` · `.code-lines`가 거기서 4.35:1이었다. 캡션이 놓이는 **세 면 전부**를 기준으로 다시 잡았다: `--canvas` 4.95 / `--canvas-soft` 4.74 / `--canvas-soft-2` 4.54. 다크 `#8f8f8f`는 6.49:1로 통과라 그대로 뒀다. **`--ink-mute`를 크롬 라벨에만 쓴다는 §2 사용 규칙은 그대로 유효하다** — 읽어야 하는 텍스트는 계속 `--ink-body`를 쓴다 |
| 2026-08-25 | 목차 없는 글에서 본문이 288px 왼쪽으로 치우쳤다 | 소제목 3개 미만인 글(**실측 32%, 약 88편**)에서 목차 트랙 240px + 간격 48px이 그대로 남았다. `--page-w` 한 곳만 갈아끼워 본문과 광고 자리가 함께 움직이게 했다. **신호는 `body.no-toc`(목차를 못 만들 때만 JS가 붙인다)이고 `.toc.is-ready`가 아니다** — `.is-ready`를 조건으로 쓰면 첫 페인트에서 모든 글이 1단이었다가 목차가 있는 68%가 144px 밀린다(실측). JS가 꺼진 경로는 `@media (scripting: none)`이 받는다 |
| 2026-08-25 | 검색 입력 포커스 표시가 2.06~2.58:1 | `outline:none`을 쓰는 유일한 컨트롤이었다. `.search:focus-within`에 전역과 같은 2px `--link` 링을 준다 (WCAG 2.4.11) |
| 2026-08-25 | 사이드바 카테고리 접기/펼치기 생산자 부재 | 계약과 CSS는 있는데 **JS 담당 모듈이 없어** 트리가 항상 전부 펼쳐졌다. `js/category.js`를 추가했다. **접기 규칙의 스코프를 `.tt_category` → `.side-category`로 옮겼다** — `.tt_category`는 실블로그에서 확인된 적 없는 이름이라, 티스토리가 다른 이름을 내면 JS는 도는데 CSS가 안 먹는다. 기능은 우리 훅에, 치장만 티스토리 이름에 건다 |
| 2026-08-25 | JS 없이 4열 표가 360px에서 페이지를 31px 밀었다 | `.contents_style table`을 `display:block; overflow-x:auto` 기본값으로 두고, JS가 감싼 경우 `.table-scroll > table`이 `display:table`로 되돌린다. 스크롤 컨테이너는 항상 하나다. 대가: JS가 죽은 경로에서 셀이 폭에 맞춰 늘어나지 않는다 |
| 2026-08-25 | 라이트박스 가림막이 `color-mix()`에만 의존 | 미지원 브라우저에서 투명해진다. **정적 값을 앞줄에 두는 방식은 듣지 않는다** — 미지원 브라우저도 `color-mix` 선언 자체는 토큰 열로 받아들여 뒷줄이 이기고, `var()`를 쓰는 순간 계산값 시점에 무효가 되어 `transparent`가 된다(브라우저에서 재현). 정적 `rgba`를 기본값으로 두고 `@supports`로 올린다 |
