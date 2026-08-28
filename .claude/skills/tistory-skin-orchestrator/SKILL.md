---
name: tistory-skin-orchestrator
description: "티스토리 커스텀 스킨 제작 팀을 조율하는 오케스트레이터. 스킨 구현, 레이아웃·스타일·동작 작업, 페이지 추가, 기능 구현을 팀으로 나눠 수행한다. '스킨 만들어', '스킨 구현', '홈 만들어', '글 페이지 작업', '목차 붙여줘', '다크모드 넣어줘' 같은 초기 요청은 물론, 후속 작업 — '다시 실행', '재실행', '수정', '보완', '업데이트', '스킨 고쳐줘', '카드 디자인만 다시', '이전 결과 개선', '프리뷰 보고 고치자' — 에도 반드시 이 스킬을 사용할 것. 단순 질문(치환자가 뭐야 등)은 직접 답해도 된다."
---

# 티스토리 스킨 오케스트레이터

`sanggi-jayg.tistory.com` 커스텀 스킨을 만드는 팀을 조율한다.

## 실행 모드: 환경을 먼저 확인한다

**`TeamCreate`가 있는 환경과 없는 환경이 둘 다 있다.** 있다고 전제하면 Phase 2·3이 통째로 실행 불가가 된다
(2026-08-25 첫 실행에서 실제로 그랬다). **Phase 2 시작 전에 `ToolSearch`로 `TeamCreate`를 조회해 분기한다.**

