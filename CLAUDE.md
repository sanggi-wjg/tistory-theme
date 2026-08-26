# 상쾌한기분 티스토리 스킨

`sanggi-jayg.tistory.com`의 커스텀 티스토리 스킨을 직접 제작하는 프로젝트.

**상위 규범** — 판단이 필요하면 이 둘을 먼저 본다.
- [DECISIONS.md](./DECISIONS.md) — 확정 결정 33건, 근거, 플랫폼 제약, 275편 실측, 미결 사항
- [DESIGN.md](./DESIGN.md) — 디자인 시스템 (토큰·타이포·컴포넌트·티스토리 고정 마크업 대응)

[HANDOFF.md](./HANDOFF.md)는 특정 시점의 인수인계 스냅샷이다. **사용자가 명시적으로 요청할 때만 읽는다** — 시간이 지나면 위 두 문서와 어긋나므로, 자동으로 읽으면 낡은 상태를 현재로 오인하게 된다.

## 작업 방식

**파일을 바꾸는 작업은 worktree에서 시작한다.** 브랜치를 따는 것과 같은 급의 기본 절차다. 조건을 따지지 않는다 — 다른 세션이 도는지 확인할 방법이 없고, 확인해야 하는 절차는 결국 건너뛰게 된다.

```
1. EnterWorktree          ← 파일을 바꾸기 전에 먼저
2. npm install            ← worktree마다 필요하다
3. … 작업 …
4. npm run check          ← 빌드 → 린트 → 프리뷰. 통과해야 커밋
5. 커밋 → 푸시 → gh pr create --base main
6. 머지되면 정리           ← 아래 「머지 후 정리」
```

**예외는 읽기뿐이다.** 질문에 답하거나 코드를 훑어보는 것처럼 아무것도 바꾸지 않는 작업은 그냥 한다.

`EnterWorktree`는 최신 `origin/main`에서 `.claude/worktrees/<이름>`에 worktree를 만들고 세션을 그리로 옮긴다. 브랜치 이름은 도구가 정한다(`worktree-<이름>`).

**나올 때는 `ExitWorktree`에 `keep`을 쓴다.** `remove`는 원래 브랜치에 없는 커밋이 있으면 거부하는데, 푸시 여부를 보지 않으므로 **PR을 올린 뒤에는 항상 거부된다.**

worktree 이름은 작업 범위로 짓는다 — `home-grid`, `toc-scrollspy`, `inline-fix`.

**여러 세션이 같은 목록에 항목을 더할 때는 번호를 쓰지 않는다.** `DECISIONS.md` 미결처럼
번호로 식별하는 목록은 동시 작업에서 반드시 겹친다 — 슬러그를 쓴다. 기존 번호는 다른 문서가
참조하므로 그대로 둔다.

**`main`에 직접 커밋하지 않는다.** worktree를 쓰면 자연히 지켜진다.

**PR 본문에 담을 것**
- **무엇을** 바꿨는가 — 파일 나열이 아니라 결과로
- **왜** — `DECISIONS.md`의 결정 번호나 `DESIGN.md` 절을 참조
- **어떻게 확인했는가** — 린트 결과, 프리뷰에서 본 페이지, **검증하지 못한 것**
- 스킨 변경이면 프리뷰 스크린샷

### 왜 worktree인가

여러 세션이 같은 디렉터리에서 일하면 서로의 작업 트리를 밟는다. 한쪽이 브랜치를 바꾸면 다른 쪽 파일이 그대로 바뀌고, 각자 `git add -A`를 돌리면 **커밋에 남의 변경이 섞인다.** 이 저장소에서 실제로 한 번 일어났다 — 커밋 메시지와 내용이 어긋난 이력이 남아 있다.

cmux를 쓰든 창을 여러 개 띄우든 마찬가지다. **터미널은 나뉘어도 파일시스템은 하나다.** worktree만이 작업 트리를 실제로 분리한다.

**worktree에서 주의할 것**

| 항목 | 동작 |
|---|---|
| `node_modules/` | worktree마다 따로 설치해야 한다 (esbuild는 플랫폼 바이너리) |
| `dist/` · `_preview/` · `_workspace/` | worktree별로 독립. **충돌하지 않는다** |
| `data/*.json` | git으로 공유된다. 한쪽에서 `/blog-census`로 갱신했으면 **커밋해야** 다른 쪽이 본다 |
| 같은 브랜치 | 두 worktree에서 동시에 체크아웃할 수 없다 |

**커밋 전 필수** — `npm run check`가 통과해야 한다. 린트 오류가 남은 채로 커밋하지 않는다. 이 도메인은 조용히 실패하므로 린트가 유일한 조기 경보다.

