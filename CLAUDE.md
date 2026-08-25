# 상쾌한기분 티스토리 스킨

`sanggi-jayg.tistory.com`의 커스텀 티스토리 스킨을 직접 제작하는 프로젝트.

**상위 규범** — 판단이 필요하면 이 둘을 먼저 본다.
- [DECISIONS.md](./DECISIONS.md) — 확정 결정 26건, 근거, 플랫폼 제약, 275편 실측, 미결 사항
- [DESIGN.md](./DESIGN.md) — 디자인 시스템 (토큰·타이포·컴포넌트·티스토리 고정 마크업 대응)

## 작업 방식

**`main`에 직접 커밋하지 않는다.** 모든 작업은 `main`에서 브랜치를 따서 시작하고 PR로 마무리한다.

```bash
git switch main && git pull            # 항상 최신 main에서 출발
git switch -c feat/home-grid           # 브랜치 생성
# … 작업 …
npm run check                          # 빌드 → 린트 → 프리뷰. 통과해야 커밋
git add -A && git commit
git push -u origin feat/home-grid
gh pr create --base main --fill-first  # 초안이 필요하면 --draft
```

**브랜치 이름** — `feat/` 기능 · `fix/` 수정 · `docs/` 문서 · `chore/` 인프라·설정. 뒤에 하이픈으로 범위를 붙인다 (`feat/dark-mode-toggle`, `fix/toc-scrollspy`).

**PR 본문에 담을 것**
- **무엇을** 바꿨는가 — 파일 나열이 아니라 결과로
- **왜** — `DECISIONS.md`의 결정 번호나 `DESIGN.md` 절을 참조
- **어떻게 확인했는가** — 린트 결과, 프리뷰에서 본 페이지, **검증하지 못한 것**
- 스킨 변경이면 프리뷰 스크린샷

### 동시 작업은 worktree로 분리한다

여러 세션이 같은 디렉터리에서 브랜치를 바꾸면 서로의 작업 트리를 밟는다. **다른 작업이 이미 돌고 있으면 worktree를 쓴다.**

Claude Code 세션에서는 `EnterWorktree` 도구를 쓴다. 직접 만들 때는:

```bash
git worktree add ../tistory-theme-<작업명> -b feat/<작업명>
cd ../tistory-theme-<작업명>
npm install                      # worktree마다 필요하다
```

끝나면 정리한다.

```bash
git worktree remove ../tistory-theme-<작업명>
```

**worktree에서 주의할 것**

| 항목 | 동작 |
|---|---|
| `node_modules/` | worktree마다 따로 설치해야 한다 (esbuild는 플랫폼 바이너리) |
| `dist/` · `_preview/` · `_workspace/` | worktree별로 독립. **충돌하지 않는다** |
| `data/*.json` | git으로 공유된다. 한쪽에서 `/blog-census`로 갱신했으면 **커밋해야** 다른 쪽이 본다 |
| 같은 브랜치 | 두 worktree에서 동시에 체크아웃할 수 없다 |

**커밋 전 필수** — `npm run check`가 통과해야 한다. 린트 오류가 남은 채로 커밋하지 않는다. 이 도메인은 조용히 실패하므로 린트가 유일한 조기 경보다.

**작업 한 사이클은 PR 생성까지가 기본이다.** 사용자가 매번 요청하지 않아도 브랜치 → 커밋 → 푸시 → PR까지 진행한다. 다만 **PR을 merge하지는 않는다** — 병합은 사용자의 판단이다. 확신이 서지 않는 변경은 `--draft`로 연다.

## 하네스: 티스토리 스킨 제작

**목표:** 치환자·고정 마크업·수동 배포라는 티스토리 제약 위에서, 조용히 실패하지 않는 스킨을 만든다.

**트리거:** 스킨 구현·수정·기능 추가 요청 시 `tistory-skin-orchestrator` 스킬을 사용하라. 치환자 질문 같은 단순 조회는 직접 응답 가능.

**이 도메인의 핵심 위험:** 티스토리에는 컴파일러가 없다. 치환자 오타는 무시되고, CSS 선택자 불일치는 에러를 내지 않으며, JS 셀렉터는 `null`을 반환하고 끝난다. **셋 다 조용히 실패한다.** 그래서 배포 전 `skin-qa-check` 린트가 필수다.

**변경 이력:**

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-08-24 | 초기 구성 — 에이전트 5, 스킬 7 | 전체 | — |
| 2026-08-25 | 브랜치·PR 작업 방식 지침 추가 | CLAUDE.md, 오케스트레이터 Phase 5 | main 직접 커밋을 막고 변경을 PR 단위로 검토하기 위해 |
| 2026-08-25 | worktree 동시 작업 지침 추가 | CLAUDE.md, .gitignore | 여러 세션이 같은 디렉터리에서 브랜치를 바꿔 서로 밟는 것을 막기 위해 |
