---
name: skin-qa-check
description: "티스토리 스킨 검증 스킬. 치환자 유효성 린트, 마크업↔CSS↔JS 경계면 교차 검증, 디자인 토큰 준수, 인라인 스타일 보정 커버리지, 접근성·안정성을 점검한다. 스킨을 수정한 뒤 '검증', 'QA', '점검', '린트', '확인해줘', '문제 없나', '빠진 거 없나' 요청 시 반드시 이 스킬을 사용할 것. 이 도메인은 오타·불일치가 에러 없이 조용히 실패하므로 눈으로 보는 것만으로는 부족하다."
---

# 스킨 검증

티스토리 스킨에는 컴파일러도 타입 시스템도 없다. **세 가지가 전부 조용히 실패한다:**

- 치환자 오타 → 티스토리가 무시하거나 문자 그대로 출력
- CSS 선택자 불일치 → 매칭이 안 돼도 에러 없음
- JS 셀렉터 불일치 → `null` 반환하고 끝

그래서 검증은 "돌려보니 되더라"로 끝낼 수 없다.

## 정적 린트

```bash
python3 .claude/skills/skin-qa-check/scripts/lint.py
python3 .claude/skills/skin-qa-check/scripts/lint.py --json   # 자동화용
```

오류가 있으면 exit code 1을 반환한다.

| 코드 | 검사 |
|---|---|
| `SUB001~006` | 존재하지 않는 치환자, `index.xml`에 없는 변수, 여닫이 불일치, **`<s_t3>` 누락** |
| `AREA001~004` | 홈/목록 접두사 혼용(`article_rep` ↔ `list_rep`), `body_id` 누락 |
| `BND001~005` | `data-cat` 경계면, 카테고리 커버리지, JS 셀렉터 ↔ 마크업, **`[class="contents_style"]` 정확일치** |
| `TOK001~005` | 토큰 우회 색 리터럴, 다크 블록 안 색 직접 지정, `prefers-color-scheme` 누락, body 배경 |
| `INL001` | 인라인색 보정 커버리지 (`data/inline-styles.json` 필요) |
| `ROB001~002`, `A11Y001~002` | `localStorage` try/catch, `MutationObserver`, `lang`, viewport |

## 린트가 못 잡는 것 — 눈으로 봐야 한다

정적 분석은 "연결이 맞는가"까지만 본다. **"보기에 맞는가"는 프리뷰로 확인한다.**

```bash
npm run build && python3 .claude/skills/skin-preview/scripts/render.py && open _preview/index.html
```

### 페이지 커버리지
8개 페이지가 **빈 화면 없이** 나오는가. 특히 `empty`(검색 결과 0건)와 `guestbook`은 빠뜨리기 쉽다.

### 다크모드 — 세 상태를 모두 본다
1. `:root[data-theme="dark"]`
2. `:root[data-theme="light"]`
3. **stamp 없음** — OS 다크 설정에서 `data-theme` 속성 없이. 대부분의 방문자가 여기 있고, 대부분의 버그도 여기서 나온다

각 상태에서 `page` 페이지의 본문 인라인 오염이 보정되는지 확인한다. 픽스처에 `#000000` `#333333` `#252525` `#eeffff` `#f8f8f8`가 모두 들어 있다.

### 반응형
640 / 768 / 1024 / 1440px. **페이지 본문이 가로로 스크롤되면 실패다.** 코드블록·표는 자기 컨테이너 안에서만 스크롤해야 한다. 홈 카드 제목이 2줄에서 잘리는지도 본다(홈 노출 제목 중앙값 49자).

### 접근성
- 라이트박스 `Esc` 닫기 + 포커스 복귀
- 모든 인터랙티브 요소에 보이는 포커스 상태
- 본문 대비 4.5:1 (라이트·다크 양쪽)
- 키보드만으로 목차·토글·복사 버튼 도달

## 리포트 규칙

`_workspace/qa-report.md`에 **통과 / 실패 / 미검증** 3분류로 쓴다.

**"미검증"을 "통과"로 적지 않는다.** 로컬 프리뷰로 확인할 수 없는 것이 있다 — 댓글 UI, 광고 삽입, 페이징 실제 동작, 스킨 옵션 UI. 목록은 `/skin-preview` 스킬의 "렌더러가 재현하지 못하는 것" 참조.

지적은 파일:라인과 수정 방법을 포함한다.

```
❌ src/skin.html:142 가 class="card"를 출력하는데
   src/styles/components.css:88 은 .post를 찾는다.
   → 어느 쪽으로 통일할지 결정 필요 (markup·style 양쪽에 알림)
```

## 경계면은 양쪽을 동시에 읽는다

한쪽만 봐서는 못 잡는다.

| 검증 | 왼쪽(생산자) | 오른쪽(소비자) | 어긋나면 |
|---|---|---|---|
| 훅 이름 | `skin.html` class·data | CSS 선택자 / JS 셀렉터 | 조용한 무동작 |
| `data-cat` | 마크업의 치환자 | CSS 접두 선택자 | **기본이미지 전부 무너짐** |
| 카테고리 | `data/categories.json` | CSS 규칙 11종 | 새 카테고리 누락 |
| 스킨 옵션 | `index.xml` `<name>` | `[##_var_*_##]` | 빈 값 |
| 영역 치환자 | 놓인 위치 | 유효한 페이지 타입 | **화면 통째로 빔** |
| 인라인색 | `data/inline-styles.json` | CSS 보정 규칙 | 다크에서 글자 실종 |
| JS 생성 DOM | `script.js`의 클래스 | CSS 대응 규칙 | 스타일 없는 날것 |
