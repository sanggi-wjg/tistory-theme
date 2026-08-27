# 기본 이미지 30장 — 생성 브리프와 GPT-image 프롬프트 팩

대표이미지 없는 글의 카드 썸네일(결정 46, `DESIGN.md §6.2`). 방향은 **결 3 · 개념 일러스트 —
Clockwise 결을 스킨 토큰으로 옮긴 것**으로 확정했다(2026-08-27, 사용자 승인). 승인된 삽화 목업이
`src/assets/placeholders-src/<slug>-{light,dark}.svg`에 있고 **지금은 그것이 곧 실제 기본 이미지**다.
AI로 더 풍부한 그림을 만들면 같은 이름의 `.png`로 덮어쓴다 — 래스터가 SVG를 이긴다.

## 1. 규격

| 항목 | 값 |
|---|---|
| 비율·크기 | 16:10. 1600×1000으로 뽑는다. 변환기가 800×500 WebP로 줄인다(다른 비율은 가운데 cover 크롭) |
| 파일명 | `src/assets/placeholders-src/<slug>-light.png` · `<slug>-dark.png` |
| slug 15종 | `infra jvm python php arch db net sec ai quality go algo tool note default` |
| 용량 | 변환 뒤 장당 100KB 이하 — 넘으면 `npm run placeholders`가 실패한다 |
| 안전 영역 | 피사체는 가운데 60%(1600×1000 기준 960×600) 안에. 카드는 340px로 줄고 모서리 8px이 잘린다 |
| 없는 것 | **글자, 사람, 얼굴, 손, 로고, 마스코트, 그라디언트, 그림자, 질감, 원근** |

넣은 뒤: `npm run placeholders` → `npm run check` → 프리뷰 확인 → `package.json`의 `placeholderVersion`을
올린다 → 배포 때 30장을 `images/`에 다시 올린다(`skin-deploy` 1-c).

## 2. 스타일 바이블 — 토큰 7개, 그 밖의 색 없음

| 역할 | 토큰 | light | dark |
|---|---|---|---|
| 바탕 (이미지 전체) | `--canvas-soft` | `#fafafa` | `#121212` |
| 면 1 (종이) | `--canvas` | `#ffffff` | `#0a0a0a` |
| 뒤판 원 | `--hairline` | `#ebebeb` | `#2e2e2e` |
| 면 2 | `--hairline-strong` | `#a1a1a1` | `#454545` |
| 외곽선 | `--ink` | `#171717` | `#ededed` |
| 작은 장식 점 | `--ink-mute` | `#707070` | `#8f8f8f` |
| 강조 (한 요소) | `--link` | `#0064da` | `#3291ff` |

형태 규칙
- 외곽선은 **한 굵기** — 이미지 높이의 2.5%(1600×1000에서 약 25px). 이음은 둥글게.
- 면은 **3톤**(종이·뒤판·면 2). 그라디언트·질감·그림자 없음.
- **뒤판 원 하나** — 지름은 높이의 74%, 정중앙.
- **파랑은 한 요소** — 피사체의 5% 안팎. 두 곳에 쓰지 않는다.
- **작은 장식 셋** — 플러스 1(외곽선 색), 점 1(`--ink-mute`), 파란 점 1. 피사체 바깥 모서리에.
- **정면 구도**, 피사체 하나.

## 3. GPT-image 절차 — 30장을 한 손으로

핵심은 OpenAI 가이드의 "앵커를 확정하고, 참조로 붙이고, 유지할 것을 매번 다시 적는다"이다.
참조 이미지는 `src/assets/placeholders-src/`의 SVG를 PNG로 내보내 쓴다(브라우저에서 열어 저장하거나
`npm run placeholders`가 만든 `src/assets/placeholders/<slug>-<theme>.webp`).

### 3-1. 앵커 한 장 — `infra-light`

`infra-light.svg`(또는 webp)를 **참조 이미지로 첨부**하고 아래를 보낸다. 마음에 들 때까지 이 한 장만 다듬는다 —
여기서 굳힌 외곽선 굵기·면 톤·장식 배치가 나머지 29장의 기준이 된다.

```
Reference image attached: match its style exactly — flat vector, bold uniform dark outlines,
three flat gray tones, one large flat circle behind the subject, one small blue element,
three tiny geometric accents (a plus sign, a gray dot, a blue dot) near the corners.

Create a 16:10 image (1600x1000). Subject: {infra 주제}, front view, centered,
occupying the middle 60% of the frame.
Palette (use these and nothing else): background #fafafa, paper fill #ffffff,
backing circle #ebebeb, secondary fill #a1a1a1, outlines #171717 (about 2.5% of
image height, rounded joins), accent dot #707070, the single blue element #0064da.
No gradients, no shadows, no texture, no perspective, no text, no people, no logos.
Calm, minimal technical concept illustration for a developer blog.
```

### 3-2. 라이트 나머지 14장

