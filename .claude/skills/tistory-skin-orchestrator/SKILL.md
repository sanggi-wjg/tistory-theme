---
name: tistory-skin-orchestrator
description: "티스토리 커스텀 스킨 제작 팀을 조율하는 오케스트레이터. 스킨 구현, 레이아웃·스타일·동작 작업, 페이지 추가, 기능 구현을 팀으로 나눠 수행한다. '스킨 만들어', '스킨 구현', '홈 만들어', '글 페이지 작업', '목차 붙여줘', '다크모드 넣어줘' 같은 초기 요청은 물론, 후속 작업 — '다시 실행', '재실행', '수정', '보완', '업데이트', '스킨 고쳐줘', '카드 디자인만 다시', '이전 결과 개선', '프리뷰 보고 고치자' — 에도 반드시 이 스킬을 사용할 것. 단순 질문(치환자가 뭐야 등)은 직접 답해도 된다."
---

# 티스토리 스킨 오케스트레이터

`sanggi-jayg.tistory.com` 커스텀 스킨을 만드는 팀을 조율한다.

## 실행 모드: 하이브리드

| Phase | 모드 | 이유 |
|---|---|---|
| Phase 1 (실측, 필요 시) | 서브 에이전트 | `blog-analyst` 단독 조사. 팀 통신 불필요 |
| Phase 3 (구현) | **에이전트 팀** | 마크업↔CSS↔JS가 훅으로 강하게 얽혀 있어 실시간 조율이 품질을 좌우 |
| Phase 4 (배포 준비) | 리더 직접 | 사람이 손으로 하는 절차 안내 |

## 팀 구성

| 팀원 | 타입 | 역할 | 주 스킬 | 출력 |
|---|---|---|---|---|
| `skin-markup` | 커스텀 | `skin.html` · `index.xml` | `/tistory-substitutions` | `src/skin.html`, `src/index.xml`, `_workspace/hooks.md` |
| `skin-style` | 커스텀 | `style.css` | `/tistory-substitutions` | `src/styles/*.css` |
| `skin-behavior` | 커스텀 | `script.js` | — | `src/js/*.js` |
| `skin-qa` | 커스텀 | 검증 | `/skin-qa-check`, `/skin-preview` | `_workspace/qa-report.md` |
| `blog-analyst` | 커스텀 (서브) | 실측 | `/blog-census` | `data/*.json` |

모든 Agent 호출에 **`model: "opus"`**를 명시한다.

---

## Phase 0: 컨텍스트 확인

0. **작업 공간을 먼저 잡는다** (`CLAUDE.md` 작업 방식).
   - **다른 세션이 이 저장소에서 작업 중이면 worktree로 분리한다.** `EnterWorktree` 도구를 쓰고,
     새 worktree에서는 `npm install`을 먼저 돌린다. 같은 디렉터리에서 브랜치를 바꾸면 서로 밟는다.
   - 단독 작업이면 브랜치만 딴다:
   ```bash
   git switch main && git pull
   git switch -c feat/<작업범위>
   ```
   `main`에 직접 커밋하지 않는다. 이미 작업 브랜치 위라면 그대로 이어간다.
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

## Phase 2: 팀 구성

```
TeamCreate(team_name: "tistory-skin", members: [
  { name: "skin-markup",   agent_type: "skin-markup",   model: "opus",
    prompt: "DECISIONS.md·DESIGN.md를 읽고 src/skin.html·src/index.xml을 작성하라.
             훅 계약을 _workspace/hooks.md에 먼저 확정하고 팀에 공표한 뒤 시작하라." },
  { name: "skin-style",    agent_type: "skin-style",    model: "opus",
    prompt: "DESIGN.md를 규범으로 src/styles/*.css를 작성하라.
             _workspace/hooks.md가 나올 때까지 토큰·리셋부터 작업하라." },
  { name: "skin-behavior", agent_type: "skin-behavior", model: "opus",
    prompt: "src/js/*.js를 작성하라. 생성하는 DOM의 클래스 이름은
             skin-style과 반드시 사전 합의하라." },
  { name: "skin-qa",       agent_type: "skin-qa",       model: "opus",
    prompt: "각 모듈이 완성될 때마다 즉시 검증하라. 전체 완성을 기다리지 마라." }
])
```

**작업 등록** — `TaskCreate`로 의존성과 함께 등록한다.