**작업 한 사이클은 PR 생성까지가 기본이다.** 사용자가 매번 요청하지 않아도 worktree → 커밋 → 푸시 → PR까지 진행한다. 다만 **PR을 merge하지는 않는다** — 병합은 사용자의 판단이다. 확신이 서지 않는 변경은 `--draft`로 연다. **머지된 뒤의 정리는 다시 내 몫이다** — 아래 「머지 후 정리」.

### 머지 후 정리 — 요청을 기다리지 않는다

**PR이 머지된 것을 확인하면 그 자리에서 worktree를 정리한다.** 내가 머지했든 사용자가 직접 했든 같다. 정리를 사용자 숙제로 남기면 죽은 worktree와 브랜치가 쌓이고, `git worktree list`가 길어지면 **어느 것이 살아 있는 작업인지 구분이 안 된다** — 그러면 남의 작업을 지우는 사고로 이어진다.

```bash
gh pr view <번호> --json state --jq .state     # MERGED 여야 한다. 이것부터 확인한다
# 세션이 그 worktree 안에 있으면 ExitWorktree(keep)로 먼저 나온다 — 안에서는 지울 수 없다
git worktree remove .claude/worktrees/<이름>
git branch -D worktree-<이름>                  # 스쿼시 머지는 커밋을 그대로 남기지 않아 -d는 거부한다
git fetch --prune                              # 원격 브랜치는 머지 때 GitHub이 지운다. 죽은 추적 참조만 턴다
```

원격은 저장소 설정(`deleteBranchOnMerge`)이 처리한다. 그래도 남아 있으면 —
`gh pr merge`를 안 쓰고 머지했거나 설정이 꺼졌다는 뜻이다 — `git push origin --delete worktree-<이름>`.

**확인하지 않은 것은 지우지 않는다.** `MERGED`가 아니면 그대로 둔다. 닫히기만 한 PR(`CLOSED`)의 worktree에는 **아직 아무 데도 없는 작업**이 들어 있다.

**내가 만든 것만 정리한다.** `git worktree list`에 `locked`로 뜨는 것은 다른 세션이 쓰는 중이다. git이 거부하지만, 애초에 대상으로 삼지 않는다.

`git worktree remove`가 거부하면 커밋되지 않은 변경이 남은 것이다. **무엇인지 보고 나서** 판단한다 — `--force`부터 쓰지 않는다.

## 하네스: 티스토리 스킨 제작

**목표:** 치환자·고정 마크업·수동 배포라는 티스토리 제약 위에서, 조용히 실패하지 않는 스킨을 만든다.

**트리거:** 스킨 구현·수정·기능 추가 요청 시 `tistory-skin-orchestrator` 스킬을 사용하라. 치환자 질문 같은 단순 조회는 직접 응답 가능.

**SEO는 별도 축이다.** 검색 유입·색인·내부링크·구조화 데이터 요청은 `seo-auditor` 에이전트가 맡는다. 배포 직후에는 `seo-verify-live` 스킬로 **프로덕션 실물**을 확인한다 — 소스 린트는 배포 사고를 원리적으로 잡지 못한다. 무엇이 우리 레버이고 무엇이 티스토리 소관인지는 `DECISIONS.md` 결정 28에 있다.

**이 도메인의 핵심 위험:** 티스토리에는 컴파일러가 없다. 치환자 오타는 무시되고, CSS 선택자 불일치는 에러를 내지 않으며, JS 셀렉터는 `null`을 반환하고 끝난다. **셋 다 조용히 실패한다.** 그래서 배포 전 `skin-qa-check` 린트가 필수다.

