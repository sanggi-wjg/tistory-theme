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
    link: "#0064da"
    link-deep: "#0761d1"
    link-bg-soft: "#d3e5ff"
    error: "#d60000"
    warning: "#f5a623"
    accent-cyan: "#29bc9b"
    selection-bg: "#171717"
    selection-fg: "#f2f2f2"
  dark:
    canvas: "#0a0a0a"
    canvas-soft: "#121212"
    canvas-soft-2: "#1a1a1a"
    surface: "#121212"
    hairline: "#2e2e2e"
    hairline-strong: "#454545"
    ink: "#ededed"
    ink-body: "#b0b0b0"
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
  --link:          #0064da;   /* 2026-08-26 #0070f3에서 내림 — §8.1 참조 */
  --link-deep:     #0761d1;
  --link-bg-soft:  #d3e5ff;
  --error:         #d60000;   /* 2026-08-26 #ee0000에서 내림 — §8.1 참조 */
  --warning:       #f5a623;
  --accent-cyan:   #29bc9b;
  --selection-bg:  #171717;
  --selection-fg:  #f2f2f2;

  /* 코드 구문 색 — 2026-08-26 신설 (결정 44). §6.3 참조.
     범용 토큰(--link·--ink·--ink-body)을 빌려 쓰던 것을 끊었다. */
  --code-keyword:  #0064da;   /* 5.48 / 5.25 / 5.02 */
  --code-string:   #0b7038;   /* 6.20 / 5.94 / 5.68 */
  --code-number:   #8a5300;   /* 6.33 / 6.06 / 5.81 */
  --code-fn:       #6f42c1;   /* 6.51 / 6.24 / 5.97 */
  --code-comment:  #707070;   /* 4.95 / 4.74 / 4.54 */
  --code-deleted:  #d60000;   /* 5.44 / 5.21 / 4.99 */

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
--canvas: #0a0a0a        --ink: #ededed        --link: #3291ff
--canvas-soft: #121212   --ink-body: #b0b0b0   --link-deep: #52a8ff
--canvas-soft-2: #1a1a1a --ink-mute: #8f8f8f   --link-bg-soft: #10233f
--surface: #121212       --hairline: #2e2e2e   --error: #ff6166
                         --hairline-strong: #454545  --warning: #f7b955
--selection-bg: #ededed  --selection-fg: #171717     --accent-cyan: #50e3c2

--code-keyword: #3291ff  --code-string: #5ec27a   --code-number: #e0a458
--code-fn: #c4a7f7       --code-comment: #8f8f8f  --code-deleted: #ff6166
```

코드 토큰의 다크 대비 (세 면 #0a0a0a / #121212 / #1a1a1a):
keyword 6.25 / 5.91 / 5.49 · string 8.93 / 8.45 / 7.85 · number 9.07 / 8.58 / 7.97 ·
fn 9.63 / 9.12 / 8.47 · comment 6.12 / 5.79 / 5.38 · deleted 6.74 / 6.38 / 5.93.

**2026-08-26 실화면 검증으로 조정했다** (DECISIONS.md 결정 33).
파생값이던 다크 팔레트를 배포본에서 처음 재 봤다. 대비 수치는 원래도 라이트와
대칭이었지만(본문 8.13 ↔ 8.45) **읽히는 느낌이 달랐다.** 세 가지를 바꿨다.

| 항목 | 전 | 후 | 이유 |
|---|---|---|---|
| 캔버스 사다리 | `#000000` / `#0a0a0a` / `#111111` | `#0a0a0a` / `#121212` / `#1a1a1a` | 순검정 위에서는 밝은 글자가 번져 획이 뭉갠다. 한 단만 올려 near-black 인상은 남겼다 |
| `--ink-body` | `#a1a1a1` | `#b0b0b0` | 같은 대비율이라도 light-on-dark는 더 얇고 흐리게 보인다. 8.13 → 9.13 |
| `--font-smooth` | (없음, 전역 `antialiased`) | 토큰으로 분기 | 아래 참조 |

새 팔레트는 전경 8종 × 배경 3면 전부 AA를 넘는다. 최저값은
`--ink-mute` on `--canvas-soft-2` = **5.38**, `--link` on `--canvas-soft-2` = **5.49**.