```
TaskCreate(tasks: [
  { title: "훅 계약 확정",        assignee: "skin-markup" },
  { title: "토큰·리셋 CSS",       assignee: "skin-style" },
  { title: "공통 뼈대(head·헤더·푸터·사이드바)", assignee: "skin-markup", depends_on: ["훅 계약 확정"] },
  { title: "홈 그리드 마크업",     assignee: "skin-markup", depends_on: ["훅 계약 확정"] },
  { title: "목록·글 마크업",       assignee: "skin-markup", depends_on: ["훅 계약 확정"] },
  { title: "레이아웃 CSS",        assignee: "skin-style",  depends_on: ["훅 계약 확정"] },
  { title: "본문·인라인오염 CSS",  assignee: "skin-style" },
  { title: "티스토리 고정마크업 CSS", assignee: "skin-style" },
  { title: "다크모드 토글 JS",     assignee: "skin-behavior" },
  { title: "목차·스크롤스파이 JS", assignee: "skin-behavior", depends_on: ["목록·글 마크업"] },
  { title: "코드 하이라이팅 JS",   assignee: "skin-behavior" },
  { title: "라이트박스·진행바·표·링크 JS", assignee: "skin-behavior" },
  { title: "중간 검증 1 (뼈대+토큰)", assignee: "skin-qa", depends_on: ["공통 뼈대(head·헤더·푸터·사이드바)", "토큰·리셋 CSS"] },
  { title: "중간 검증 2 (홈+목록)",  assignee: "skin-qa", depends_on: ["홈 그리드 마크업", "레이아웃 CSS"] },
  { title: "최종 검증",            assignee: "skin-qa" }
])
```

> 팀원당 4~6개가 적정. 작업을 더 잘게 쪼개면 조율 오버헤드가 커진다.

---

## Phase 3: 구현

**실행 모드:** 에이전트 팀. 팀원이 공유 작업 목록에서 작업을 요청해 자체 조율한다.

### 통신 규칙

- **`skin-markup`이 가장 먼저 `_workspace/hooks.md`를 쓰고 `SendMessage`로 공표한다.** 나머지 둘은 이걸 받기 전엔 훅에 의존하지 않는 작업(토큰 CSS, 다크모드 토글)부터 한다
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
| skin-markup | `src/skin.html`, `src/index.xml`, `_workspace/hooks.md` |
| skin-style | `src/styles/*.css` |
| skin-behavior | `src/js/*.js`, `_workspace/head-inline.js` |
| skin-qa | `_workspace/qa-report.md` |

---

## Phase 4: 빌드·프리뷰·검증

1. `/skin-build` — `npm run build`
2. `/skin-preview` — 8개 페이지 렌더, 경고 확인
3. `/skin-qa-check` — 린트. **오류 0이 될 때까지 Phase 3로 되돌린다** (최대 3회)
4. `_workspace/qa-report.md` 최종본 확인 — **"미검증" 항목을 사용자에게 그대로 보고**

---

## Phase 5: 정리

1. 팀원 종료 요청 (`SendMessage`) → `TeamDelete`
2. `_workspace/` **보존** (사후 추적용)
3. `npm run check` 통과 확인 후 커밋. **린트 오류가 남은 채로 커밋하지 않는다**
4. 사용자에게 보고: 완료 항목 · 미검증 항목 · 배포 절차(`/skin-deploy`)
5. **푸시 → PR 생성.** 사이클의 기본 종료 지점이다 (merge는 하지 않는다):
   ```bash
   git push -u origin <브랜치>
   gh pr create --base main --fill-first
   ```
   PR 본문에 **무엇을 / 왜(`DECISIONS.md`·`DESIGN.md` 참조) / 어떻게 확인했는가 / 검증하지 못한 것**을 담는다.
   QA 리포트의 "미검증" 항목을 PR에 그대로 옮긴다 — 리뷰어가 알아야 한다
6. **피드백 요청** — "결과에서 고치고 싶은 부분이 있나요? 팀 구성이나 순서에 바꿀 점이 있나요?"

---

## 데이터 흐름

```
[리더] → (조건부) blog-analyst 서브 → data/*.json
          ↓
       TeamCreate + TaskCreate
          ↓
   skin-markup ──hooks.md──→ skin-style
        │                        │
        └──hooks.md──→ skin-behavior ←─클래스 합의─┘
                    ↓
                 src/**
                    ↓
              skin-qa (모듈 완성 즉시, 반복)
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
6. Phase 4 — 빌드 → 프리뷰 8페이지 → 린트 오류 2건 → Phase 3 복귀 → 재검증 통과
7. Phase 5 — 팀 정리, `_workspace/qa-report.md` 보고
8. 예상 결과: `dist/skin.html` · `dist/style.css` · `dist/images/script.js` 생성, 프리뷰 8페이지 정상

### 에러 흐름
1. Phase 3에서 `skin-behavior`가 응답 없음
2. 리더가 유휴 알림 수신 → `SendMessage` 상태 확인 → 무응답
3. 재시작 시도 → 실패
4. 목차·하이라이팅 작업을 리더가 직접 수행
5. Phase 4 진행, 린트 통과
6. 최종 보고에 "라이트박스·진행바 미구현 — skin-behavior 실패" 명시
