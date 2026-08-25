# 치환자 조합 패턴

## 목차

1. [홈 목록](#1-홈-목록)
2. [카테고리·검색·태그 목록](#2-카테고리검색태그-목록)
3. [글 페이지](#3-글-페이지)
4. [관련글·이전글·다음글](#4-관련글이전글다음글)
5. [사이드바](#5-사이드바)
6. [페이징](#6-페이징)
7. [댓글·방명록](#7-댓글방명록)
8. [스킨 옵션](#8-스킨-옵션)
9. [광고](#9-광고)

---

## 1. 홈 목록

홈에서만 동작한다. 접두사가 `article_rep_`이다.

```html
<s_index_article_rep>
  <article class="post" data-cat="[##_article_rep_category_##]">
    <span class="thumb">
      <s_article_rep_thumbnail>
        <img src="[##_article_rep_thumbnail_url_##]" alt="">
      </s_article_rep_thumbnail>
    </span>
    <a href="[##_article_rep_link_##]" class="link">
      <strong class="title">[##_article_rep_title_##]</strong>
      <p class="summary">[##_article_rep_summary_##]</p>
    </a>
    <div class="meta">
      <a href="[##_article_rep_category_link_##]" class="cat">[##_article_rep_category_##]</a>
      <time>[##_article_rep_simple_date_##]</time>
      <s_rp_count><span class="cnt">[##_article_rep_rp_cnt_##]</span></s_rp_count>
    </div>
  </article>
</s_index_article_rep>
```

`<s_article_rep_thumbnail>`은 대표이미지가 없으면 **블록째 사라진다.** `.thumb`의 CSS 배경이 그대로 드러나므로 JS 없이 fallback이 된다.

---

## 2. 카테고리·검색·태그 목록

접두사가 `list_rep_`이다. 홈과 다르다.

```html
<s_list>
  <header class="list-head" <s_list_image>style="background-image:url('[##_list_image_##]')"</s_list_image>>
    <h1>[##_list_conform_##]</h1>
    <p>[##_list_description_##]</p>
    <span class="count">글 [##_list_count_##]개</span>
  </header>

  <s_list_empty>
    <p class="empty">해당하는 글이 없습니다.</p>
  </s_list_empty>

  <div class="list [##_list_style_##]">
    <s_list_rep>
      <article class="post" data-cat="[##_list_rep_category_##]">
        <span class="thumb">
          <s_list_rep_thumbnail><img src="[##_list_rep_thumbnail_##]" alt=""></s_list_rep_thumbnail>
        </span>
        <a href="[##_list_rep_link_##]" class="link">
          <strong class="title">[##_list_rep_title_text_##]</strong>
          <p class="summary">[##_list_rep_summary_##]</p>
        </a>
        <div class="meta">
          <time>[##_list_rep_regdate_##]</time>
          <span class="cnt">[##_list_rep_rp_cnt_##]</span>
        </div>
      </article>
    </s_list_rep>
  </div>
</s_list>
```

- `[##_list_conform_##]` — 카테고리 이름 / 검색어 / 태그명
- `[##_list_image_##]` — 카테고리 대표이미지 (**목록 상단 배너에 쓴다**)
- `[##_list_style_##]` — `index.xml`의 `<liststyle>`로 정의하면 카테고리 관리 화면에서 선택 가능
- **`[##_list_rep_title_text_##]`** — `_title_`에는 New 아이콘이 섞인다

---

## 3. 글 페이지

```html
<s_permalink_article_rep>
  <article class="entry">
    <header>
      <a href="[##_article_rep_category_link_##]" class="cat">[##_article_rep_category_##]</a>
      <h1>[##_article_rep_title_##]</h1>
      <div class="meta">
        <time datetime="[##_article_rep_date_year_##]-[##_article_rep_date_month_##]-[##_article_rep_date_day_##]">
          [##_article_rep_date_##]
        </time>
        <s_rp_count><span>댓글 [##_article_rep_rp_cnt_##]</span></s_rp_count>
      </div>
    </header>

    <div class="body">[##_article_rep_desc_##]</div>

    <s_tag_label>
      <div class="tags">[##_tag_label_rep_##]</div>
    </s_tag_label>

    <s_ad_div>
      <div class="admin">
        <a href="[##_s_ad_m_link_##]">수정</a>
        <a href="#" onclick="[##_s_ad_d_onclick_##]">삭제</a>
      </div>
    </s_ad_div>
  </article>
</s_permalink_article_rep>
```

- `[##_article_rep_desc_##]` — 본문 전체. 티스토리 에디터 마크업이 통째로 들어온다
- `<s_ad_div>` — 관리자에게만 보인다

---

## 4. 관련글·이전글·다음글

```html
<s_article_related>
  <nav class="related">
    <strong>'[##_article_rep_category_##]'의 다른 글</strong>
    <ul>
      <s_article_related_rep>
        <li class="[##_article_related_rep_type_##]">
          <a href="[##_article_related_rep_link_##]">
            <s_article_related_rep_thumbnail>
              <img src="[##_article_related_rep_thumbnail_link_##]" alt="">
            </s_article_related_rep_thumbnail>
            <span class="t">[##_article_related_rep_title_##]</span>
            <time>[##_article_related_rep_date_##]</time>
          </a>
        </li>
      </s_article_related_rep>
    </ul>
  </nav>
</s_article_related>

<nav class="adjacent">
  <s_article_prev>
    <a href="[##_article_prev_link_##]" class="prev [##_article_prev_type_##]">
      <s_article_prev_thumbnail><img src="[##_article_prev_thumbnail_link_##]" alt=""></s_article_prev_thumbnail>
      <span>[##_article_prev_title_##]</span>
    </a>
  </s_article_prev>
  <s_article_next>
    <a href="[##_article_next_link_##]" class="next [##_article_next_type_##]">
      <s_article_next_thumbnail><img src="[##_article_next_thumbnail_link_##]" alt=""></s_article_next_thumbnail>
      <span>[##_article_next_title_##]</span>
    </a>
  </s_article_next>
</nav>
```

`[##_article_related_rep_type_##]`은 `text_type` / `thumb_type`을 출력한다. **티스토리가 썸네일 유무를 알려주므로** 클래스로 받아 CSS 분기에 쓸 수 있다.

---

## 5. 사이드바

`<s_sidebar_element>`의 **첫 줄 주석이 사이드바 타이틀**이 된다.

```html
<div class="sidebar">
  <s_sidebar>
    <s_sidebar_element>
      <!-- 검색 -->
      <div class="mod search">
        <s_search>
          <input type="text" name="[##_search_name_##]" value="[##_search_text_##]"
                 onkeypress="if (event.keyCode == 13) { [##_search_onclick_submit_##] }">
          <button onclick="[##_search_onclick_submit_##]">검색</button>
        </s_search>
      </div>
    </s_sidebar_element>

    <s_sidebar_element>
      <!-- 카테고리 -->
      <div class="mod category">[##_category_##]</div>
    </s_sidebar_element>

    <s_sidebar_element>
      <!-- 최근 글 -->
      <div class="mod recent">
        <ul>
          <s_rctps_rep>
            <li>
              <a href="[##_rctps_rep_link_##]">[##_rctps_rep_title_##]</a>
              <time>[##_rctps_rep_simple_date_##]</time>
            </li>
          </s_rctps_rep>
        </ul>
      </div>
    </s_sidebar_element>

    <s_sidebar_element>
      <!-- 인기 글 -->
      <div class="mod popular">
        <ul>
          <s_rctps_popular_rep>
            <li><a href="[##_rctps_rep_link_##]">[##_rctps_rep_title_##]</a></li>
          </s_rctps_popular_rep>
        </ul>
      </div>
    </s_sidebar_element>

    <s_sidebar_element>
      <!-- 태그 -->
      <div class="mod tags">
        <s_random_tags>
          <a href="[##_tag_link_##]" class="[##_tag_class_##]">[##_tag_name_##]</a>
        </s_random_tags>
      </div>
    </s_sidebar_element>
  </s_sidebar>
</div>
```

- `[##_category_##]` 폴더형 / `[##_category_list_##]` 리스트형
- 인기글은 `<s_rctps_popular_rep>`이지만 **안쪽 값 치환자는 최근글과 같은 `[##_rctps_rep_*_##]`**를 쓴다
- `[##_tag_class_##]` — `cloud1`~`cloud5` (빈도 5단계)

---

## 6. 페이징

```html
<s_paging>
  <nav class="paging">
    <a [##_prev_page_##] class="[##_no_more_prev_##]">이전</a>
    <s_paging_rep>
      <a [##_paging_rep_link_##] class="num">[##_paging_rep_link_num_##]</a>
    </s_paging_rep>
    <a [##_next_page_##] class="[##_no_more_next_##]">다음</a>
  </nav>
</s_paging>
```

**`href=`를 쓰지 않는다.** 치환자가 `href="..."` 전체를 포함한 속성 문자열로 치환된다.

---

## 7. 댓글·방명록

```html
<s_permalink_article_rep>
  [##_comment_group_##]
</s_permalink_article_rep>

<!-- 방명록 페이지 -->
[##_guestbook_group_##]
```

한 줄이면 끝난다. 서버는 빈 `<div data-tistory-react-app="Comment">`를 내보내고 클라이언트에서 채워진다. **JS로 조작하려면 `MutationObserver`가 필요하다.**

---

## 8. 스킨 옵션

`index.xml`에 정의하고 `skin.html`에서 쓴다.

```xml
<variables>
  <variablegroup name="레이아웃">
    <variable>
      <name>show-sidebar</name>
      <label><![CDATA[사이드바 표시]]></label>
      <type>BOOL</type>
      <option />
      <default>true</default>
      <description><![CDATA[목록 페이지에 사이드바를 표시합니다.]]></description>
    </variable>
  </variablegroup>
</variables>
```

```html
<s_if_var_show-sidebar>
  <div class="sidebar">…</div>
</s_if_var_show-sidebar>

<s_not_var_show-sidebar>
  <div class="no-sidebar-notice">…</div>
</s_not_var_show-sidebar>

<style>.hero { background-image: url('[##_var_cover-image_##]'); }</style>
```

타입: `STRING` `SELECT` `IMAGE` `BOOL` `COLOR`

⚠️ `index.xml`을 바꾸면 **스킨의 모든 설정이 초기화된다.** 변수 이름은 한 번 정하면 바꾸지 않는다.

---

## 9. 광고

```html
[##_revenue_list_upper_##]   <!-- 홈·목록 상단 -->
[##_revenue_list_lower_##]   <!-- 홈·목록 하단 -->
```

자리만 심어두면 노출 여부는 티스토리 수익 설정에서 결정된다. 글 페이지 본문 광고는 티스토리가 자동 삽입하므로 스킨에 넣지 않는다.