**위계는 유지했다.** 제목(`--ink`)과 본문(`--ink-body`)의 명도차는 라이트가 2.12,
다크가 1.85다. 본문을 더 밝히면(#bdbdbd → 1.60) 소제목·`<strong>`이 본문에 묻히기
시작한다 — 그래서 한 단에서 멈췄다.

### 사용 규칙

- **색은 링크와 포인트에만.** 목차 현재 위치, 카테고리 라벨, 태그 호버, 포커스 링.
- **면으로 구분하지 말고 선으로 구분한다.** 카드·사이드바·코드블록은 `--hairline` 1px 테두리로 분리한다. 배경 채우기는 `--canvas-soft`까지만.
- **그림자를 쓰지 않는다.** 깊이는 그레이 사다리와 hairline으로 만든다.
- `--hairline-strong`는 입력 포커스와 강조 구분선에만.
- 다크 캔버스는 `#0a0a0a`다 — **순검정이 아니다.** 카드·코드블록은 `--canvas-soft`로 한 단 올려 층위를 만든다.
  순검정을 버린 이유는 대비가 아니라 번짐이다. 수치로는 `#000000`이 가장 높지만, 밝은 글자가
  순검정 위에서 halation을 일으켜 획 경계가 흐려진다. 되돌리려면 §8.1의 실측을 먼저 볼 것.

### 다크 모드 동작

- 기본값은 **시스템 설정을 따른다**. 사용자가 토글하면 `localStorage`에 기억하고 `:root[data-theme]`로 고정한다.
- 세 가지 상태를 모두 다뤄야 한다: `data-theme="dark"` / `data-theme="light"` / **stamp 없음(시스템 따름)**.
- `body`에 토큰 배경을 명시적으로 지정한다.

### 테마에 따라 달라지는 "색이 아닌 값"

색이 아니어도 테마마다 달라져야 하는 값이 있다. **그것도 토큰으로 만든다** — 컴포넌트
CSS에 `@media`나 `[data-theme]` 분기가 새는 것을 막는 것이 목적이다.

| 토큰 | 라이트 | 다크 | 쓰는 곳 |
|---|---|---|---|
| `--icon-sun-display` | `none` | `block` | 테마 토글 아이콘 — "누르면 갈 곳"을 보여준다 |
| `--icon-moon-display` | `block` | `none` | 위와 짝 |
| `--font-smooth` | `antialiased` | `auto` | `body`의 `-webkit-font-smoothing` |
| `--font-smooth-moz` | `grayscale` | `auto` | `body`의 `-moz-osx-font-smoothing` |

**`--font-smooth`가 왜 테마별인가.** macOS에서 `antialiased`는 서브픽셀 렌더링을 끄고
**획을 얇게** 만든다. 어두운 글자를 밝은 배경에 얹는 라이트에서는 깔끔해 보이지만,
다크에서는 이미 번져 보이는 밝은 글자를 더 가늘게 만들어 "전체적으로 흐리다"는
체감에 크게 기여한다. 다크에서만 브라우저 기본으로 되돌린다.

두 벤더 속성이 값 어휘를 공유하지 않아(`antialiased`/`auto` vs `grayscale`/`auto`)
토큰도 두 개다. 하나로 합치려다 `-moz-osx-font-smoothing: antialiased`처럼
**무효값**을 내면 조용히 무시된다.

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
| `display-xl` | 48px | 1.05 | -0.028em | 700 | 쓰지 않음 (예비). **글 제목 후보로 한 번 검토하고 접었다** — 결정 39 |
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
| **홈** | `.list-title` ("전체 글") | `<s_list>` — 홈에서도 렌더된다 |

**헤더의 블로그 이름은 `h1`이 아니다.** 헤더는 모든 페이지에 있으므로 거기에 `h1`을 두면
글·목록에서 그 페이지의 `h1`과 겹쳐 **마크업에 `h1`이 둘**이 된다. CSS로 감춰도 원시 HTML에는
남고, 크롤러와 `seo-verify-live`의 `V003`은 원시 HTML을 센다 — 감춤 방식으로 만들어 본 결과
홈을 뺀 전 페이지가 `h1` 2개였다.

**홈의 `h1`은 목록 영역이 준다.** `<s_list>`는 홈에서도 렌더되고, 거기서 `[##_list_conform_##]`이
`"전체 글"`로 채워진다(2026-08-25 실측). 그래서 홈도 다른 페이지와 같은 규칙을 따른다 —
`h1`은 그 페이지 자신의 영역이 갖는다.

한동안 "홈은 `h1`이 없는 것이 정상"이라고 적어 두었는데, 그건 홈 목록을 `<s_index_article_rep>`로
그리려다 **그 영역이 통째로 죽어서 생긴 착시**였다(`DECISIONS.md` 결정 29). `V003`의 홈 예외도
같이 지웠다 — 이제 홈의 `h1` 0개는 진짜 결함이다.

- 본문 소제목은 에디터가 만든다. 스킨은 `h2`·`h3`만 상정하고 목차도 그 둘만 모은다.
- 공지 제목은 `h2`다. 공지 영역은 반복이라 `h1`을 쓰면 공지 수만큼 늘어난다.
- **소제목 굵기 600은 `tistory.css`에서 다시 한 번 이겨야 한다.** 티스토리 `content.css`가
  `#tt-body-page h2[data-ke-size] { font-weight: normal }`(1,1,1)로 덮는다.
  `[data-ke-size]`가 붙은 글에서만 지므로 **글마다 굵기가 갈렸다** (결정 36, 린트 `TIS004`).

### 원칙

- **한글에는 음수 자간을 아끼라.** 원본 Vercel은 48px에서 -2.4px(-0.05em)까지 당기지만, 한글은 그만큼 당기면 자소가 붙어 보인다. 이 스케일은 최대 -0.028em으로 완화했다.
  이 줄과 48px 상한 때문에 **글 제목을 Vercel docs의 56px/-0.06em으로 올리자는 제안을 접었다** (결정 39). Vercel과 다른 것은 실수가 아니라 다른 언어를 조판하고 있기 때문이다.
- **본문 행간은 1.75.** 본문 길이 중앙값 2,813자, 최대 30,314자. 긴 글을 오래 읽는 블로그다.
- **본문 폭은 68~72자 내외.** 글 페이지는 1단이지만 무한정 넓히지 않는다.
- 대문자 라벨(eyebrow, 사이드바 제목)에만 양수 자간 `0.1em`을 준다.
- 숫자가 세로로 정렬되는 곳(방문자 수, 날짜 목록)은 `font-variant-numeric: tabular-nums`.

---

## 4. 레이아웃

### 골격 (E안 + 좌측 레일)

| 페이지 | `body_id` | 구성 |
|---|---|---|
| 홈 | `tt-body-index` | **좌측 레일** + (주목 글 1 + 3열 카드 그리드) |
| 목록 (카테고리·검색·태그·보관함) | `tt-body-category` 등 | **좌측 레일** + 목록 |
| 글 | `tt-body-page` | **좌측 레일** + 본문 + 우측 목차 (3단) |
| 방명록·보호글 | 각 id | 1단, 최소 스타일 |

`body_id`로 CSS를 분기한다. 헤더·푸터는 전 페이지 공유.

**사이드바는 왼쪽이다.** 카테고리가 이 블로그의 뼈대인데(상위 14 · 하위 21) 예전에는
목록 4종의 오른쪽에만 있었다. 홈으로 들어온 방문자는 카테고리를 볼 길이 없었고,
페이지를 옮기면 자리가 바뀌었다. 사이드바를 통째로 왼쪽에 세워 **같은 폭에서는
어느 페이지든 카테고리가 같은 x좌표에 온다** (실측 1440px, 2026-08-27: 레일 x=24,
폭 240 — 홈·글 목차 유/무·카테고리·보관함 다섯 장 전부 같다).

⚠ **x가 고정값인 것은 아니다.** 1600px부터는 래퍼(1520)가 뷰포트보다 좁아 가운데
정렬이 살아나 레일 x가 56.5 → 216.5(1920)로 움직인다. 지켜야 하는 것은 절대 좌표가
아니라 **페이지 사이의 일치**다.

그래서 `--page-w`도 레일이 서는 페이지에서는 전부 `--wrap`(1520px)이다. 페이지마다
폭이 다르면 컨테이너가 다른 폭으로 가운데 정렬되어 **레일이 옆으로 뛴다.**
본문은 `--content-w`(800px)로 잠기고 남는 자리는 비워 둔다.

**거터도 같은 이유로 페이지마다 같다.** 레일 x가 같아도 본문 x가 다르면
홈→글에서 글이 옆으로 뛴다. 1400px 이상에서 레일 6종에 같은 유동 거터를 건다
(실측 확인: 1400·1440·1512·1920 네 폭 전부 홈·글·카테고리의 레일 x와 본문 x가 일치).

### 거터 — 본문과 레일·목차 사이

`--gutter-min 24px` ~ `--gutter-max 96px`. 폭이 남으면 거터가 먼저 먹고, 96에서 멈춘다.

Vercel docs는 `max-width` 래퍼가 없다. 레일을 뷰포트 왼쪽, 목차를 오른쪽에 못박고
**남는 폭 전부를 거터가** 먹는다 — 1400/1512/1920에서 39·95·299px이었다(2026-08-26 실측).
우리는 래퍼를 유지하되 그 구간의 감각만 가져오고 96px에서 멈춘다. 그 이상은
바깥 여백으로 보낸다 — 풀블리드로 가면 홈 카드 영역이 1,600px가 되어 3열/4열을
다시 정해야 한다(결정 36).

| 뷰포트 | 거터 | 본문 | 래퍼 |
|---|---|---|---|
| 1400px | 28.5px | 800px | 1385 (뷰포트가 상한) |
| 1440px | 48.5px | 800px | 1425 |
| 1512px | 84.5px | 800px | 1497 |
| 1600px~ | **96px** | 800px | **1520** (`--wrap`이 상한) |

`--gutter-min`이 24px인 것은 취향이 아니라 산수다 — 3단 하한 1400px에서 스크롤바
15px을 빼면 실사용 폭이 1385이고, 거터가 32면 본문이 800을 못 채운다.
24면 거터가 28.5로 접히면서 본문이 정확히 800이 된다. 800이 `index.xml`
`<contentWidth>`와의 계약이므로 이쪽이 양보한다.

구현은 `column-gap`의 **백분율**이다. `100vw`·`@media`는 스크롤바를 포함한 폭이라
그것으로 계산하면 트랙 합이 컨테이너를 넘는다. `column-gap`의 %는 그리드 컨테이너
자기 content-box 기준이라 스크롤바가 이미 빠져 있다 (결정 36).

### 간격

4px 기준. `4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96`

- **카드에는 내부 패딩이 없다** — 썸네일이 모서리까지 차고, 자식 간격은 `.post-link`의 `gap` 12px이다.
  카드 사이 간격은 24px(`--sp-5`).
- 섹션 사이 48px. **페이지 여백은 위 48px · 아래 96px**(`.layout`의 `--sp-7`/`--sp-9`) — 위아래가 다르다.
  아래를 넓게 둔 것은 푸터와 붙지 않게 하려는 것이다.
- 본문 문단 사이 24px, 소제목 위 48px / 아래 16px

### 모서리

`sm 4px` (태그·인라인코드) · `md 6px` (버튼·입력) · `lg 8px` (카드·코드블록) · `xl 12px` (히어로)

### 반응형

단일 반응형 스킨이다. 모바일 전용 스킨은 존재하지 않는다.

| 폭 | 좌측 레일 | 홈 그리드 | 글 |
|---|---|---|---|
| ~640px | 본문 하단으로 | 1열 | 목차 접이식 |
| 641~1024px | 본문 하단으로 | 2열 | 목차 접이식 |
| 1025~1239px | **좌측** | 2열 (카드 325~432px) | 목차 접이식 |
| 1240~1399px | 좌측 | **3열** (카드 280~333px) | 목차 접이식 |
| 1400px~ | 좌측 | 3열 (카드 340~363px) | **우측 목차 (3단)** · 유동 거터 |

두 하한의 근거는 실측이다 (2026-08-27 재측정, 스크롤바 15px 포함).

- **홈 3열 1240px** — 카드가 **280.3px**로 나온다.
  `(1225 - 여백 48 - 레일 240 - 간격 48 - 카드간격 48) / 3 = 280.3`.
  ⚠ **분자는 1240이 아니라 1225다.** `@media`가 보는 폭에는 스크롤바가 들어 있고
  실제 컨테이너는 그만큼 좁다 — 결정 36이 거터에서 잡아낸 것과 같은 함정이다.
  예전에는 여기에 `(1240 - …) / 3 = 285px`라고 적혀 있었다.
  하한 자체는 아직 성립하지만(「280px 아래로 가면 카드 제목이 매번 잘린다」)
  **여유가 5px이 아니라 0.3px이다.** 이 값을 근거로 무엇을 더 얹기 전에 다시 잰다.
  1025~1239px에서는 2열이고 카드가 325~432px로 오히려 넓다.
- **글 3단 1400px** — `240 + 24 + 800 + 24 + 240 + 여백 48 = 1376`. 스크롤바 15px을
  더해도 1391로 1400 안에 들어간다. 레일 폭이 300px이면 1496px이 필요해 1440 모니터가
  3단에서 떨어진다. 그래서 `--sidebar-w`를 240px로 정했다.
  (여기 24는 `--gutter-min`이다. 실제로는 28.5까지 벌어진다 — 위 「거터」 표.)

**1399px에서 1400px로 넘어가는 순간 거터가 48 → 28.5로 한 번 좁아진다.** 목차가
들어오면서 같은 폭에 트랙이 하나 늘기 때문이고, 1440px이면 다시 48로 돌아온다.
창을 줄일 때만 보이는 과도 구간이라 그대로 둔다 — 페이지를 옮길 때 뛰는 것은 아니다.

**위 표에 없는 문턱이 일곱 있다** — 표는 «레이아웃이 바뀌는 폭»(레일·열 수·목차)만 적고, 아래는
컴포넌트 하나씩만 바꾸므로 따로 둔다. 새 문턱을 만들 때는 표와 이 목록 중 어디에 속하는지 정하고,
**같은 폭을 다른 이유로 쓰면 줄을 따로 적는다** — 640과 641이 각각 둘씩이다.

| 폭 | 무엇 | 어디 |
|---|---|---|
| `max-width: 640px` | 헤더 압축 — 브랜드 설명을 접고 검색을 96px로(결정 50) | `components.css` |
| `max-width: 640px` | 제목 한 단 축소 — `.entry-title`·`.list-title`·`.tagcloud-title`이 `display-md`로 | `components.css` |
| `max-width: 767px` | 블로그 메뉴(`.site-nav`)를 헤더 아랫줄로 내린다. **메뉴가 비면 `:empty`가 먼저 지운다**(결정 50) | `components.css` |
| `min-width: 561px` | 목록 4종의 카드를 세로 → **가로**(썸네일 왼쪽)로 | `components.css` |
| `min-width: 641px` | 홈 **주목 글**(첫 카드)을 가로로 — 썸네일이 왼쪽 46% | `components.css` |
| `min-width: 641px` | 이전/다음 글을 1열 → **2열**로 | `components.css` |
| `min-width: 768px` | `--pad-x` 20 → 24px | `tokens.css` |

`layout.css`의 `min-width: 641px`(홈 그리드 2열)은 여기가 아니라 **위 표**의 「641~1024px 2열」이다.

1399px 이하에서 접히는 것은 **목차**다. 카테고리는 모든 데스크톱 폭에서 남는다.

**1024px 이하에서는 카테고리가 헤더로 올라간다.** 레일이 본문 아래로 내려가 사실상 안
보이므로(390px 실측: 홈 5,800px·글 15,300px 아래), 헤더 안 `.cat-chips`가 상위 14종 + 「전체」를
가로 스크롤 한 줄로 낸다. 하위 21종은 칩에 없다 — 카테고리 페이지에 들어가면 그 목록이 하위
역할을 한다. 같은 폭에서 브랜드 설명을 접고(640px 이하) 검색을 96px로 줄여 헤더 본체가
159 → 73px(칩 줄 포함 129px)이 된다(결정 50, 프리뷰 실측).

넓은 콘텐츠(코드블록·표·다이어그램)는 각자 `overflow-x: auto` 컨테이너 안에서 스크롤한다. **페이지 본문이 가로로 스크롤되면 안 된다.**

**인쇄에는 스크롤이 없다** — `@media print`에서 코드블록은 `pre-wrap`으로 풀고(줄번호 거터는 끈다 — 접힌 줄과 번호가 어긋난다) 표는 `display: table` + `table-layout: fixed`로 되돌린다. 크롬(레일·목차·진행바·맨위로·페이징·이전다음·관련글·메뉴·댓글·방명록·복사 버튼·광고·푸터)은 지운다. 팔레트는 **다크 블록을 `@media not print`로 좁혀** 라이트가 그대로 나가게 한다(결정 52).

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

### 5.2b 티스토리 스타일시트가 박아 둔 라이트 전용 색

**5.2와 다른 문제다.** 5.2는 글 본문의 `style` 속성이라 `[style*=…]`로 잡힌다. 여기 색들은
티스토리가 **자기 스타일시트에서** 에디터 컴포넌트에 칠하는 것이라, 속성 선택자로는
원리적으로 닿지 않고 인라인 보정도 JS 안전망도 건드리지 못한다.

```
static/style/content.css        오픈그래프·인용·첨부·장소·검색카드·표 스타일
페이지 안 <style>                .another_category ("카테고리의 다른 글") — 전부 !important
cdnjs .../atom-one-light.min.css  코드 구문 색 — 우리 style.css **뒤**에 온다
```

**핵심은 순서가 아니라 특이도다.** content.css는 우리보다 앞에 오지만 상당수 규칙이
`#tt-body-page`로 시작한다 — ID 하나가 클래스 전부를 이긴다.

```css
#tt-body-page blockquote[data-ke-style='style1'] { color:#333 }        /* (1,1,1) 티스토리 */
.contents_style blockquote { color: var(--ink-body) }                  /* (0,1,1) 우리 — 진다 */
#tt-body-page .contents_style blockquote[data-ke-style="style1"] { … } /* (1,3,1) 우리 — 이긴다 */
```

**대응 원칙 세 가지** (`src/styles/tistory.css`):

1. **테마 분기를 하지 않는다.** 리터럴을 토큰으로 바꾸기만 하면 다크는 토큰이 따라온다.
   §8.1에서 두 번 데인 "여섯 상태" 실수를 아예 만들지 않는다. 덤으로 라이트도 고쳐진다 —
   `style12` 표 머리는 **라이트에서도** 2.78:1이었다.
2. **상대 선택자를 그대로 베끼고 앞에만 붙인다.** `.contents_style`로 (0,1,0)을 더하고,
   상대가 ID로 시작하면 `#tt-body-page`까지 붙인다. 같으면 순서 싸움이 되고 순서는 티스토리가 정한다.
3. **선택자를 줄이지 않는다.** `figure.fileblock .filename`을 `.filename`으로 줄이면 진다.

**코드 구문 색은 반대 경우다.** atom-one-light은 우리보다 **뒤**에 오고 특이도가 같아서(0,1,0)
순서로 이긴다. 그래서 `components.css`의 팔레트는 전부 `.hljs ` 접두를 달아 (0,2,0)으로 올린다.
접두를 떼면 팔레트 전체가 화면에 닿지 않고, 라이트 테마 색이 다크 배경에 얹힌다.

**목록은 `data/tistory-hardcoded-colors.json`이 정본이고, 린트 `TIS001`/`TIS002`/`HLJS001`이 지킨다.**
티스토리가 시트를 바꾸면 목록도 갱신해야 한다 — 자동 감지 수단은 없다.

### 5.3 카테고리 트리

**`[##_category_list_##]`(리스트형)가 통째로 렌더링한다.** `[##_category_##]`(폴더형)가 아니다 — 둘은 완전히 다른 것을 출력하고, 폴더형을 쓰면 아래 클래스가 **하나도 나오지 않는다**(`DECISIONS.md` 결정 31, 린트 `CAT001`). 마크업은 바꿀 수 없다.

```
ul.tt_category > li > a.link_tit          "분류 전체보기" + span.c_cnt
  ul.category_list > li > a.link_item     상위 카테고리 14
    ul.sub_category_list > li > a.link_sub_item   하위 카테고리 21
```

- **현재 보고 있는 가지의 `li`에 `class="selected"`가 붙는다.** 카테고리 페이지에서만이다 — 글 페이지에는 안 붙는다. **`--canvas-soft-2` 알약 배경**(`--radius-md`) + `--link` 글자로 표시한다 (결정 37). 예전에는 왼쪽 2px 막대였고 "240px 레일에서 배경 블록의 면적이 크고 §4의 촘촘한 세로선을 끊는다"가 그 근거였는데, 재보니 알약은 `li`가 아니라 `a`에만 걸려 세로 폭이 막대와 같고, 하위 목록의 세로선(`ul`의 `padding-left` 12px)까지 5px이 남는다(프리뷰 실측). 좌우 여백은 같은 크기의 음수 마진으로 상쇄해 **글자가 움직이지 않는다.**
- 앵커 안에는 앞뒤 공백이 들어 있다 — `<a> 인프라 <span>(42)</span> </a>`.
- 접기/펼치기가 필요하면 JS로 DOM을 조작한다(`js/category.js`). 기본은 접힘이 아니라 **펼침**이고, JS가 토글을 만든 가지만 접힌 상태로 시작한다 — JS가 실패해도 하위 카테고리로 갈 길이 남는다.
- **`index.xml`의 `<tree>` 설정은 리스트형에 닿지 않는다.** 폴더형 전용이다. 지우려면 `index.xml`을 다시 올려야 하고 그러면 스킨 설정이 초기화되므로(결정 1) 그대로 둔다. 색·글수 표시는 전부 CSS가 맡는다.
- **상위 14종 / 하위 21종 → 트리 36줄** (`분류 전체보기` 1 + 14 + 21). 개편 전 48줄(1 + 11 + 36). 전체 목록과 순서는 `DECISIONS.md` §3, 정본은 `data/categories.json`.
- `span.c_cnt`는 `--ink-mute`, `tabular-nums`. 제목이 두 줄이 될 때 배지가 마지막 줄에 붙지 않도록 앵커 정렬은 `baseline`이 아니라 `flex-start`다.
- **1024px 이하에서는 같은 트리를 `cat-chips.js`가 한 번 더 읽어** 헤더 안 칩 한 줄(상위 14종 + 「전체」)을 만든다. 파서는 `category.js`와 **같은 함수**다 — 둘이 다른 목록을 내면 화면에 신호가 없다(결정 50, `docs/hooks.md` §5.9).
- **240px 레일에서 상위·하위 35종이 전부 한 줄에 들어간다** (2026-08-25 프리뷰 계측). 가장 긴 이름 `성능과 동시성`·`Django·Flask`·`Kotlin·Java`도 줄바꿈되지 않는다. 이름이 더 길어지면 `overflow-wrap: break-word`로 흘린다.

### 5.4 댓글·방명록

`[##_comment_group_##]` / `[##_guestbook_group_##]` 한 줄이면 티스토리 React 앱이 UI 전체를 렌더링한다. 우리는 `tt-*` 클래스에 토큰을 입힌다.

주요 훅: `.tt-comment-cont` · `.tt-box-total` · `.tt-area-reply` · `.tt-list-reply` · `.tt-item-reply` · `.tt-box-thumb` · `.tt-thumbnail` · `.tt-link-user` · `.tt_desc` · `.tt_date` · `.tt-cmt` · `.tt-btn_register`

**직접 마크업을 짜지 않는다.** `<s_rp>` 계열 치환자는 구형이라 핀 고정·프로필 레이어·더보기를 잃는다.

---

## 6. 컴포넌트

### 6.1 카드 (홈 그리드 / 목록)

```
.post                     ← <article>. data-cat에 카테고리 전체 경로가 들어간다
  .post-link              ← 카드 전체를 감싼 단 하나의 <a> (중첩 앵커를 피한다)
    .thumb                16:10, radius lg, 1px hairline
      img.thumb-img       대표이미지가 있을 때만 (치환자가 없으면 블록째 사라짐)
    .post-text
      .post-cat           caption, --link
      .post-title         display-sm, 2줄 클램프
      .post-excerpt       발췌
      .post-meta          caption, --ink-mute, tabular-nums
        .post-date · .post-rp
```

**이름은 `docs/hooks.md` §2가 정본이다.** 2026-08-28까지 여기에는 `.cat`·`.title`·`.meta`로 적혀
있었는데 실제 마크업은 `.post-cat`·`.post-title`·`.post-meta`다 — 접두 없는 이름은 이 스킨에
하나도 없다. 카드 자식이 전부 인라인 요소(span·strong·time)인 것도 `.post-link` 하나로 감쌌기
때문이다(hooks.md §2).

- **제목은 반드시 2줄에서 자른다.** 홈에 노출되는 최신 20편의 제목 중앙값이 49자, 40자 초과가 75%다.
- 카드 높이를 고정해 그리드 정렬을 유지한다.
- **`.thumb`의 CSS는 §6.2가 통째로 갖는다.** 여기서 따로 쓰지 않는다 — 상자 속성(`display` `position` `overflow`)이 §6.2의 기본 이미지 3층 구조를 떠받치고 있어서, 두 곳에서 정의하면 갈라진다.

### 6.2 대표이미지 기본값

대표이미지 보유율은 전체 45%, 홈 노출분 85%다. 없는 글은 **상위 카테고리별 기본 이미지**로 메운다.

```html
<article class="post" data-cat="[##_list_rep_category_##]">
  <span class="thumb">
    <s_list_rep_thumbnail>
      <img class="thumb-img" src="[##_list_rep_thumbnail_##]" alt="" loading="lazy" decoding="async">
    </s_list_rep_thumbnail>
  </span>
</article>
```

**3층으로 쌓는다.** 격자는 CSS, 기본 이미지는 배경, 진짜 이미지는 그 위.

```css
/* 0층 — 상자. 위의 세 줄은 장식이 아니라 기계장치다. 지우면 조용히 무너진다.
   · display   — `<span class="thumb">`는 기본이 inline이라 크기를 못 갖는다
   · position  — 없으면 2층 ::before가 .thumb가 아니라 페이지 전체에 붙는다
                 (실측: 높이 1028px짜리 모티프가 화면을 덮었다)
   · overflow  — 기본 이미지와 img를 radius로 잘라낸다 */
.post .thumb {
  display: block;
  position: relative;
  overflow: hidden;
  aspect-ratio: 16 / 10;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-lg);

  /* 1층 — 점격자. 순수 CSS라 용량이 0이고 토큰을 그냥 따른다. 이미지가 뜨기 전·못 뜰 때 보이는 자리다 */
  background-color: var(--canvas-soft);
  background-image: radial-gradient(circle, var(--hairline) 1.1px, transparent 1.2px);
  background-size: 8px 8px;
  background-position: -1px -1px;
}

/* 2층 — 기본 이미지, 다중 배경 두 겹. 위 겹은 WebP(--ph-*, 라이트 정의 + 다크 재정의),
   아래 겹은 같은 slug의 모티프 SVG를 data:로 인라인한 폴백(--ph-*-svg). WebP가 404면 아래가 드러난다 */
.post .thumb::before {
  content: ""; position: absolute; inset: 0;
  background:
    var(--ph-default)     center / cover no-repeat,
    var(--ph-default-svg) center / cover no-repeat;
}

/* 상위 14종. 순서는 사이드바 노출 순 (DECISIONS.md §3). 두 겹을 항상 같이 쓴다 */
.post[data-cat="인프라"] .thumb::before,
.post[data-cat^="인프라/"] .thumb::before        { background-image: var(--ph-infra), var(--ph-infra-svg); }
.post[data-cat="Kotlin·Java"] .thumb::before    { background-image: var(--ph-jvm), var(--ph-jvm-svg); }
.post[data-cat="Python"] .thumb::before,
.post[data-cat^="Python/"] .thumb::before       { background-image: var(--ph-python), var(--ph-python-svg); }
.post[data-cat="PHP"] .thumb::before,
.post[data-cat^="PHP/"] .thumb::before          { background-image: var(--ph-php), var(--ph-php-svg); }
.post[data-cat="아키텍처"] .thumb::before,
.post[data-cat^="아키텍처/"] .thumb::before       { background-image: var(--ph-arch), var(--ph-arch-svg); }
.post[data-cat="데이터베이스"] .thumb::before,
.post[data-cat^="데이터베이스/"] .thumb::before    { background-image: var(--ph-db), var(--ph-db-svg); }
.post[data-cat="네트워크"] .thumb::before         { background-image: var(--ph-net), var(--ph-net-svg); }
.post[data-cat="보안"] .thumb::before            { background-image: var(--ph-sec), var(--ph-sec-svg); }
.post[data-cat="AI"] .thumb::before             { background-image: var(--ph-ai), var(--ph-ai-svg); }
.post[data-cat="코드 품질"] .thumb::before,
.post[data-cat^="코드 품질/"] .thumb::before      { background-image: var(--ph-quality), var(--ph-quality-svg); }
.post[data-cat="Go"] .thumb::before             { background-image: var(--ph-go), var(--ph-go-svg); }
.post[data-cat="알고리즘"] .thumb::before         { background-image: var(--ph-algo), var(--ph-algo-svg); }
.post[data-cat="개발 도구"] .thumb::before,
.post[data-cat^="개발 도구/"] .thumb::before      { background-image: var(--ph-tool), var(--ph-tool-svg); }
.post[data-cat="기록"] .thumb::before            { background-image: var(--ph-note), var(--ph-note-svg); }

/* 3층 — 진짜 대표이미지가 있으면 앞의 둘을 덮는다. z-index가 있어야 ::before 위로 온다 */
.thumb-img { position: relative; z-index: 1; width: 100%; height: 100%; object-fit: cover; }

/* 카테고리 목록에서는 같은 그림이 최대 15번 반복되므로 감춘다 (결정 7) */
#tt-body-category .post:not(:has(.thumb-img)) .thumb { display: none; }
```

- **이미지는 WebP 래스터 30장이다** — `src/assets/placeholders/<slug>-{light,dark}.webp`, **800×500(16:10)**, 장당 **100KB 이하**. 원본은 `src/assets/placeholders-src/<slug>-<theme>.{png,jpg,webp,svg}`에 두고 `npm run placeholders`(`scripts/prep-placeholders.mjs`)가 크롭·변환한다. 배포 때 스킨 편집기 파일업로드 탭으로 `images/`에 올린다. 2026-08-27까지는 SVG 마스크 15장을 `data:` URI로 `style.css`에 인라인했다 — 결정 5·6 개정.
- **라이트/다크 두 벌이다.** 래스터는 마스크와 달리 색을 토큰에서 받지 못한다. 빌드가 `--ph-<slug>`를 `:root`에서 라이트로 정의하고 `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) }`·`:root[data-theme="dark"]`에서 다크로 재정의한다 — `tokens.css`의 3블록과 같은 패턴이라 §7 "미디어쿼리 안에서 색을 처음 정의하지 않는다"와 맞는다. **한 쌍이라도 빠지면 빌드가 멈춘다**(경고가 아니라 오류). 빠진 쪽 테마에서 점격자만 남는데 에러가 없기 때문이다.
- **WebP가 안 오면 옛 모티프가 드러난다 — 다중 배경 폴백.** 빌드가 `src/assets/motifs/<slug>.svg`를 중간 회색(`#8a8a8a`, 62%)으로 구워 `--ph-<slug>-svg`에 `data:`로 인라인하고(15장 약 8KB, 테마 공통 — 아래 점격자가 토큰을 따르니 테마감은 거기서 난다), 2층은 `var(--ph-x), var(--ph-x-svg)` 두 겹이다. 브라우저는 404·네트워크 실패한 겹만 `none`으로 취급하므로 아래 겹이 보이고, WebP가 오기 전에도 먼저 그려진다. **그래서 `motifs/`와 `scripts/gen-placeholders.py`는 영구 자산이다** — 새 slug를 더하면 모티프도 같이 그린다(없으면 빌드 오류).
- **두 변수 중 하나라도 없으면 둘 다 사라진다.** `background-image: var(--ph-x), var(--ph-x-svg)`는 한 변수만 비어도 선언 전체가 무효가 되어 1층 점격자만 남는다. 빌드가 slug마다 WebP 한 쌍 + 모티프를 요구하고, 린트 `TOK006`이 정의 없는 `var()`를 잡는다. 마스크 시절의 "단색 판이 카드를 덮는" 실패와 `--ph-fallback`은 사라졌다.
- **폴백은 방문자를 위한 안전망이지 검사를 대신하지 않는다.** 업로드를 빠뜨려도 화면은 옛 도안으로 멀쩡해 보인다 — AI 사진 자리에 선 그림이 뜨니 사람 눈엔 다르지만, 그걸 발견 수단으로 삼지 않는다. 린트 `TOK007`이 배포 전에 `dist/style.css`의 `url(…images/…)` 마다 `dist/images/` 실재를 보고, 배포 후에는 `curl -I`로 30장이 200인지 본다(`skin-deploy`).
- **파일명에 버전이 박힌다** — `dist/images/ph-<slug>-<theme>.v<N>.webp`, N은 `package.json`의 `placeholderVersion`. 티스토리 CDN이 같은 이름을 오래 캐시하므로 **이미지를 바꾸면 N을 올리고 30장을 다시 올린다.** 이미지가 안 바뀐 배포에서는 올리지 않는다.
- **접두사 충돌이 없다** — 상위 14종 중 어느 이름도 다른 이름의 접두사가 아니다. `^=`가 옆 카테고리를 물지 않는다.
- **하위가 없는 7종**(`Kotlin·Java` `네트워크` `보안` `AI` `Go` `알고리즘` `기록`)은 `^=` 줄을 두지 않았다. 하위가 생기면 두 줄짜리로 바꾼다 — 안 바꾸면 새 하위 글이 `--ph-default`로 조용히 떨어진다.
- 이름에 `&`가 없어 이스케이프 걱정은 사라졌지만 **`코드 품질`·`개발 도구`에는 공백이 있으므로** 값은 계속 따옴표로 감싼다.
- **`--ph-*` 변수명은 파일의 slug에서 그대로 나온다** (`arch-light.webp` → `--ph-arch`). 빌드가 이름을 검사하지 않으므로 **slug를 틀리면 변수가 정의되지 않고 카드는 조용히 `--ph-default`로 떨어진다.** 위 블록의 이름이 곧 slug 목록이다.
- **카테고리를 늘리거나 이름을 바꾸면 이 블록과 이미지 두 장을 같이 고친다.** 린트 `BND003`이 `data/categories.json`과 대조해 빠진 상위를 잡는다.
- **`og:image`는 안 바뀐다.** CSS 배경이라 검색·SNS 공유 썸네일은 여전히 티스토리 기본이다(`DECISIONS.md` §3 실측). 이 그림은 **사이트 안에서만** 보인다.
- **삽화 방향은 확정됐다 — 결 3 · 개념 일러스트, Clockwise 결을 스킨 토큰으로**(2026-08-27 사용자 승인). 규칙과 GPT-image 프롬프트 팩은 [`docs/placeholder-image-brief.md`](./docs/placeholder-image-brief.md)에 있다: 굵은 외곽선 한 굵기, 면 3톤, 뒤판 원 하나, `--link` 파랑 한 요소, 작은 장식 셋, 정면, 사람·글자 없음. 지금 `placeholders-src/`의 SVG 30장은 그 방향의 **승인된 목업**이고 곧 실제 기본 이미지다. AI로 더 풍부하게 만든 그림은 같은 이름의 `.png`로 덮어쓴다(래스터가 SVG를 이긴다). `motifs/`는 폴백이므로 남는다.
- **카테고리 목록 상단에는 `<s_list_image>` / `[##_list_image_##]`로 카테고리 대표이미지를 배너 1장으로 깐다.** 다만 이 치환자는 관리 화면에서 카테고리 대표이미지를 설정해야 값이 나오고, 없으면 블록째 사라진다 — **기본 이미지를 배너로 대신 쓸지는 미정**이다(`DECISIONS.md` 미결 12).

### 6.3 코드블록

```css
.contents_style pre {
  font-family: var(--font-mono);
  font-size: var(--fs-mono);      /* 13px */
  line-height: var(--lh-mono);    /* 1.7 */
  background: var(--canvas-soft);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-lg);
  padding: var(--sp-4);           /* 16px */
  overflow-x: auto;          /* 줄바꿈하지 않는다 — 최대 1,777자짜리 줄이 있다 */
}
```

- **언어 라벨은 우상단에 표시**한다. 어느 값을 쓰는지는 **누가 썼는가**로 갈린다 (결정 43):
  - **글쓴이가 마크다운 펜스로 쓴 `<code class="language-X">` → 신뢰한다.** 임계·한글 가드를 건너뛰고 그 언어로 칠한다.
  - **에디터가 붙인 것은 무엇이든 무시한다** — `data-ke-language`(285개/39%, `javascript` 44개가 전부 오답)와 `<pre>`의 클래스(실측 41블록의 최빈값이 `reasonml` 6개) 둘 다.
  - 글쓴이 라벨이 없으면 **자동 감지**로 간다.
- **감지 신뢰도가 낮으면 하이라이팅하지 않고 라벨도 숨긴다.** 한국어 메모 블록이 엉뚱하게 물드는 것을 막는다.
- **글쓴이가 쓴 이름이 번들에 없으면 라벨만 달고 칠하지 않는다.** `typescript`라고 쓴 것을 우리가 `java`로 칠하는 쪽이 더 나쁘다. **언어인지 모르는 이름(`info` 등)은 라벨도 달지 않는다** — 펜스에는 언어가 아닌 표식과 오타가 섞여 들어오고, 거기에 "Info" 라벨을 달면 틀린 정보를 화면에 새로 만드는 것이다.
- **구문 색은 코드 전용 토큰만 쓴다** (결정 44). `--link`·`--ink`·`--error`를 여기서 다시 쓰지 않는다 — 그 연결을 끊는 것이 이 토큰의 존재 이유다.

  | 역할 | 토큰 | `.hljs-*` |
  |---|---|---|
  | 키워드·타입·내장·리터럴 | `--code-keyword` | `keyword` `selector-tag` `literal` `type` `built_in` `meta-keyword` |
  | 문자열·정규식 | `--code-string` | `string` `regexp` `addition` |
  | 숫자·기호 | `--code-number` | `number` `symbol` `bullet` |
  | 함수·클래스 이름 (600) | `--code-fn` | `title` `section` `name` `selector-id` `selector-class` |
  | 주석 (italic) | `--code-comment` | `comment` `quote` |
  | 삭제 줄 | `--code-deleted` | `deletion` |

  **속성·변수(`attr` `attribute` `variable`)는 `--ink-body`, 메타·태그는 `--ink-mute`로 무채색을 유지한다.** 한 줄에 유채색이 넷을 넘으면 강조가 강조를 잡아먹는다 — 여기까지가 이 팔레트의 상한이다.
- highlight.js 언어 번들은 필요한 것만: `python bash shell sql java kotlin go json yaml xml`
- **하이라이트는 첫 페인트 뒤 유휴 시간에 청크로 돈다**(결정 51). **20,000자 넘는 블록**은 **자동 감지**를 건너뛰고 복사 버튼·줄번호 규칙만 붙는다 — 로그 덤프에 10개 문법을 돌리지 않는다. 글쓴이가 언어를 쓴 블록은 문법 하나라 상한과 무관하게 칠한다.
- 복사 버튼은 우상단, 호버 시 노출. 줄 번호는 일정 줄 수 이상에서만.

### 6.4 목차 (TOC)

본문 `h2`/`h3`를 JS로 스캔해 생성한다. 소제목 3개 이상인 글이 68%, 최대 25개다.

- 현재 위치는 `--link` + 좌측 2px 바
- `position: sticky`(1400px~ 우측 칸), 1399px 이하에서는 본문 상단 접이식으로 전환 — §4 표의 3단 경계와 같다(결정 48)
- 소제목이 3개 미만이면 목차를 렌더링하지 않는다

### 6.4b 소제목 앵커

목차는 소제목이 3개 이상일 때만 생긴다. **32%의 글에는 소제목을 가리킬 수단이 없었다.**
그래서 앵커는 목차와 무관하게 붙인다 — 소제목이 하나여도 붙는다 (결정 38).

- 소제목 끝에 `#`. `--ink-mute`, 굵기 400, **소제목 호버 시에만** 나타난다
- 호버가 없는 입력장치(`@media (hover: none)`)에서는 항상 보인다 — 터치에서 나타날 계기가 없다
- **`#`은 CSS `::before`가 그린다.** 소제목의 `textContent`가 목차 라벨이자 검색결과 제목이라
  텍스트 노드로 넣으면 둘 다 오염된다. 복사·선택에도 딸려오지 않는다
- id는 목차와 **같은 함수**(`util.headingsWithIds()`)가 만든다. 따로 세면 번호가 어긋나는데
  눌러 보기 전에는 신호가 없다
- 나타나는 조건은 `:focus-visible`가 아니라 **`:focus`**다. 기본이 `opacity: 0`이라
  포커스에서 안 보이면 포커스 링까지 사라진다

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

- ~~**다크 코드 팔레트는 여전히 임시다.**~~ **해결 (2026-08-26)** — 코드 전용 토큰 6종을 신설했다(결정 44 · §8.1). 다만 `.hljs ` 접두가 없으면 그 임시 팔레트조차 화면에 닿지 않는다는 것은 2026-08-26에 잡았다(§8.1).
- **티스토리 하드코딩 색 목록은 수동 갱신이다.** `data/tistory-hardcoded-colors.json`은 2026-08-26 기준으로 받아 적은 것이고, 티스토리가 `content.css`를 바꾸거나 새 에디터 컴포넌트를 내면 **자동으로 알 방법이 없다.** 린트는 목록 대비 우리 CSS만 검사한다 — 목록 자체가 낡으면 조용히 통과한다. 새 컴포넌트를 쓴 글을 쓰거나 다크에서 이상한 것이 보이면 시트를 다시 받아 대조할 것.
- ~~**기본 이미지 30장은 임시본이다**~~ **해결 (2026-08-27)** — 결 3 개념 일러스트로 확정한 삽화 30장(`src/assets/placeholders-src/*.svg` → WebP)이 §6.2의 구조로 배포됐고 라이브에서 확인했다. AI 생성은 선택 사항으로 `docs/placeholder-image-brief.md`에 절차만 남겼다. 린트는 `BND003`(카테고리 커버리지)·`TOK007`(파일 실재)이 `npm run check`에서 돈다.
- ~~**`preview.gif` / `preview256.jpg` / `preview560.jpg` / `preview1600.jpg`** 스킨 미리보기 이미지가 필요하다.~~ **끝났다** — `src/preview/`, `scripts/gen-preview.mjs`가 만든다.
- **인라인 색 열거 목록은 2026-08-24 기준 275편 전수 조사 결과다.** 새 글이 쌓이면 다시 세야 하며, 그때까지는 JS 안전망이 막는다.
- **인라인 보정 CSS의 스코프는 여섯 상태를 모두 덮어야 한다.** `scripts/build.mjs`가 다크·라이트 각각을 **명시 스코프 + 시스템 스코프** 두 벌로 낸다(§8.1 참조). 새 색이 실측에 추가되면 자동으로 따라가지만, **스코프 구조를 손대면 여섯 상태를 다시 재야 한다** — 명시 다크/라이트 × OS 다크/라이트 4가지 + stamp 없음 × OS 2가지.
- **`--accent-cyan`·`--warning`은 라이트 캔버스 위 본문 크기 글자로 쓸 수 없다.** `#29bc9b` on `#fafafa` = **2.30:1**, `#f5a623` on `#fafafa` = **1.94:1**로 WCAG AA(4.5:1)에 크게 못 미친다. 다크에서는 각각 12.4:1 · 11.3:1로 충분하다. 현재 CSS는 이 둘을 텍스트 색으로 쓰지 않는다. **2026-08-27 기준 어디에도 쓰지 않는다** — 예정 소비자였던 콜아웃이 취소되면서(TODO 닫힌 항목) 남은 사용처가 0이 됐고, 린트 `TOK006`의 「참조 없는 토큰」 목록에 뜬다. 팔레트에는 남겨 두되 **실제 사용처가 생기기 전에는 조정하지 않는다.** 그때의 조정안은 라이트 전용으로 한 단 어둡게 파생한 값을 넣고 다크에서 현재 값으로 되돌리는 것이다.

## 8.1 해결된 빈틈

| 날짜 | 항목 | 무엇을 했나 |
|---|---|---|
| 2026-08-28 | 인쇄 스타일이 **한 줄도 없었다** · 강제 색상 모드에서 진행바가 사라진다 · 복사 버튼이 24×24 하한에 1px 모자람 | **다크 토큰 블록과 인라인 보정을 `@media not print`로 좁혀** 종이가 라이트 정의를 그대로 쓰게 했다 — 인쇄 블록에서 토큰을 다시 나열한 첫 판은 20종 중 10종만 덮어 흰 종이에 다크 코드색·강조색이 남았다. 크롬 13종 제거(레일은 상대가 ID 스코프라 **켜는 쪽**을 좁혔다 — `!important`는 인라인 보정 전용), `pre-wrap` + 거터 끄기, 표는 `table-layout: fixed`, `break-after: avoid`(Gecko는 `avoid-page`를 버린다). `.reading-progress-bar`에 `forced-color-adjust: none` + `Highlight`. `.code-copy` 27px. `.heading-anchor`는 인라인 예외라 그대로. 결정 52 |
| 2026-08-27 | 1025~1399px에서 목차가 본문 위에 펼쳐진 채 고정 · 터치에서 복사 버튼 부재 · 라이트박스 키보드 진입 불가 · `no-toc`가 `script.js` 도착에 의존 | 목차 접이식 경계를 레일 경계(1025)에서 3단 경계(1400)로 옮겼다 — §4 표와 §6.4가 이제 같은 말을 한다. 복사 버튼·검색 입력은 `@media (hover: none)`, 라이트박스는 `tabindex`+Enter, `no-toc`는 `skin.html` 인라인이 첫 페인트 전에 판정. `.side-rp` 가드는 선택자 목록을 둘로 쪼갰다. 결정 48 |
| 2026-08-26 | 구문 하이라이팅 **색 규정이 없었다** (§8 미결) | §6.3이 라벨과 신뢰도만 정하고 `.hljs-*` 색을 정하지 않아, `components.css`가 범용 토큰만으로 2톤 팔레트를 임시로 짜 두고 있었다. **라이브 실측이 그 대가를 보여줬다** — 문자열·숫자가 `--ink-body`라 **기본 코드색보다 흐렸고**(라이트 `#4d4d4d` < `#171717`, 다크 `#b0b0b0` < `#ededed`) 함수명은 `--ink`라 **기본색과 완전히 같아 구분이 0**이었다. 실제로 쓰이는 색이 셋뿐이었고 유채색은 `--link` 하나였다. 코드 전용 토큰 **6종**(`keyword`·`string`·`number`·`fn`·`comment`·`deleted`)을 신설하고 **여섯 면 전부**(라이트/다크 × 세 면)에서 대비를 쟀다. 최저 4.54. 덤으로 `--link`·`--error`가 코드블록 위에서 벗어나 §8.1의 2026-08-26 항목이 걱정하던 연결이 끊겼다. 결정 44 |
| 2026-08-26 | 🔴 티스토리 스타일시트의 라이트 전용 색이 다크에서 **1.00~3.66:1**로 사라졌다 | 원인은 우리 CSS가 아니라 **특이도**다. `content.css`의 상당수 규칙이 `#tt-body-page`로 시작해 `.contents_style …`(0,1,1)을 이겼다. 인라인 보정도 JS 안전망도 원리적으로 못 잡는다 — 색이 `style` 속성이 아니라 **시트**에 있기 때문이다. 실측 피해: 오픈그래프 카드 제목 **1.00:1**(62곳/39편), 인용 `style1` 1.66(7곳), 인용 `style3`·`box`는 다크에 **흰 카드**(24곳), `blockquote p` 3.66(전체 57곳), `style12` 표 1.90~2.27(9곳). `tistory.css`에 §5.2b 원칙대로 토큰 덮어쓰기를 넣고 린트 `TIS001`(누락)·`TIS002`(ID 짝 누락)를 추가했다 |
| 2026-08-26 | 🔴 구문 색 팔레트가 **통째로 무효**였다 | 티스토리가 코드블록 있는 글에 `atom-one-light`을 CDN에서 주입하는데, 그 `<link>`가 우리 `style.css` **뒤**에 온다. 양쪽 다 `.hljs-keyword`(0,1,0)라 특이도가 같고, 같으면 뒤가 이긴다. 라이트 테마 색이 다크 배경에 얹혀 keyword 3.06 · number 3.85 · literal 4.48로 AA 미달이었다. 팔레트 전체에 `.hljs ` 접두를 달아 (0,2,0)으로 올리고 린트 `HLJS001`을 추가했다. `.contents_style`이 아니라 `.hljs`로 잡은 이유는 `code.js`가 직접 그 클래스를 붙이기 때문이다 — 누가 칠했든 항상 참인 구조다 |
| 2026-08-26 | 다크 팔레트 파생값 검증 | 배포본에서 처음 실측했다. 수치는 라이트와 대칭이었지만 체감이 달라 세 가지를 조정했다 — 캔버스 사다리 한 단 위(`#0a0a0a`/`#121212`/`#1a1a1a`), `--ink-body` `#a1a1a1` → `#b0b0b0`, `--font-smooth` 토큰 신설(다크에서 `antialiased` 해제). 전경 8종 × 배경 3면 전부 AA 통과, 최저 5.38. §2 참조 |
| 2026-08-26 | `--link`·`--error` 라이트 AA 미달 — **`--ink-mute`와 똑같은 함정** | 본 블로그 첫 배포 직후 프로덕션에서 쟀다. `--link` `#0070f3`은 흰 캔버스 **4.55:1로 겨우 통과**해 통과로 기록돼 있었지만, 코드블록 배경(`--canvas-soft`)에서 **4.36**, `--canvas-soft-2`에서 **4.18**이었다. `.hljs-keyword`·`.hljs-literal`·`.hljs-built_in`·`.hljs-type` 4종이 여기 걸렸다. `--error`도 같다 — 유일한 사용처 `.hljs-deletion`이 **항상** 코드블록 위에 놓이는데 4.34였다. 세 면 전부를 기준으로 다시 잡았다: `--link` **`#0064da`**(5.48 / 5.25 / 5.02), `--error` **`#d60000`**(5.44 / 5.21 / 4.99). 다크는 `#3291ff` 6.25/5.91/5.49, `#ff6166` 6.74/6.38/5.93으로 통과라 그대로 뒀다. **2026-08-25 `--ink-mute` 항목과 같은 실패다** — 토큰을 흰 캔버스만 보고 정하고, 그 토큰이 tinted 면에서도 쓰인다는 것을 놓쳤다. 세 번째를 막으려면 §8 미결의 코드 전용 토큰이 필요하다 |
| 2026-08-26 | 프리뷰가 티스토리 시트를 안 불러 **세 번째 위조 통과** 직전이었다 | 렌더러가 우리 CSS만 그려서, 위 두 결함이 프리뷰에서는 멀쩡해 보였다. 이제 `content.css`(우리 앞)와 `atom-one-light`(우리 뒤)을 **실제 순서대로** 끼우고, 못 불러오면 화면 하단에 경고 띠를 띄운다. 본문 픽스처에도 오픈그래프·인용 3종·첨부·`style12` 표·`another_category`를 넣었다. 픽스처 조립을 `replace("</div>", …, 1)`에서 "열기+알맹이+닫기"로 바꿨다 — 알맹이에 `<div>`가 생기는 순간 첫 `</div>`가 안쪽 것이 되어 조용히 엉뚱한 자리에 붙는다 |
| 2026-08-25 | 🔴 인라인 보정 CSS가 **stamp 없음 + 시스템 다크**를 안 덮었다 | `scripts/build.mjs`가 다크를 `[data-theme="dark"]`와 `@media (prefers-color-scheme: dark) { :not([data-theme="light"]) }` 두 벌로 낸다. 라이트도 같은 이유로 대칭이 필요해 `[data-theme="light"]` + `@media (prefers-color-scheme: light) { :not([data-theme="dark"]) }`로 나눴다 — 그전에는 라이트 보정이 시스템 다크에서도 발화해 다크에서 멀쩡히 읽히던 밝은 글자를 끌어내렸다. 선택자 56 → **112개**. 함께 고친 것: 린트 `TOK002`가 `[style*="color: #000000"]` **선택자 줄**을 선언으로 오인하던 오탐, `TOK001` 상시 경고(생성 주석의 hex) |
| 2026-08-25 | `--ink-mute` 라이트 AA 미달 | `#888888` → **`#707070`**. 흰 캔버스만 보고 `#767676`(4.54:1)으로 내렸다가, `--ink-mute`가 **코드블록 안(`--canvas-soft`)에서도 쓰인다**는 것을 놓친 것을 잡았다 — `.hljs-comment` · `.code-lang` · `.code-lines`가 거기서 4.35:1이었다. 캡션이 놓이는 **세 면 전부**를 기준으로 다시 잡았다: `--canvas` 4.95 / `--canvas-soft` 4.74 / `--canvas-soft-2` 4.54. 다크 `#8f8f8f`는 6.49:1로 통과라 그대로 뒀다. **`--ink-mute`를 크롬 라벨에만 쓴다는 §2 사용 규칙은 그대로 유효하다** — 읽어야 하는 텍스트는 계속 `--ink-body`를 쓴다 |
| 2026-08-25 | 목차 없는 글에서 본문이 288px 왼쪽으로 치우쳤다 | 소제목 3개 미만인 글(**실측 32%, 약 88편**)에서 목차 트랙 240px + 간격 48px이 그대로 남았다. `--page-w` 한 곳만 갈아끼워 본문과 광고 자리가 함께 움직이게 했다. **신호는 `body.no-toc`(목차를 못 만들 때만 JS가 붙인다)이고 `.toc.is-ready`가 아니다** — `.is-ready`를 조건으로 쓰면 첫 페인트에서 모든 글이 1단이었다가 목차가 있는 68%가 144px 밀린다(실측). JS가 꺼진 경로는 `@media (scripting: none)`이 받는다 |
| 2026-08-25 | 검색 입력 포커스 표시가 2.06~2.58:1 | `outline:none`을 쓰는 유일한 컨트롤이었다. `.search:focus-within`에 전역과 같은 2px `--link` 링을 준다 (WCAG 2.4.11) |
| 2026-08-25 | 사이드바 카테고리 접기/펼치기 생산자 부재 | 계약과 CSS는 있는데 **JS 담당 모듈이 없어** 트리가 항상 전부 펼쳐졌다. `js/category.js`를 추가했다. **접기 규칙의 스코프를 `.tt_category` → `.side-category`로 옮겼다** — `.tt_category`는 실블로그에서 확인된 적 없는 이름이라, 티스토리가 다른 이름을 내면 JS는 도는데 CSS가 안 먹는다. 기능은 우리 훅에, 치장만 티스토리 이름에 건다 |
| 2026-08-25 | JS 없이 4열 표가 360px에서 페이지를 31px 밀었다 | `.contents_style table`을 `display:block; overflow-x:auto` 기본값으로 두고, JS가 감싼 경우 `.table-scroll > table`이 `display:table`로 되돌린다. 스크롤 컨테이너는 항상 하나다. 대가: JS가 죽은 경로에서 셀이 폭에 맞춰 늘어나지 않는다 |
| 2026-08-25 | 라이트박스 가림막이 `color-mix()`에만 의존 | 미지원 브라우저에서 투명해진다. **정적 값을 앞줄에 두는 방식은 듣지 않는다** — 미지원 브라우저도 `color-mix` 선언 자체는 토큰 열로 받아들여 뒷줄이 이기고, `var()`를 쓰는 순간 계산값 시점에 무효가 되어 `transparent`가 된다(브라우저에서 재현). 정적 `rgba`를 기본값으로 두고 `@supports`로 올린다 |
