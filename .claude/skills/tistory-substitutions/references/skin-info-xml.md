# index.xml — 스킨 정보 파일

> ⚠️ **이 파일이 변경되면 스킨의 모든 설정이 초기화된다.** 변수 이름과 구조는 한 번 정하면 바꾸지 않는다. 값만 바꾸는 것도 초기화를 유발하므로, 배포 시점에 한 번에 확정한다.

## 목차

1. [전체 구조](#1-전체-구조)
2. [기본 정보와 제작자](#2-기본-정보와-제작자)
3. `<default>` [설정 기본값](#3-default-설정-기본값)
4. `<variables>` [스킨 옵션](#4-variables-스킨-옵션)
5. `<liststyle>` [리스트 스타일](#5-liststyle-리스트-스타일)
6. `<cover>` [홈 커버](#6-cover-홈-커버)

---

## 1. 전체 구조

```xml
<?xml version="1.0" encoding="utf-8"?>
<skin>
  <information>
    <name>스킨 이름</name>
    <version>1.0</version>
    <description><![CDATA[설명]]></description>
    <license><![CDATA[라이선스]]></license>
  </information>
  <author>
    <name>제작자</name>
    <homepage>https://…</homepage>
    <email>…</email>
  </author>
  <default>…</default>
  <variables>…</variables>
  <liststyle>…</liststyle>
  <cover>…</cover>
</skin>
```

---

## 2. 기본 정보와 제작자

스킨 목록·상세보기에 표시된다. `<information><name>`은 스킨 보관함에서 스킨을 식별하는 이름이기도 하다.

---

## 3. `<default>` 설정 기본값

티스토리가 이미 만들어둔 **고정 설정 항목**의 기본값이다. 사용자는 관리 화면에서 이 값을 바꿀 수 있다.

| 키 | 의미 |
|---|---|
| `entriesOnPage` | 홈 화면 글 수 |
| `entriesOnList` | 글 목록 글 수 |
| `recentEntries` | 사이드바 최근글 개수 |
| `recentComments` | 사이드바 최근 댓글 개수 |
| `tagsInCloud` | 사이드바 태그 개수 |
| `sortInCloud` | 태그 정렬 (1:인기도 2:이름 3:랜덤) |
| `itemsOnGuestbook` | 방명록 페이지당 개수 |
| `lengthOfRecentEntry` | 최근글 제목 글자수 |
| `lengthOfRecentComment` | 최근 댓글 글자수 |
| `lengthOfRecentNotice` | 최근 공지 글자수 |
| `lengthOfLink` | 링크 글자수 |
| `expandComment` | 댓글 영역 (0:감추기 1:펼치기) |
| `showListOnCategory` | **커버 미사용 홈의 목록 표현** (0:내용만 1:목록만 2:내용+목록) |
| `showListOnArchive` | 보관함 목록 표현 |
| `showListLock` | 홈 설정에서 '목록 구성 요소' 노출 여부 (0:노출 1:숨김) |
| `contentWidth` | 콘텐츠 가로 크기. **에디터 위지윅이 이 폭에 맞춰진다** |
| `tree.color` / `bgColor` / `activeColor` / `activeBgColor` | 카테고리 트리 색상 |
| `tree.labelLength` | 카테고리 글자수 |
| `tree.showValue` | 카테고리 글 수 표시 (0:숨김 1:보임) |

`<tree>`는 `[##_category_##]`가 통짜로 렌더링하는 카테고리 트리의 색을 제어하는 **유일한 수단**이다. CSS로도 덮을 수 있지만 여기서 기본값을 맞춰두는 편이 안전하다.

```xml
<default>
  <entriesOnPage>7</entriesOnPage>
  <entriesOnList>20</entriesOnList>
  <showListOnCategory>1</showListOnCategory>
  <contentWidth>720</contentWidth>
  <tree>
    <color>4d4d4d</color>
    <bgColor>ffffff</bgColor>
    <activeColor>0070f3</activeColor>
    <activeBgColor>fafafa</activeBgColor>
    <labelLength>30</labelLength>
    <showValue>1</showValue>
  </tree>
</default>
```

---

## 4. `<variables>` 스킨 옵션

**내가 직접 만드는 설정 항목**이다. 관리 화면에 노출되고 `skin.html`에서 치환자로 쓴다.

```xml
<variables>
  <variablegroup name="그룹 이름">
    <variable>
      <name>치환자에서 쓸 이름</name>
      <label><![CDATA[사용자에게 보일 이름]]></label>
      <description><![CDATA[설명 (선택)]]></description>
      <type>BOOL</type>
      <option />
      <default>true</default>
    </variable>
  </variablegroup>
</variables>
```

| 타입 | 값 | `<option>` |
|---|---|---|
| `STRING` | 문자 | 불필요 |
| `BOOL` | true/false | 불필요 |
| `COLOR` | `#000000` | 불필요 |
| `IMAGE` | 이미지 URL | 불필요 |
| `SELECT` | 선택값 | **필수** — name/label/value JSON 배열 |

```xml
<variable>
  <name>theme-default</name>
  <label><![CDATA[기본 테마]]></label>
  <type>SELECT</type>
  <option><![CDATA[
    [
      {"name":"system", "label":"시스템 설정 따름", "value":"system"},
      {"name":"light",  "label":"밝게",           "value":"light"},
      {"name":"dark",   "label":"어둡게",         "value":"dark"}
    ]
  ]]></option>
  <default>system</default>
</variable>
```

**사용**

```html
<s_if_var_이름>  …값이 있으면(BOOL은 true면) 남는다…  </s_if_var_이름>
<s_not_var_이름> …값이 없으면(BOOL은 false면) 남는다… </s_not_var_이름>
[##_var_이름_##]
```

> 이 프로젝트는 본인 블로그 전용이므로 변수를 최소화한다. 값을 바꿀 일이 드문 것은 코드에 직접 박는 편이 `index.xml` 초기화 위험을 줄인다.

---

## 5. `<liststyle>` 리스트 스타일

정의하면 **카테고리 관리 화면에 리스트 스타일 선택기가 생긴다.** 카테고리별로 다른 목록 모양을 줄 수 있다.

```xml
<default>
  <liststyle>list</liststyle>
</default>

<liststyle>
  <item><label>목록형</label><value>list</value></item>
  <item><label>카드형</label><value>card</value></item>
  <item><label>갤러리형</label><value>gallery</value></item>
</liststyle>
```

선택된 값이 `[##_list_style_##]`로 출력되므로 class로 받아 CSS 분기한다.

```html
<div class="list [##_list_style_##]">…</div>
```

---

## 6. `<cover>` 홈 커버

정의하면 관리 화면에 **"홈 편집" UI**가 생기고, 사용자가 블록을 골라 순서대로 조립한다. `skin.html`에는 각 블록의 **모양만** 정의한다.

```xml
<cover>
  <item>
    <name>featured</name>
    <label><![CDATA[주목할 글]]></label>
    <description><![CDATA[강조할 글을 크게 표시합니다.]]></description>
  </item>
  <item>
    <name>list</name>
    <label><![CDATA[글 목록]]></label>
    <description><![CDATA[최신 글을 목록으로 표시합니다.]]></description>
  </item>
</cover>
```

```html
<s_cover_group>
  <s_cover_rep>
    <s_cover name='featured'>
      <section class="cover-featured">
        <h2>[##_cover_title_##]</h2>
        <s_cover_item>
          <article>
            <s_cover_item_thumbnail><img src="[##_cover_item_thumbnail_##]" alt=""></s_cover_item_thumbnail>
            <a href="[##_cover_item_url_##]">[##_cover_item_title_##]</a>
            <s_cover_item_article_info>
              <span>[##_cover_item_category_##] · [##_cover_item_simple_date_##]</span>
            </s_cover_item_article_info>
          </article>
        </s_cover_item>
        <s_cover_url><a href="[##_cover_url_##]">더보기</a></s_cover_url>
      </section>
    </s_cover>
  </s_cover_rep>
</s_cover_group>
```

**기본값** — `<default><cover>`에 JSON 문자열로 추천 조합을 넣으면 스킨 적용 즉시 반영된다.

```json
[
  { "name": "featured", "title": "", "dataType": "RECENT", "data": { "category": "ALL", "size": 1 } },
  { "name": "list",     "title": "", "dataType": "RECENT", "data": { "category": "ALL", "size": 9 } }
]
```

- `dataType` — `RECENT`(최신 글) 또는 `CUSTOM`(직접 입력)만 가능
- `RECENT`의 `category`는 **`ALL` 또는 `NOTICE`만** 지정할 수 있다 (제작자가 사용자의 카테고리를 알 수 없으므로)
- `size` 1~100

> 이 프로젝트는 커버를 쓰지 않기로 했다(`DECISIONS.md` #4). 다만 홈 블록을 커버로 전환 가능한 구조로 만들어두므로, 전환 시 이 문서를 참조한다.
