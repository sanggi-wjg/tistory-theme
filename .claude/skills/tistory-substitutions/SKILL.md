---
name: tistory-substitutions
description: "티스토리 스킨 치환자(그룹 치환자 <s_*>, 값 치환자 [##_*_##]) 레퍼런스. 어떤 치환자가 존재하는지, 어느 페이지 영역에서 동작하는지, 티스토리가 통짜로 렌더링해 손댈 수 없는 영역이 무엇인지 확인할 때 사용. skin.html이나 index.xml을 작성·수정하거나, 치환자 이름·동작·페이지 타입이 헷갈리거나, '이 데이터를 치환자로 가져올 수 있나'를 판단해야 할 때 반드시 이 스킬을 사용할 것. 치환자를 추측으로 쓰면 티스토리가 조용히 무시하므로 반드시 확인한다."
---

# 티스토리 치환자 레퍼런스

티스토리 스킨은 `skin.html` **한 장**이 모든 URL을 담당한다. 서버가 방문한 URL을 보고 해당 영역만 남기고 나머지를 지운다. 치환자를 잘못 쓰면 에러가 아니라 **빈 화면**이 나온다.

## 두 종류

| 종류 | 형태 | 역할 |
|---|---|---|
| 값 치환자 | `[##_이름_##]` | 값으로 치환 |
| 그룹 치환자 | `<s_이름>…</s_이름>` | 반복 / 조건 / 영역 선언 |

그룹 치환자의 세 역할을 구분하는 것이 중요하다:
- **반복** — `<s_list_rep>` 안쪽이 글 개수만큼 복제된다
- **조건** — `<s_list_rep_thumbnail>`은 대표이미지가 없으면 **블록째 사라진다**. 이 성질이 이 프로젝트의 기본이미지 fallback을 가능하게 한다
- **영역 선언** — `<s_permalink_article_rep>`·`<s_index_article_rep>`는 **`<s_article_rep>` 안에서만** 살아남는다. 바깥에 두면 에러 없이 통째로 버려진다(결정 29, 린트 `SUB008`)

## 검증이 먼저다

치환자 이름을 추측하지 않는다. 전체 목록이 `data/substitutions.json`에 있다 (그룹 62종 · 값 174종). 티스토리에는 컴파일러가 없어 오타는 조용히 무시되거나 문자 그대로 출력된다.

```bash
python3 -c "
import json; d=json.load(open('data/substitutions.json'))
print([g for g in d['groups'] if 'thumb' in g])"
```

원문 확인이 필요하면 `docs/tistory-skin-reference.txt` (공식 문서 24페이지 통합본)를 읽는다.

## 페이지 타입과 영역 — 가장 흔한 실수

`<body id="[##_body_id_##]">`에 페이지별 값이 들어온다.

| body_id | 페이지 | 목록 치환자 |
|---|---|---|
| `tt-body-index` | 홈 | **`<s_list_rep>`** — `<s_list>`는 홈에서도 렌더된다(결정 29) |
| `tt-body-page` | 글 | `<s_permalink_article_rep>` |
| `tt-body-category` | 카테고리 목록 | **`<s_list_rep>`** |
| `tt-body-search` | 검색결과 | `<s_list_rep>` |
| `tt-body-tag` | 태그 목록 | `<s_list_rep>` |
| `tt-body-archive` | 보관함 | `<s_list_rep>` |
| `tt-body-guestbook` | 방명록 | — |
| `tt-body-location` | 지역로그 | — |

**홈 목록도 `<s_list_rep>`로 그린다.** `<s_list>`는 홈에서도 렌더되고 `[##_list_conform_##]`이 "전체 글"로 채워진다(2026-08-25 실측, 결정 29). `<s_index_article_rep>`은 `<s_article_rep>`의 하위 영역이라 바깥에 두면 통째로 버려진다 — 이 스킨은 쓰지 않는다. 글 페이지의 `<s_permalink_article_rep>`도 같은 이유로 `<s_article_rep>` 안에 둔다. 안에서 쓰는 접두사는 각각 `[##_list_rep_*_##]` / `[##_article_rep_*_##]`다(린트 `AREA001`).

## 손댈 수 없는 영역

티스토리가 통짜로 렌더링한다. 치환자 한 줄만 놓고 CSS로만 스타일링한다.

| 치환자 | 출력 | 훅 |
|---|---|---|
| `[##_category_list_##]` (리스트형 — 폴더형 `[##_category_##]`은 다른 UI를 내며 `CAT001`이 막는다, 결정 31) | 카테고리 트리 전체 | `.tt_category` `.link_tit` `.category_list` `.link_item` `.sub_category_list` `.c_cnt` |
| `[##_comment_group_##]` | 댓글 UI 전체 (React) | `.tt-comment-cont` `.tt-area-reply` `.tt-item-reply` `.tt_desc` `.tt_date` … |
| `[##_guestbook_group_##]` | 방명록 UI 전체 (React) | 댓글과 동일 |

댓글을 `<s_rp>` 계열로 직접 구성하지 않는다. 치환자가 구형이라 **핀 고정·프로필 레이어·더보기 기능을 잃는다.**

## 함정

| 함정 | 내용 |
|---|---|
| `<s_t3>` 누락 | 티스토리 공통 JS가 안 들어가 댓글·공유가 전부 죽는다. **필수** |
| `[##_list_rep_title_##]` | New 아이콘 `<img>`가 섞여 나온다. 순수 텍스트는 `[##_list_rep_title_text_##]` |
| `<a [##_prev_page_##]>` | 링크가 아니라 `href`를 포함한 **속성 문자열째** 삽입된다. `href="[##_prev_page_##]"`는 깨진다 |
| `index.xml` 수정 | **스킨의 모든 설정이 초기화된다.** 변수 추가·이름 변경은 사용자 설정을 날린다 |
| 홈에서 글 선별 | 불가능하다. 커버를 쓰지 않는 홈은 최신순 자동 반복이다 |
| 본문 래퍼 | `<div class="tt_article_useless_p_margin contents_style">`. 정확일치 선택자로 찾으면 오래된 글이 누락된다 |

## 자주 쓰는 조합

기능별 치환자 조합, 스킨 옵션(`<variables>`) 정의법, 홈 커버 구조는 아래를 참조한다:

- **[references/common-patterns.md](references/common-patterns.md)** — 홈 목록 · 카테고리 목록 · 글 페이지 · 사이드바 · 페이징 · 관련글 · 스킨 옵션의 실제 코드
- **[references/skin-info-xml.md](references/skin-info-xml.md)** — `index.xml` 전체 구조, `<default>` 설정값 목록, `<variables>` 타입, `<liststyle>`, 홈 커버 정의

## 이 프로젝트의 확정 사항

`DECISIONS.md`와 `DESIGN.md`가 상위 규범이다. 치환자 선택이 그 결정과 충돌하면 문서를 따르고 리더에게 보고한다.