앵커 결과 이미지 **와** 그 slug의 목업 SVG 둘을 첨부한다. 앵커는 스타일, 목업은 구도·피사체의 근거다.

```
Image 1 is the style anchor — keep its outline weight, three gray tones, backing circle,
accent placement and overall calm exactly. Image 2 is a rough sketch of the composition
to follow. Replace the subject with: {slug 주제}. The single blue element is: {파랑 요소}.
Everything else stays as in Image 1. Same palette, 16:10, 1600x1000, no text, no people.
```

### 3-3. 다크 15장

같은 slug의 **라이트 결과**를 첨부하고 팔레트만 바꾼다. 구도가 같아야 테마를 토글할 때 "같은 그림"으로 읽힌다.

```
Image 1 is the light version. Recreate the identical composition — same subject, same
positions, same outline weight — in the dark palette: background #121212, paper fill #0a0a0a,
backing circle #2e2e2e, secondary fill #454545, outlines #ededed, accent dot #8f8f8f,
the single blue element #3291ff. Nothing else changes. 16:10, 1600x1000, no text, no people.
```

### 3-4. 한 장마다 확인할 것

- [ ] 글자·사람·로고 없음
- [ ] 파랑이 **한 요소**뿐인가
- [ ] 장식이 플러스 1 · 점 1 · 파란 점 1인가 (더 많으면 지우라고 한다)
- [ ] 피사체가 가운데 60% 안에 있고, 뒤판 원이 정중앙인가
- [ ] 외곽선 굵기가 앵커와 같은가 (모델이 가늘게 만들려는 경향이 있다 — "thicker outlines, same as Image 1")
- [ ] 바탕이 단색 `#fafafa` / `#121212`인가 (미세한 그라디언트를 넣으면 다시)

드리프트가 보이면 그 줄을 프롬프트에 **다시 적는다**("outlines must be as thick as in Image 1"). 이어지는 대화에서
"같은 스타일로"만 쓰면 3~4장 지나며 흐려진다.

## 4. 카테고리별 주제 사전 — `{slug 주제}` · `{파랑 요소}`

상표·마스코트(고퍼, 엘리펀트, 커피잔)는 쓰지 않는다. 목업 SVG가 각 줄의 구도 스케치다.

| slug | 카테고리 | 주제 (영문 프롬프트 조각) | 파랑 요소 |
|---|---|---|---|
| infra | 인프라 | a compact server rack with three drawer units and one cable loop coming out of the middle unit | the status light on the middle unit |
| jvm | Kotlin·Java | three class-diagram boxes stacked vertically, each with a header band, joined by two small down arrows | the top box's header band |
| python | Python | five rounded horizontal bars forming an indentation staircase beside a thin vertical guide line | the fourth (shortest, most indented) bar |
| php | PHP | three overlapping web-page cards fanned to the upper right, the front card showing three short text-line strokes | a small blinking text cursor block on the front card |
| arch | 아키텍처 | one module box above two module boxes, connected by a horizontal bus line with three vertical drops | the top module box |
| db | 데이터베이스 | a three-tier database cylinder with one visible band line | a small index tab attached to the lower right of the cylinder |
| net | 네트워크 | a hub node with six straight spokes ending in small ring nodes arranged in a hexagon | the hub node |
| sec | 보안 | a rounded shield outline with a keyhole in its center | the keyhole |
| ai | AI | a small lattice of seven ring nodes in three columns joined by thin lines | the center node |
| quality | 코드 품질 | a pair of large curly braces holding a single check mark | the check mark |
| go | Go | two parallel horizontal pipes with a small parcel passing between them and a small arrow at the right end | the parcel |
| algo | 알고리즘 | seven vertical bars of increasing height on a baseline | the fourth bar |
| tool | 개발 도구 | a terminal window with a title bar of three dots, a prompt chevron and a cursor block | the cursor block |
| note | 기록 | a single notebook page with a folded top-right corner, three ruled lines and a bookmark ribbon | the bookmark ribbon |
| default | (기본값) | a rounded rectangle outline with a smaller filled rounded rectangle inside | none — this one has no blue element |

## 5. 네거티브 (텍스트 프롬프트 끝에 붙인다)

```
no text, no letters, no numbers, no watermark, no logo, no signature, no people, no faces,
no hands, no mascot, no photo, no 3D render, no gradient, no drop shadow, no texture,
no perspective, no isometric, no extra colors beyond the palette, no busy background
```

## 6. 참고

- 방향 캔버스(승인본): 라이트·다크 격자와 스타일 규칙 — 대화에서 공유한 "기본 이미지 삽화 방향" 아트팩트
- 레퍼런스: Clockwise Software IT Blog Illustrations (Anna Butenko, Behance) — 플랫 벡터·굵은 외곽선·기하·사물 은유
- OpenAI 이미지 생성 프롬프팅 가이드 — 앵커·참조·유지 목록 재기술