**설정을 보고 판단하지 마라.** `.claude/settings.json`에 `teammateMode: "auto"`와
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`이 **둘 다 켜져 있어도** `TeamCreate`가 없을 수 있다.
팀은 팀원을 **터미널 페인으로 띄우는** 기능이라 붙일 터미널이 있어야 한다 — 백그라운드
잡(`CLAUDE_JOB_DIR`이 잡히는 세션)에서는 플래그가 멀쩡해도 도구가 올라오지 않는다
(2026-08-26 점검에서 확인). **설정이 아니라 도구 목록이 사실이다.**

| Phase | `TeamCreate` 있음 | 없음 |
|---|---|---|
| Phase 1 (실측, 필요 시) | 서브 에이전트 | 서브 에이전트 |
| Phase 3 (구현) | **에이전트 팀** — 마크업↔CSS↔JS가 훅으로 얽혀 실시간 조율이 품질을 좌우한다 | **서브 에이전트 파이프라인** (§Phase 3-B) |
| Phase 4 (배포 준비) | 리더 직접 | 리더 직접 |

## 팀 구성

| 팀원 | 타입 | 역할 | 주 스킬 | 출력 |
|---|---|---|---|---|
| `skin-markup` | 커스텀 | `skin.html` · `index.xml` | `/tistory-substitutions` | `src/skin.html`, `src/index.xml`, `docs/hooks.md` |
| `skin-style` | 커스텀 | `style.css` | `/tistory-substitutions` | `src/styles/*.css` |
| `skin-behavior` | 커스텀 | `script.js` | — | `src/js/*.js` |
| `skin-qa` | 커스텀 | 검증 | `/skin-qa-check`, `/skin-preview` | `_workspace/qa-report.md` |
| `blog-analyst` | 커스텀 (서브) | 실측 | `/blog-census` | `data/*.json` |
| `seo-auditor` | 커스텀 (서브) | 검색엔진에 보이는 것 | `/seo-verify-live`, `/skin-qa-check` | `_workspace/seo-report.md`, `data/seo-baseline.json` |

모든 Agent 호출에 **`model: "opus"`**를 명시한다.

---

## Phase 0: 컨텍스트 확인

0. **브랜치를 먼저 딴다** (`CLAUDE.md` 작업 방식) — `git switch main && git pull` 로 기점을
   맞춘 뒤 `git switch -c <작업 범위>` (`home-grid`, `toc-scrollspy`). `main`에서 작업하지
   않는다. 이미 작업 브랜치 위면 그대로 이어간다.
1. `_workspace/` 존재 여부 확인
2. 실행 모드 결정:
   - **미존재** → 초기 실행. Phase 1로
   - **존재 + 부분 수정 요청** ("카드만 다시", "목차 고쳐줘") → **부분 재실행.** 해당 에이전트만 호출하고 이전 산출물 경로를 프롬프트에 포함해 읽고 고치게 한다
   - **존재 + 새 방향 지시** → **새 실행.** `_workspace/`를 `_workspace_{YYYYMMDD_HHMMSS}/`로 옮기고 Phase 1로
3. `DECISIONS.md`와 `DESIGN.md`를 읽는다. **이 둘이 상위 규범이다.** 요청이 문서와 충돌하면 사용자에게 확인한다

---

## Phase 1: 실측 (조건부)

**실행 모드:** 서브 에이전트

다음 중 하나에 해당할 때만 실행한다. 아니면 건너뛴다.

- `data/posts.json`의 `crawledAt`이 30일 이상 지났다
- 사용자가 "글이 늘었다"고 했다
- 인라인색 보정 규칙이나 기본이미지 카테고리를 손대야 한다
- `data/inline-styles.json`이 없다 (린트 INL001이 검사를 건너뛴다)

```
Agent(subagent_type: "blog-analyst", model: "opus", run_in_background: false,
      prompt: "/blog-census 스킬로 전수 실측하고, 이전 수치 대비 변화와
               설계 영향(인라인색 목록·카테고리 추가)을 _workspace/census-report.md에 정리하라.")
```

---

## Phase 2: 실행 모드 분기

```
ToolSearch(query: "select:TeamCreate", max_results: 1)
```

- **나오면** → Phase 2-A(팀 구성) → Phase 3-A
- **안 나오면** → Phase 2-A를 건너뛰고 **Phase 3-B**로 간다. 사용자에게 한 줄로 알린다:
  "`TeamCreate`가 없어 서브 에이전트 파이프라인으로 진행합니다 — 병렬성과 실시간 조율이 줄어듭니다."

---

## Phase 2-A: 팀 구성 (`TeamCreate` 있을 때만)

```
TeamCreate(team_name: "tistory-skin", members: [
  { name: "skin-markup",   agent_type: "skin-markup",   model: "opus",
    prompt: "DECISIONS.md·DESIGN.md를 읽고 src/skin.html·src/index.xml을 작성하라.
             훅 계약을 docs/hooks.md에 먼저 확정하고 팀에 공표한 뒤 시작하라." },
  { name: "skin-style",    agent_type: "skin-style",    model: "opus",
    prompt: "DESIGN.md를 규범으로 src/styles/*.css를 작성하라.
             docs/hooks.md가 나올 때까지 토큰·리셋부터 작업하라." },
  { name: "skin-behavior", agent_type: "skin-behavior", model: "opus",
    prompt: "src/js/*.js를 작성하라. 생성하는 DOM의 클래스 이름은
             skin-style과 반드시 사전 합의하라." },
  { name: "skin-qa",       agent_type: "skin-qa",       model: "opus",
    prompt: "각 모듈이 완성될 때마다 즉시 검증하라. 전체 완성을 기다리지 마라." }
])
```

**작업 등록** — `TaskCreate`는 **한 번에 한 건**만 만든다. 배열도, `assignee`도, `depends_on`도 받지 않는다.
담당과 의존성은 만든 뒤 `TaskUpdate`로 붙인다. (`TaskCreate` → `{subject, description, activeForm}`,
반환된 `taskId`에 `TaskUpdate` → `{owner}` / `{addBlockedBy: [id…]}`.)

| # | subject | owner | blockedBy |
|---|---|---|---|
| 1 | 훅 계약 확정 | skin-markup | — |
| 2 | 토큰·리셋 CSS | skin-style | — |
| 3 | 공통 뼈대(head·헤더·푸터·사이드바) | skin-markup | 1 |
| 4 | 홈 그리드 마크업 | skin-markup | 1 |
| 5 | 목록·글 마크업 | skin-markup | 1 |
| 6 | 레이아웃 CSS | skin-style | 1 |
| 7 | 본문·인라인오염 CSS | skin-style | — |
| 8 | 티스토리 고정마크업 CSS | skin-style | — |
| 9 | 다크모드 토글 JS | skin-behavior | — |
| 10 | 목차·스크롤스파이 JS | skin-behavior | 5 |
| 11 | 코드 하이라이팅 JS | skin-behavior | — |
| 12 | 라이트박스·진행바·표·링크 JS | skin-behavior | — |
| 13 | 중간 검증 1 (뼈대+토큰) | skin-qa | 3, 2 |
| 14 | 중간 검증 2 (홈+목록) | skin-qa | 4, 6 |
| 15 | 최종 검증 | skin-qa | — |

**표의 `#`는 읽기용 번호지 `taskId`가 아니다.** 실제 id는 `TaskCreate`가 돌려주므로 받아서 쓴다.

```
TaskCreate(subject: "훅 계약 확정",
           description: "docs/hooks.md에 클래스·data 속성 계약을 확정하고 팀에 공표한다",
           activeForm: "훅 계약 확정 중")     → taskId 반환 (이 값을 보관한다)
TaskUpdate(taskId: <1번의 id>, owner: "skin-markup")
…
TaskUpdate(taskId: <3번의 id>, addBlockedBy: [<1번의 id>])   ← 의존성은 만든 뒤에 건다
```

> 팀원당 4~6개가 적정. 작업을 더 잘게 쪼개면 조율 오버헤드가 커진다.

---

## Phase 3-A: 구현 — 에이전트 팀

**실행 모드:** 에이전트 팀. 팀원이 공유 작업 목록에서 작업을 요청해 자체 조율한다.

### 통신 규칙

- **`skin-markup`이 가장 먼저 `docs/hooks.md`를 쓰고 `SendMessage`로 공표한다.** 나머지 둘은 이걸 받기 전엔 훅에 의존하지 않는 작업(토큰 CSS, 다크모드 토글)부터 한다
- 훅 이름이 바뀌면 markup이 **style·behavior 양쪽에 동시 통보**한다
- `skin-behavior`는 생성 DOM의 클래스를 `skin-style`과 합의한 뒤 구현한다
- `skin-qa`는 모듈 완성 알림을 받으면 즉시 검증하고, 경계면 이슈는 **양쪽 모두에게** 알린다

### 리더 모니터링

- 팀원 유휴 알림 수신 시 `TaskGet`으로 진행률 확인
- 훅 계약이 지연되면 `skin-markup`에 우선순위 재지정
- 같은 경계면 이슈가 2회 이상 반복되면 훅 계약 자체를 재검토하도록 지시

### 산출물

| 팀원 | 경로 |
|---|---|
| skin-markup | `src/skin.html`, `src/index.xml`, `docs/hooks.md` |
| skin-style | `src/styles/*.css` |
| skin-behavior | `src/js/*.js`, `_workspace/head-inline.js` |
| skin-qa | `_workspace/qa-report.md` |

---

## Phase 3-B: 구현 — 서브 에이전트 파이프라인 (`TeamCreate` 없을 때)

에이전트는 한 번 실행되고 끝난다. **"공표를 기다리며 다른 일을 한다"가 불가능하므로**
훅 계약을 만드는 쪽을 완전히 끝낸 뒤 나머지를 띄운다.

```
skin-markup (단독 선행) → docs/hooks.md 확정
        ↓ 리더가 hooks.md 내용을 프롬프트에 직접 넣어 전달
skin-style · skin-behavior (병렬, 파일 담당을 겹치지 않게 나눠서)
        ↓
skin-qa (일괄 검증)
        ↓ 실패 항목을 담당 에이전트에 되돌린다
```

**리더가 직접 져야 하는 책임 — 팀 모드에서는 팀원이 하던 일이다**

1. **훅 중계.** markup이 정한 이름을 style·behavior 프롬프트에 **그대로 복사해 넣는다.** 링크만 주지 마라
2. **파일 담당을 겹치지 않게 못박는다.** 두 에이전트가 같은 파일을 동시에 고치면 한쪽이 덮인다.
   프롬프트에 "네가 건드릴 파일은 X뿐이다. Y는 절대 건드리지 마라 — 지금 다른 에이전트가 고치고 있다"를 **명시**한다
3. **협상이 필요한 결정을 미리 내린다.** behavior가 만드는 DOM 클래스는 협상할 상대가 없으므로 훅 계약에 미리 박혀 있어야 한다.
   빠졌으면 리더가 정해서 양쪽에 같은 문장으로 전달한다
4. **incremental QA를 포기한 대가를 인정한다.** 검증이 끝에 몰리므로 경계면 어긋남이 팀 모드보다 많이 나온다.
   `skin-qa` 프롬프트에 **"서브 에이전트 모드라 경계면이 어긋났을 가능성이 높다"**를 배경으로 넣고,
   각 에이전트가 "확인 못 했다"고 남긴 항목 목록을 함께 넘긴다

**QA 프롬프트에 반드시 넣을 것** — `_workspace/qa-report.md`에 **통과 / 실패 / 미검증 3분류**로 쓰고,
**"미검증을 통과로 적지 말 것"**. 이 도메인은 조용히 실패하므로 "아마 될 것"이 가장 위험한 문장이다.

---

## Phase 4: 빌드·프리뷰·검증

1. `/skin-build` — `npm run build`
2. `/skin-preview` — 12개 페이지 렌더, 경고 확인
3. `/skin-qa-check` — 린트. **오류 0이 될 때까지 Phase 3로 되돌린다** (최대 3회). `SEO001`(반복 블록 안의 `h1`)과 `SEO002`(내부링크 치환자 **전부** 누락)도 오류다 — 일부만 빠지면 경고다
4. **다크모드를 프리뷰에서 눈으로 본다.** 린트는 규칙의 **존재**만 확인한다. 티스토리 시트와의
   특이도 싸움에서 실제로 이기는지는 계산된 색을 봐야 안다 (DESIGN.md §5.2b).
   프리뷰 하단에 주황색 경고 띠가 떠 있으면 티스토리 시트를 못 불러온 것이니 이 확인은 무효다.
5. `_workspace/qa-report.md` 최종본 확인 — **"미검증" 항목을 사용자에게 그대로 보고**

**`seo-auditor`는 여기서 팀원이 아니다.** Phase 3의 SEO 관심사는 `SEO001~005` 린트가 이미 덮으므로 팀을 5명으로 늘릴 이유가 없다. 이 에이전트는 **배포 전후**에 서브 에이전트로 부른다 — 배포 직전 `--save-baseline`, 배포 직후 `--compare`. 그때가 프로덕션 실물이 존재하는 유일한 시점이다.

---

## Phase 5: 정리

1. 팀 모드였으면 팀원 종료 요청(`SendMessage`) → `TeamDelete`. 파이프라인 모드였으면 할 일 없다
2. `_workspace/` **보존** (사후 추적용)
3. `npm run check` 통과 확인 후 커밋. **린트 오류가 남은 채로 커밋하지 않는다**
4. 사용자에게 보고: 완료 항목 · 미검증 항목 · 배포 절차(`/skin-deploy`)
5. **`/pr-review-gate` — PR 리뷰.** 커밋 뒤, 푸시 전에 돈다.
   브랜치 전체 diff를 상위 규범 충돌·조용한 결함·**검사가 이 변경을 볼 수 있는가**·
   문서 동기화 네 축으로 읽고 차단/경고/통과를 판정한다. 일반 코드 품질은 빌트인
   `/code-review`에 위임한다. **차단이 남으면 Phase 3으로 되돌린다** — 게이트가
   마커를 찍지 않으면 다음 단계의 PR 생성 명령이 훅에 막힌다.

   린트가 통과했다는 것은 이 리뷰의 **입력이지 결론이 아니다.** 이 저장소의
   검증 도구는 통과 신호를 여러 번 위조했고 전부 린트·프리뷰가 초록불이었다(횟수와 목록은 CLAUDE.md 「핵심 위험」이 정본).
6. **푸시 → PR 생성.** 사이클의 기본 종료 지점이다 (merge는 하지 않는다).
   PR 본문에 **무엇을 / 왜(`DECISIONS.md`·`DESIGN.md` 참조) / 어떻게 확인했는가 / 검증하지 못한 것**을 담는다.
   QA 리포트와 리뷰의 "미검증"·"경고" 항목을 PR에 그대로 옮긴다 — 리뷰어가 알아야 한다
7. **피드백 요청** — "결과에서 고치고 싶은 부분이 있나요? 팀 구성이나 순서에 바꿀 점이 있나요?"

---

## 데이터 흐름

```
[리더] → (조건부) blog-analyst 서브 → data/*.json
          ↓
    ToolSearch("select:TeamCreate")
          ↓
  ┌───────┴────────────────────────────────┐
  │ 있음: TeamCreate + TaskCreate          │ 없음: 파이프라인
  │  skin-markup ─hooks.md→ skin-style     │  skin-markup 완료
  │       │                    │           │      ↓ 리더가 hooks.md를 프롬프트에 복사
  │       └→ skin-behavior ←합의┘          │  skin-style ∥ skin-behavior (파일 담당 분리)
  └───────┬────────────────────────────────┘
                    ↓
                 src/**
                    ↓
              skin-qa (팀: 모듈 완성 즉시 반복 / 파이프라인: 끝에 일괄)
                    ↓
          빌드 → 프리뷰 → 린트
                    ↓
           _workspace/qa-report.md
```

---

## 에러 핸들링

| 상황 | 전략 |
|---|---|
| 팀원 1명 실패·중지 | `SendMessage`로 상태 확인 → 재시작. 재실패 시 해당 작업을 리더가 직접 수행하고 리포트에 명시 |
| 훅 계약 충돌 반복 | 리더가 개입해 이름을 확정하고 양쪽에 통보. 팀원 협상에 맡기지 않는다 |
| 린트 오류가 3회 반복해도 안 잡힘 | 사용자에게 보고하고 진행 여부 확인. 억지로 통과시키지 않는다 |
| 리뷰 게이트가 차단 판정 | Phase 3으로 되돌려 고치고 **게이트를 다시 실행**한다. 마커를 손으로 찍지 않는다 — 찍는 순간 초록불이 거짓이 되고, 다음 사람이 그것을 믿는다 |
| PR 생성이 훅에 막힘 | 리뷰를 안 했거나 리뷰 뒤 커밋이 쌓였다. 훅 메시지의 SHA 두 개를 비교하고 **새 커밋만** 리뷰한 뒤 다시 찍는다 |
| 프리뷰가 렌더링 안 됨 | **스킨이 아니라 렌더러 문제일 수 있다.** 경고를 먼저 읽고, 렌더러 결함이면 `scripts/render.py` 수정 |
| 치환자가 필요한데 없음 | 지어내지 않는다. `docs/tistory-skin-reference.txt` 확인 후, 없으면 JS 구현으로 우회하거나 사용자에게 보고 |
| `DESIGN.md`에 없는 값 필요 | 임의 결정 금지. 문서를 먼저 갱신하고 사용자에게 알린다 |

---

## 테스트 시나리오

### 정상 흐름
1. 사용자: "홈 화면부터 만들어줘"
2. Phase 0 — `_workspace/` 없음 → 초기 실행
3. Phase 1 — `data/posts.json`이 최신이라 건너뜀
4. Phase 2 — 팀 4명 + 작업 15개 등록
5. Phase 3 — markup이 훅 계약 공표 → 셋이 병렬 작업, qa가 중간 검증 2회
6. Phase 4 — 빌드 → 프리뷰 12페이지 → 린트 오류 2건 → Phase 3 복귀 → 재검증 통과
7. Phase 5 — 팀 정리, 커밋 → `/pr-review-gate` 경고 1·차단 0 → 마커 → 푸시 → PR
8. 예상 결과: `dist/skin.html` · `dist/style.css` · `dist/images/script.js` 생성, 프리뷰 12페이지 정상

### 에러 흐름
1. Phase 3에서 `skin-behavior`가 응답 없음
2. 리더가 유휴 알림 수신 → `SendMessage` 상태 확인 → 무응답
3. 재시작 시도 → 실패
4. 목차·하이라이팅 작업을 리더가 직접 수행
5. Phase 4 진행, 린트 통과
6. 최종 보고에 "라이트박스·진행바 미구현 — skin-behavior 실패" 명시
