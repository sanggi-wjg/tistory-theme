---
name: tistory-skin-orchestrator
description: "티스토리 커스텀 스킨 제작 팀을 조율하는 오케스트레이터. 스킨 구현, 레이아웃·스타일·동작 작업, 페이지 추가, 기능 구현을 팀으로 나눠 수행한다. '스킨 만들어', '스킨 구현', '홈 만들어', '글 페이지 작업', '목차 붙여줘', '다크모드 넣어줘' 같은 초기 요청은 물론, 후속 작업 — '다시 실행', '재실행', '수정', '보완', '업데이트', '스킨 고쳐줘', '카드 디자인만 다시', '이전 결과 개선', '프리뷰 보고 고치자' — 에도 반드시 이 스킬을 사용할 것. 단순 질문(치환자가 뭐야 등)은 직접 답해도 된다."
---

# 티스토리 스킨 오케스트레이터

`sanggi-jayg.tistory.com` 커스텀 스킨을 만드는 팀을 조율한다.

## 실행 모드

| Phase | 실행 모드 |
|---|---|
| Phase 1 (실측, 필요 시) | 서브 에이전트 — 결과만 한 번 받는다 |
| Phase 3 (구현) | **이름 있는 팀원** — `Agent(name:)`로 띄우고 `SendMessage`로 다시 깨운다. 마크업↔CSS↔JS가 훅으로 얽혀 있어 고치고 다시 보는 왕복이 품질을 좌우한다 |
| Phase 4 (빌드·검증) | 리더 직접 |

