---
name: skin-build
description: "티스토리 스킨을 배포 산출물로 빌드하는 스킬. src/의 CSS 조각과 JS 모듈을 esbuild로 묶어 dist/skin.html · dist/style.css · dist/index.xml · dist/images/script.js를 만든다. '빌드', 'build', '번들', '산출물 만들어', '컴파일', 'npm run build' 요청 시, 그리고 프리뷰나 배포 직전에 반드시 이 스킬을 사용할 것. 배포가 수동이므로 업로드할 파일 수를 최소로 유지하는 것이 이 빌드의 핵심 제약이다."
---

# 빌드 — 소스에서 배포 산출물로

티스토리 스킨은 **붙여넣는 파일 3개 + 업로드하는 파일 35개**다(`images/` 31 + 미리보기 4). 배포를 사람이 손으로 하기 때문에 이 수를 늘리지 않는다 — 그리고 31 중 30은 **이미지가 바뀐 배포에서만** 올린다.

## 산출물 규격

```
dist/
├── skin.html          ← 스킨 편집기에 붙여넣기
├── style.css          ← 스킨 편집기에 붙여넣기
├── index.xml          ← 스킨 편집기에 붙여넣기
├── preview.gif · preview256.jpg · preview560.jpg · preview1600.jpg   ← 파일 업로드 (루트로 간다. 바뀌었을 때만)
└── images/
    ├── script.js                          ← 파일 업로드 (매 배포)
    └── ph-<slug>-<light|dark>.v<N>.webp   ← 파일 업로드 30장 (이미지가 바뀐 배포에서만. N = package.json placeholderVersion)
```

**`images/`는 script.js 1 + 기본 이미지 30 = 31개다.** 더 생기면 빌드가 경고한다. 기본 이미지 말고는 `images/`에 두지 않는다 — 폰트는 CDN에서 받는다. 2026-08-27까지는 기본 이미지를 SVG 마스크로 `style.css`에 `data:` 인라인해 `images/`가 1개였다(결정 5·6 개정 전).

## 소스 구조

```
src/
├── skin.html          치환자 마크업 (그대로 복사, 치환자를 건드리지 않는다)
├── index.xml          스킨 정보
├── styles/
│   ├── tokens.css     DESIGN.md 토큰 — 라이트/다크
│   ├── base.css       리셋, 타이포, body
│   ├── layout.css     body_id별 레이아웃
│   ├── content.css    .contents_style 본문 + 인라인 오염 보정
│   ├── tistory.css    카테고리 트리 · 댓글 tt-* 오버라이드
│   └── components.css 카드 · 목차 · 코드블록 · 사이드바
├── js/
│   ├── index.js       진입점
│   ├── toc.js  code.js  theme.js  lightbox.js  progress.js  tables.js  links.js  inline-fix.js
└── assets/
    ├── placeholders/      기본 이미지 WebP 30장 (상위 14 + 기본값 1) × (light · dark). 빌드가 읽는 것은 이것뿐
    ├── placeholders-src/  원본 — 승인된 삽화 SVG 30장(결 3). AI 이미지는 같은 이름 .png로 덮어쓴다. `npm run placeholders`가 800×500 WebP로 변환. 규칙은 docs/placeholder-image-brief.md
    └── motifs/            SVG 모티프 15장 — WebP가 안 올 때의 **폴백**(data: 인라인, --ph-*-svg). 임시본(--stub)의 원료이기도. 영구 자산
```

## 빌드가 하는 일

1. **CSS 병합** — `styles/*.css`를 정해진 순서로 이어붙인다. 순서가 곧 특이도 순서이므로 임의로 바꾸지 않는다: `tokens → base → layout → content → tistory → components`
2. **기본 이미지 복사 + 변수** — `assets/placeholders/<slug>-<theme>.webp`를 `dist/images/ph-<slug>-<theme>.v<N>.webp`로 복사하고 `--ph-<slug>`를 **3블록**(`:root` 라이트 / 시스템 다크 / 명시 다크)으로 `style.css` 맨 앞에 낸다. slug마다 light·dark 한 쌍이 없거나 100KB를 넘으면 **빌드가 멈춘다** — 한쪽 테마만 점격자로 남는 실패는 에러가 없기 때문이다. 같은 slug의 `assets/motifs/<slug>.svg`는 `--ph-<slug>-svg`로 `data:` 인라인한다(다중 배경 폴백, 약 8KB). 모티프가 없어도 멈춘다
3. **JS 번들** — esbuild로 `js/index.js`부터 단일 파일로 묶는다. highlight.js는 필요한 언어만 담는다 (`python bash shell sql java kotlin go json yaml xml`)
4. **인라인 보정 CSS 생성** — `data/inline-styles.json`에서 색 17종 + 배경 11종을 읽어 **공백 유/무 두 형태**의 선택자를 만든다. 실제 마크업이 `style="color: #000000;"`(공백 있음)이라 무공백형만 쓰면 609곳 중 1곳에만 걸린다. 손으로 쓰지 않는다
5. **skin.html 복사** — 치환자가 있으므로 어떤 변환도 하지 않는다. HTML 최소화도 하지 않는다 (치환자가 깨질 수 있다)

## 명령

```bash
npm run build                  # dist/ 생성
npm run watch                  # 변경 감지 재빌드
npm run placeholders           # assets/placeholders-src/ → assets/placeholders/*.webp (원본이 바뀔 때만)
npm run placeholders -- --stub # 원본이 없는 자리를 motifs/ SVG로 채운 임시본
```

## 주의

- **`skin.html`을 minify하지 않는다.** `<s_...>` 태그를 HTML 파서가 알 수 없는 태그로 보고 재배치하거나 제거할 수 있다.
- **CSS를 minify해도 인라인 오염 보정 선택자는 보존되어야 한다.** `[style*="color:#000000"]`의 공백 처리가 minifier에 따라 달라지면 매칭이 깨진다. 확신이 없으면 minify하지 않는다 — style.css 한 장의 크기보다 정확성이 중요하다.
- **highlight.js 전체 번들(약 1MB)을 넣지 않는다.** 언어를 골라 담으면 100KB 안팎이다.
- 빌드 후 `dist/images/`에 파일이 **31개**(script.js + WebP 30)인지 확인한다. 빌드가 개수를 세어 다르면 경고한다.
- 기본 이미지를 바꿨으면 `package.json`의 `placeholderVersion`을 올린다. 파일명이 같으면 티스토리 CDN이 옛 그림을 한동안 내보낸다.

## 빌드 후

```bash
python3 .claude/skills/skin-preview/scripts/render.py   # 프리뷰
python3 .claude/skills/skin-qa-check/scripts/lint.py    # 린트
```