**변경 이력:**

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-08-24 | 초기 구성 — 에이전트 5, 스킬 7 | 전체 | — |
| 2026-08-25 | 브랜치·PR 작업 방식 지침 추가 | CLAUDE.md, 오케스트레이터 Phase 5 | main 직접 커밋을 막고 변경을 PR 단위로 검토하기 위해 |
| 2026-08-25 | worktree·cmux 동시 작업 지침 추가 | CLAUDE.md, .gitignore | 여러 세션이 같은 디렉터리에서 브랜치를 바꿔 서로 밟는 것을 막기 위해 |
| 2026-08-25 | worktree를 조건 없는 기본 절차로 | CLAUDE.md, 오케스트레이터 Phase 0 | "다른 세션이 도는지" 는 확인할 방법이 없어 결국 건너뛰게 된다. 브랜치처럼 무조건 하는 절차로 바꿨다 |
| 2026-08-25 | HANDOFF를 요청 시에만 읽도록 | CLAUDE.md, HANDOFF.md | 스냅샷이라 시간이 지나면 살아 있는 문서와 어긋난다. 자동으로 읽으면 낡은 상태를 현재로 오인한다 |
| 2026-08-25 | 카테고리 개편 적용 후 문서 정리 — 개편안·매핑·생성 스크립트 삭제, 실측 반영 | DECISIONS.md(결정 27 신설), DESIGN.md, HANDOFF.md, data/ | 개편안이 실물이 된 뒤에도 남아 있으면 계획과 현재가 두 벌로 갈린다. 살릴 근거(축·이름 규칙·정렬 판단)는 DECISIONS.md로 옮겼다 |
| 2026-08-25 | 오케스트레이터를 `TeamCreate` 가용 여부로 분기 | 오케스트레이터 Phase 2·3·5 | 첫 실행에서 이 환경에 `TeamCreate`가 없어 Phase 2·3이 통째로 실행 불가였다. 환경마다 다르므로 두 모드를 모두 담았다 |
| 2026-08-25 | 기본 이미지 15장 도안 + 마스크 방식 채택 | src/assets/placeholders/, scripts/gen-placeholders.py, DESIGN.md §6.2, DECISIONS.md 결정 5·6 | 마스크로 쓰면 색이 토큰에서만 나와 라이트/다크가 한 파일로 갈린다 — 28장이 15장이 되고 팔레트가 바뀌어도 도안이 따라온다 |
| 2026-08-25 | SEO 하네스 추가 — 에이전트 `seo-auditor`, 스킬 `seo-verify-live`, 린트 `SEO001~005` | .claude/agents, .claude/skills, DECISIONS.md(결정 28), skin-deploy, skin-qa-check | 레딧 SEO 워크플로 검토 결과, 5단계 중 **배포 후 프로덕션 실물 검증**이 우리에게 가장 잘 맞고 지금 없었다. 배포가 수동 복붙이라 소스와 프로덕션이 갈라지는 경로가 여럿인데 소스 린트가 하나도 못 잡는다. 동시에 실측으로 **모바일 우선 색인이 커스텀 스킨을 통째로 우회한다**는 것을 확인했다 |
| 2026-08-25 | 스킨 첫 구현 — 훅 계약을 `docs/`로 이동, 린트 `SUB007`, 렌더러 8 → 10페이지 | src/ 전체, docs/hooks.md, skin-qa-check, skin-preview | `_workspace/`가 gitignore라 CSS 주석이 참조하는 계약 문서가 저장소에 없었다. 렌더러가 공지와 "목차 있는 글"을 한 번도 렌더하지 않아 그 안의 결함을 눈으로 찾아야 했다 |
| 2026-08-25 | 정리 절차에서 원격 브랜치 삭제를 `fetch --prune`으로 | CLAUDE.md | 저장소에 `deleteBranchOnMerge`를 켜서 머지 때 GitHub이 원격을 지운다. 손으로 지우는 단계가 남아 있으면 이미 없는 것을 지우려다 실패한다. 설정이 꺼진 경우만 예외로 남겼다 |
| 2026-08-25 | 머지 후 worktree 정리를 자동 절차로 | CLAUDE.md | 정리를 사용자 숙제로 남기면 죽은 worktree가 쌓이고, 목록이 길어지면 살아 있는 작업과 구분이 안 된다. 머지 확인(`MERGED`)을 조건으로 달아 닫히기만 한 PR의 작업은 지우지 않게 했다 |
| 2026-08-25 | 라이브 검증 대상을 대상 블로그에서 찾도록 — `--post-path`·`--category`, baseline에 대상 고정 | seo-verify-live, skin-deploy | 테스트 블로그 첫 baseline이 `V014`로 저장되지 않았다. 검증기가 `data/posts.json`(본 블로그 실측)의 글·카테고리를 테스트 블로그에 붙여 404를 냈다. 실측이 늘어도 배포 전/후가 같은 글을 비교하도록 기준선에 대상을 박았다 |
| 2026-08-25 | 🔴 첫 배포 사고 수습 — `s_article_rep` 래퍼 추가, 홈 목록을 `s_list` 한 벌로 통합, 린트 `SUB008`, 렌더러에 영역 중첩 규칙 | src/skin.html, layout.css, components.css, docs/hooks.md, DECISIONS.md(결정 29), DESIGN.md §3, skin-qa-check, skin-preview, seo-verify-live, skin-deploy | `<s_permalink_article_rep>`를 최상위에 두어 글 본문이 통째로 사라졌다. 에러도 빈 껍데기도 없었고 홈은 `s_list`가 대신 그려 줘 멀쩡해 보였다. 짝 검사로는 원리적으로 못 잡는다 — 짝은 맞고 위치만 틀리다. 프리뷰도 규칙을 몰라 통과 신호를 위조하고 있었다 |
| 2026-08-25 | 스킨 미리보기 이미지 4종 — `scripts/gen-preview.mjs` | src/preview/, scripts/gen-preview.mjs, scripts/build.mjs, skin-deploy, DECISIONS.md(§2·미결 7) | 관리 화면에 엑박이 떴다. preview*는 스킨 **루트** 파일이라 처음엔 zip 패키지를 만들었는데 **티스토리가 zip을 받지 않았다.** 실제로는 파일업로드 탭이 이 이름들만 루트로 보낸다 — 목적지가 파일명으로 갈린다. 공식 문서에 없는 동작이라 §2에 실측으로 남겼다. zip 패키징은 지웠다 |
| 2026-08-25 | 🔴 카테고리를 리스트형 치환자로 — `[##_category_list_##]`, 린트 `CAT001`, 라이브 검사 `V016`, 선택 상태 `li.selected` | src/skin.html, tistory.css, js/category.js, skin-qa-check, skin-preview, seo-verify-live, skin-deploy, DECISIONS.md(결정 31·미결 14 해결), DESIGN.md §5.3, docs/hooks.md | 배포본이 **폴더형**을 내보내고 있었다. 중첩 table 19 + 트리선 GIF 17장에 링크는 `onclick`이라 **`<a href>`가 0개** — 사이드바 최대 모듈이 크롤러에도 키보드에도 닿지 않았다. 리스트형으로 바꾸니 내부링크 36개가 생기고 인라인 `style`이 18개 → 0개가 되어 **미결 14(다크 트리 색)가 원인째 사라졌다** — `!important`도 `index.xml` 수정도 없이. 프리뷰가 두 치환자를 같은 마크업에 매핑해 두어 또 통과 신호를 위조했다 |
| 2026-08-25 | 사이드바를 좌측 레일로 — 홈·글에서도 표시, `--wrap` 1400 · `--sidebar-w` 240 | src/styles/tokens.css, layout.css, DESIGN.md §4, docs/hooks.md §1, DECISIONS.md(결정 30) | 카테고리가 목록 4종 오른쪽에만 있어 홈·글에서 볼 길이 없었고 페이지를 옮기면 자리가 바뀌었다. **레일 페이지의 `--page-w`를 전부 `--wrap`으로 통일한 것이 핵심** — 폭이 다르면 컨테이너 정렬이 달라져 레일이 옆으로 뛴다 |
| 2026-08-26 | 🔴 티스토리 시트가 박은 라이트 전용 색 26종을 토큰으로 덮음 — 린트 `TIS001`·`TIS002`·`HLJS001`, `data/tistory-hardcoded-colors.json` | src/styles/tistory.css·components.css·content.css, skin-qa-check, DESIGN.md §5.2b, DECISIONS.md(결정 32) | 다크에서 오픈그래프 카드 제목이 **1.00:1**로 사라지고 있었다(62곳/39편). 원인은 우리 CSS가 아니라 **특이도** — `content.css` 규칙이 `#tt-body-page`로 시작해 `.contents_style …`을 이겼다. **인라인 보정도 JS 안전망도 원리적으로 못 잡는다**: 색이 `style` 속성이 아니라 시트에 있다. 라이트에서는 12.63:1이라 한쪽 테마에서만 조용히 깨져 있었다. 구문 색은 반대로 `atom-one-light`이 우리 **뒤**에 실려 팔레트가 통째로 무효였다 |
| 2026-08-26 | 다크 팔레트 실화면 검증 — 캔버스 `#0a0a0a`, `--ink-body` `#b0b0b0`, `--font-smooth` 토큰 신설 | src/styles/tokens.css·base.css, DESIGN.md §2, DECISIONS.md(결정 33·미결 5 해결) | 파생값이던 다크 토큰을 배포본에서 처음 쟀다. **대비 수치는 라이트와 대칭인데 체감이 달랐다**(본문 8.13 ↔ 8.45) — 순검정 위 halation, light-on-dark의 얇아 보임, macOS `antialiased`의 획 가늘어짐이 겹친 것. 대비율은 하한을 지키는 도구이지 읽히는 느낌의 척도가 아니다 |
| 2026-08-26 | 프리뷰가 티스토리 시트를 **실제 순서대로** 불러오도록 — 실패 시 경고 띠, 에디터 컴포넌트 픽스처 | .claude/skills/skin-preview/scripts/render.py | 렌더러가 우리 CSS만 그려서 위 두 결함이 프리뷰에서 멀쩡해 보였다 — **통과 신호 위조 세 번째**가 될 뻔했다. `content.css`는 우리 앞, `atom-one-light`은 우리 뒤에 실어야 특이도 싸움이 재현된다. 픽스처 조립도 `replace("</div>", …, 1)`에서 "열기+알맹이+닫기"로 바꿨다 — 알맹이에 `<div>`가 생기면 첫 `</div>`가 안쪽 것이 된다 |