**`TeamCreate`·`TeamDelete`는 없다. 에이전트 팀은 형태가 바뀌어 남아 있다.** `Agent(name: "…")`로 띄운
에이전트가 곧 팀원이고(`in_process_teammate`), 팀은 따로 만들지 않으며 리더는 `team-lead`로 잡힌다.
이 동작을 켜는 것이 `.claude/settings.json`의 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`이다(공식 문서 agent-teams
기준 — 꺼서 시험하지는 않았다). **지우면 Phase 3의 전제가 꺼진다.** 예전 판은 `TeamCreate` 유무로 갈라서, 팀원 기능이 있어도
매번 한 번 돌고 끝나는 파이프라인으로 내려갔다.

2026-10-05 점검(Claude Code 2.1.289, 대화형 CLI)에서 실측한 것:

- 유휴가 된 팀원을 `SendMessage`로 깨우면 **맥락을 유지한 채** 이어간다
- 팀원끼리 직접 보낼 수 있고, 그 요약이 리더의 유휴 알림에 실려 온다. 단 팀원에게 `SendMessage`는
  **지연 도구**라 `ToolSearch("select:SendMessage")`로 불러와야 보인다 — 모르면 "통보할 수단이 없다"고 결론 낸다
- 공유 작업 목록(`TaskCreate`·`TaskUpdate`·`TaskGet`)은 **올라오지 않았다**(문서에는 있다). 작업표는 리더가 들고 간다
- 팀원을 멈추는 것은 `TaskStop`(이름으로)

**설정이 아니라 도구 목록이 사실이다.** 위는 그날의 실측이다. 플래그가 꺼졌거나 환경이 다르면 재개나
팀원 간 메시지가 안 될 수 있다. 그래도 **분기 판정을 먼저 하지 않는다** — 경로는 하나고, 안 되는 자리에서
§에러 핸들링의 대체 동작(새로 띄우기 · 리더 중계)으로 내려간다.

## 팀 구성

| 팀원 | 타입 | 역할 | 주 스킬 | 출력 |
|---|---|---|---|---|
| `skin-markup` | 커스텀 | `skin.html` · `index.xml` | `/tistory-substitutions` | `src/skin.html`, `src/index.xml`, `docs/hooks.md` |
| `skin-style` | 커스텀 | `style.css` | `/tistory-substitutions` | `src/styles/*.css` |
| `skin-behavior` | 커스텀 | `script.js` | — | `src/js/*.js` |
| `skin-qa` | 커스텀 | 검증 | `/skin-qa-check`, `/skin-preview` | `_workspace/qa-report.md` |
| `blog-analyst` | 커스텀 (서브) | 실측 | `/blog-census` | `data/*.json` |
| `seo-auditor` | 커스텀 (서브) | 검색엔진에 보이는 것 | `/seo-verify-live`, `/skin-qa-check` | `_workspace/seo-report.md`, `data/seo-baseline.json` |

**모델은 각 에이전트 정의의 frontmatter(`model:`)가 정본이다. 호출에서 `model`을 넘기지 않는다.**
호출 인자가 frontmatter보다 우선하므로, 넘기면 정의를 바꿔도 조용히 적용되지 않는다 — 두 곳에 적힌 값이 갈라지는 부류다.

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
Agent(subagent_type: "blog-analyst", run_in_background: false,
      prompt: "/blog-census 스킬로 전수 실측하고, 이전 수치 대비 변화와
               설계 영향(인라인색 목록·카테고리 추가)을 _workspace/census-report.md에 정리하라.")
```

---

## Phase 2: 작업표 — 리더가 들고 간다

공유 작업 목록이 없으므로(§실행 모드) 리더가 작업표를 `_workspace/tasks.md`에 적고 상태를 갱신한다.
대화가 요약돼도 남고, 사후에 무엇이 누구 몫이었는지 추적된다. 부분 재실행이면 해당 줄만 적는다.

| # | 작업 | 담당 | 선행 |
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

> 팀원당 4~6개가 적정. 작업을 더 잘게 쪼개면 조율 오버헤드가 커진다.

---

## Phase 3: 구현 — 이름 있는 팀원

**실행 모드:** 이름 있는 팀원(`Agent(name:)` + `SendMessage`). 리더가 허브다 — 팀원끼리 직접 보내도 되지만,
처음 띄울 때의 지시와 결정은 리더가 쥔다.

### 띄우는 순서

```
skin-markup (단독 선행) → docs/hooks.md 확정
        ↓ 리더가 바뀐 훅 이름을 프롬프트에 직접 복사
skin-style ∥ skin-behavior ∥ skin-qa (한 메시지에서 병렬로, 파일 담당을 겹치지 않게)
        │  모듈 하나가 끝날 때마다 → skin-qa가 그 모듈만 검증
        │  실패 항목 → 담당 팀원을 같은 이름으로 깨워 되돌린다
        ↓
skin-qa 최종 검증 → _workspace/qa-report.md
```

**훅 계약이 먼저인 이유** — 훅에 기대는 작업이 계약보다 먼저 시작되면 이름이 어긋난 채 굳는다.
이번 요청에 훅을 건드리는 일이 없으면(토큰·다크모드 토글만 등) markup을 건너뛰고 바로 띄운다.

```
Agent(name: "skin-markup", subagent_type: "skin-markup",
      prompt: "DECISIONS.md·DESIGN.md를 읽고 <요청 범위>를 src/skin.html·src/index.xml에 반영하라.
               훅 계약(docs/hooks.md)을 먼저 확정하고, 새로 만들거나 바꾼 이름을 최종 보고 맨 앞에 목록으로 적어라.")
```

markup의 유휴 알림을 받은 뒤 나머지를 **한 메시지에서** 띄운다:

```
Agent(name: "skin-style", subagent_type: "skin-style",
      prompt: "<markup이 보고한 훅 이름 목록을 그대로 붙인다> …
               네가 건드릴 파일은 src/styles/*.css뿐이다. src/js/는 지금 skin-behavior가 고치고 있다.
               모듈 하나를 끝낼 때마다 skin-qa에게 SendMessage로 검증을 요청하라 —
               SendMessage는 지연 도구라 ToolSearch('select:SendMessage')로 불러온다. 못 쓰면 최종 보고에 적어라.")
Agent(name: "skin-behavior", subagent_type: "skin-behavior", prompt: "… (같은 형식, 담당은 src/js/*.js)")
Agent(name: "skin-qa", subagent_type: "skin-qa",
      prompt: "검증 요청이 올 때까지 바로 끝내고 대기하라. 요청이 오면 그 모듈만 즉시 검증하고,
               경계면 이슈는 생산자·소비자 양쪽에 SendMessage로 알려라.
               다른 팀원이 아직 고치는 중인 파일에서 난 오류는 그 팀원 몫으로 적고 넘어간다. <아래 QA 필수 문구>")
```

기준선은 따로 잡지 않는다 — 시작 시점의 트리는 통과 상태다. `main`은 CI(`check`)가 머지 조건이고, 작업 브랜치의
커밋은 `npm run check` 통과 뒤에만 쌓인다. 팀원들은 같은 작업 트리를 동시에
고치므로, 중간 검증의 `npm run check`는 남의 미완성 파일까지 본다. 그래서 위 마지막 문장이 필요하다.

### 통신 규칙

- **팀원 간 통보는 `SendMessage`다.** 지연 도구라 불러오는 법을 프롬프트에 넣는다. 못 쓰면 최종 보고에 적고 리더가 중계한다
- 훅 이름이 바뀌면 markup이 **style·behavior 양쪽에 동시 통보**한다
- `skin-behavior`는 생성 DOM의 클래스를 `skin-style`과 합의한 뒤 구현한다
- `skin-qa`는 경계면 이슈를 **양쪽 모두에게** 알린다
- 팀원끼리 보낸 메시지의 요약은 리더의 유휴 알림에 실려 온다 — 리더는 그것으로 작업표를 갱신한다

### 리더가 직접 지는 책임

1. **훅 중계.** markup이 정한 이름을 style·behavior 프롬프트에 **그대로 복사해 넣는다.** 링크만 주지 마라
2. **파일 담당을 겹치지 않게 못박는다.** 팀원은 같은 작업 트리를 쓴다 — 두 명이 같은 파일을 동시에 고치면 한쪽이 덮인다.
   프롬프트에 "네가 건드릴 파일은 X뿐이다. Y는 절대 건드리지 마라 — 지금 다른 팀원이 고치고 있다"를 **명시**한다
3. **협상이 길어지면 리더가 정한다.** behavior가 만드는 DOM 클래스는 훅 계약에 미리 박혀 있는 것이 가장 좋다.
   빠졌는데 합의가 한 번에 안 나면 리더가 정해서 양쪽에 같은 문장으로 전달한다
4. **되돌릴 때는 같은 이름으로 깨운다.** `SendMessage({to: "skin-style"})` — 새로 띄우면 앞서 읽은 맥락을 잃는다
5. **훅 계약이 지연되면** markup에 우선순위를 다시 준다. 같은 경계면 이슈가 2회 이상 반복되면 훅 계약 자체를 재검토시킨다

**QA 프롬프트에 반드시 넣을 것** — `_workspace/qa-report.md`에 **통과 / 실패 / 미검증 3분류**로 쓰고,
**"미검증을 통과로 적지 말 것"**. 이 도메인은 조용히 실패하므로 "아마 될 것"이 가장 위험한 문장이다.
각 팀원이 "확인 못 했다"고 남긴 항목 목록도 함께 넘긴다.

### 산출물

| 팀원 | 경로 |
|---|---|
| skin-markup | `src/skin.html`, `src/index.xml`, `docs/hooks.md` |
| skin-style | `src/styles/*.css` |
| skin-behavior | `src/js/*.js` (다크모드 초기화 스니펫은 `src/skin.html`의 `head-inline` 블록이 정본 — 바꿀 때 skin-markup에게 교체를 요청) |
| skin-qa | `_workspace/qa-report.md` |

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

1. 더 쓸 일이 없는 팀원은 `TaskStop`(이름)으로 멈춘다. 유휴로 두면 세션이 끝날 때까지 메시지를 받는다
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
    작업표 → _workspace/tasks.md
          ↓
    skin-markup (이름 있는 팀원) → docs/hooks.md
          ↓ 리더가 훅 이름을 프롬프트에 복사
    skin-style ∥ skin-behavior ∥ skin-qa (한 메시지에서)
          │   style·behavior ──모듈 완성──→ qa ──경계면 이슈──→ 양쪽
          │   리더 ←── 유휴 알림(팀원 간 메시지 요약 포함)
          │   실패 → 리더가 같은 이름으로 깨워 되돌림
          ↓
       src/**
          ↓
    빌드 → 프리뷰 → 린트
          ↓
    _workspace/qa-report.md
```

---

## 에러 핸들링

| 상황 | 전략 |
|---|---|
| 팀원 1명 실패·중지 | `SendMessage`로 상태 확인 → 무응답이면 같은 정의를 **새 이름**(`skin-behavior-2`)으로 띄우고 이전 산출물 경로와 작업표의 해당 줄을 프롬프트에 넣는다. 재실패 시 해당 작업을 리더가 직접 수행하고 리포트에 명시 |
| 같은 이름으로 깨워지지 않는다 (환경 차이) | 새로 띄우고 이전 산출물 경로를 넘긴다 — 맥락은 잃지만 산출물은 남아 있다. 이후 그 단계는 한 번 돌고 끝나는 서브 에이전트로 본다 |
| 팀원이 "통보할 수단이 없다"고 보고 | `SendMessage`가 지연 도구라는 것을 몰랐다. 프롬프트에 불러오는 법을 넣었는지 확인한다. 정말 못 쓰는 환경이면 최종 보고 → **리더가 중계**한다. 훅 이름은 리더가 상대 프롬프트에 그대로 복사해 넣는다 |
| 훅 계약 충돌 반복 | 리더가 개입해 이름을 확정하고 양쪽에 통보. 팀원 협상에 맡기지 않는다 |
| 린트 오류가 3회 반복해도 안 잡힘 | 사용자에게 보고하고 진행 여부 확인. 억지로 통과시키지 않는다 |
| 리뷰 게이트가 차단 판정 | Phase 3으로 되돌려 고치고 **게이트를 다시 실행**한다. 마커를 손으로 찍지 않는다 — 찍는 순간 초록불이 거짓이 되고, 다음 사람이 그것을 믿는다 |
| PR 생성이 훅에 막힘 | 리뷰를 안 했거나, 리뷰 뒤 커밋이 쌓였거나, **마커 기록과 PR 생성을 한 명령에 묶었다.** 훅 메시지의 SHA 두 개를 비교하고 **새 커밋만** 리뷰한 뒤 다시 찍는다. 묶었으면 마커만 따로 찍고 다시 연다(`/pr-review-gate` 5단계) |
| 프리뷰가 렌더링 안 됨 | **스킨이 아니라 렌더러 문제일 수 있다.** 경고를 먼저 읽고, 렌더러 결함이면 `.claude/skills/skin-preview/scripts/render.py` 수정 |
| 치환자가 필요한데 없음 | 지어내지 않는다. `docs/tistory-skin-reference.txt` 확인 후, 없으면 JS 구현으로 우회하거나 사용자에게 보고 |
| `DESIGN.md`에 없는 값 필요 | 임의 결정 금지. 문서를 먼저 갱신하고 사용자에게 알린다 |

---

## 테스트 시나리오

### 정상 흐름
1. 사용자: "홈 화면부터 만들어줘"
2. Phase 0 — `_workspace/` 없음 → 초기 실행
3. Phase 1 — `data/posts.json`이 최신이라 건너뜀
4. Phase 2 — 작업 15개를 `_workspace/tasks.md`에
5. Phase 3 — markup이 훅 계약 확정 → 리더가 이름을 복사해 style·behavior·qa를 한 메시지에서 띄움 →
   qa가 모듈마다 검증(중간 검증 2회), 경계면 이슈 1건은 qa가 style·behavior 양쪽에 직접 통보 →
   리더는 유휴 알림으로 작업표 갱신
6. Phase 4 — 빌드 → 프리뷰 12페이지 → 린트 오류 2건 → 담당 팀원을 **같은 이름으로** 깨워 되돌림 → 재검증 통과
7. Phase 5 — 팀원 `TaskStop`, 커밋 → `/pr-review-gate` 경고 1·차단 0 → 마커 → (별도 명령으로) 푸시 → PR
8. 예상 결과: `dist/skin.html` · `dist/style.css` · `dist/images/script.js` 생성, 프리뷰 12페이지 정상

### 에러 흐름
1. Phase 3에서 `skin-behavior`가 응답 없음
2. 리더가 `SendMessage`로 상태 확인 → 무응답
3. `skin-behavior-2`로 새로 띄우고 이전 산출물 경로를 넘김 → 실패
4. 목차·하이라이팅 작업을 리더가 직접 수행
5. Phase 4 진행, 린트 통과
6. 최종 보고에 "라이트박스·진행바 미구현 — skin-behavior 실패" 명시
