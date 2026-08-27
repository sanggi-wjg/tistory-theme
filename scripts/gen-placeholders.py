"""상위 카테고리 기본 이미지의 **모티프** SVG를 만든다.

2026-08-27까지는 이 SVG가 곧 기본 이미지였다(CSS 마스크, 결정 5·6 구판). 지금 기본 이미지는
`src/assets/placeholders/<slug>-{light,dark}.webp` 래스터 30장이고(결정 46), 이 SVG는 두 곳에 쓰인다.
  1. **폴백** — 빌드가 `--ph-<slug>-svg`로 data: 인라인하고 CSS 다중 배경의 아래 겹에 깐다.
     WebP가 404·네트워크 실패면 이것이 드러난다(DESIGN.md §6.2). 그래서 영구 자산이다.
  2. 임시 래스터의 원료 — `scripts/prep-placeholders.mjs --stub`가 테마 색으로 감싸 래스터화한다.
새 slug를 더하면 여기에도 모티프를 그린다 — 없으면 빌드가 멈춘다.

색은 #000 고정이다. 임시 래스터를 만들 때 prep 스크립트가 토큰 색으로 바꿔 넣는다.
KEY가 곧 slug다 — `arch` → `arch-light.webp` → `--ph-arch`. DESIGN.md §6.2의 선택자와
어긋나면 카드가 조용히 --ph-default로 떨어진다.

    python3 scripts/gen-placeholders.py
"""
import os

OUT = os.path.join("src", "assets", "motifs")

HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 200" '
        'fill="none" stroke-linecap="round" stroke-linejoin="round">')

MOTIF = {
# 인프라 — 랙 유닛 3단 + 좌측 연결선
"infra": '<g stroke="#000" stroke-width="1.5">'
    '<rect x="176" y="46" width="116" height="30" rx="3"/>'
    '<rect x="176" y="86" width="116" height="30" rx="3"/>'
    '<rect x="176" y="126" width="116" height="30" rx="3"/>'
    '<path d="M140 61h30M140 101h30M140 141h30M140 61v80"/>'
    '<path d="M262 55v12M272 55v12M262 95v12M272 95v12M262 135v12M272 135v12"/></g>'
    '<g fill="#000"><circle cx="192" cy="61" r="2.8"/><circle cx="192" cy="101" r="2.8"/>'
    '<circle cx="192" cy="141" r="2.8"/></g>',

# Kotlin·Java — UML 클래스 박스 (이름/필드/메서드).
# Kotlin 마크의 세 삼각형을 먼저 시도했는데, 외곽선이 가운데서 만나 X자로 읽혔다.
# 채우면 다른 모티프보다 무거워져서 의미가 더 정확한 쪽으로 바꿨다.
# 개발 도구(터미널 창)와 같은 사각형 계열이지만, 점 3개+꺾쇠 대신
# 전폭 구분선 2개와 짧은 텍스트 줄로 실루엣이 갈린다.
"jvm": '<g stroke="#000" stroke-width="1.5">'
    '<rect x="158" y="50" width="140" height="100" rx="4"/>'
    '<path d="M158 78h140M158 106h140"/>'
    '<path d="M176 66h104"/>'
    '<path d="M176 94h76"/>'
    '<path d="M176 122h88M176 136h58"/></g>',

# Python — 들여쓰기 막대. 파이썬의 표식은 들여쓰기다
"python": '<g fill="#000">'
    '<rect x="150" y="48" width="130" height="9" rx="4.5"/>'
    '<rect x="168" y="72" width="104" height="9" rx="4.5"/>'
    '<rect x="186" y="96" width="82" height="9" rx="4.5"/>'
    '<rect x="186" y="120" width="60" height="9" rx="4.5"/>'
    '<rect x="168" y="144" width="96" height="9" rx="4.5"/></g>'
    '<g stroke="#000" stroke-width="1.5" opacity=".55"><path d="M160 68v92"/></g>',

# PHP — </> . 잠정 카테고리라 표식도 단순하게 둔다 (DECISIONS.md 결정 27)
"php": '<g stroke="#000" stroke-width="2.2">'
    '<path d="M190 64l-30 36 30 36"/><path d="M258 64l30 36-30 36"/>'
    '<path d="M236 56l-26 88"/></g>',

# 아키텍처 — 시스템 다이어그램
"arch": '<g stroke="#000" stroke-width="1.5">'
    '<rect x="192" y="38" width="76" height="36" rx="4"/>'
    '<rect x="146" y="122" width="66" height="36" rx="4"/>'
    '<rect x="248" y="122" width="66" height="36" rx="4"/>'
    '<path d="M230 74v24M179 98h102M179 98v24M281 98v24"/></g>',

# 데이터베이스 — 3단 실린더
"db": '<g stroke="#000" stroke-width="1.5"><ellipse cx="224" cy="54" rx="56" ry="16"/>'
    '<path d="M168 54v30c0 8.8 25.1 16 56 16s56-7.2 56-16V54"/>'
    '<path d="M168 90v30c0 8.8 25.1 16 56 16s56-7.2 56-16V90"/>'
    '<path d="M168 126v20c0 8.8 25.1 16 56 16s56-7.2 56-16v-20"/></g>',

# 네트워크 — 허브와 스포크
"net": '<g stroke="#000" stroke-width="1.5"><circle cx="224" cy="98" r="16"/>'
    '<path d="M224 82V52M224 114v30M208 98h-34M240 98h34'
    'M212 86l-22-22M236 86l22-22M212 110l-22 22M236 110l22 22"/></g>'
    '<g fill="#000"><circle cx="224" cy="48" r="4.2"/><circle cx="224" cy="148" r="4.2"/>'
    '<circle cx="170" cy="98" r="4.2"/><circle cx="278" cy="98" r="4.2"/>'
    '<circle cx="186" cy="60" r="4.2"/><circle cx="262" cy="60" r="4.2"/>'
    '<circle cx="186" cy="136" r="4.2"/><circle cx="262" cy="136" r="4.2"/></g>',

# 보안 — 방패와 열쇠구멍
"sec": '<g stroke="#000" stroke-width="1.5">'
    '<path d="M224 32l52 19v43c0 31-21 52-52 64-31-12-52-33-52-64V51z"/>'
    '<circle cx="224" cy="94" r="10"/><path d="M224 104v18"/></g>',

# AI — 3층 신경망. 간선은 opacity로 물린다
"ai": '<g stroke="#000" stroke-width="1.1" opacity=".55">'
    '<path d="M162 66l54-24M162 66l54 24M162 66l54 58M162 134l54-92M162 134l54 24'
    'M162 134l54 58M216 42l54 24M216 42l54 58M216 90l54-24M216 90l54 58'
    'M216 124l54-58M216 124l54 24M216 158l54-58M216 158l54 24"/></g>'
    '<g fill="#000"><circle cx="162" cy="66" r="5"/><circle cx="162" cy="134" r="5"/>'
    '<circle cx="216" cy="42" r="5"/><circle cx="216" cy="90" r="5"/>'
    '<circle cx="216" cy="124" r="5"/><circle cx="216" cy="158" r="5"/>'
    '<circle cx="270" cy="66" r="5"/><circle cx="270" cy="132" r="5"/></g>',

# 코드 품질 — 중괄호 안의 정돈된 줄과 체크
"quality": '<g stroke="#000" stroke-width="1.9">'
    '<path d="M186 44c-13 0-15 6-15 17v14c0 11-4 15-11 15 7 0 11 4 11 15v14c0 11 2 17 15 17"/>'
    '<path d="M262 44c13 0 15 6 15 17v14c0 11 4 15 11 15-7 0-11 4-11 15v14c0 11-2 17-15 17"/></g>'
    '<g stroke="#000" stroke-width="1.5"><path d="M196 78h56M196 96h38"/>'
    '<path d="M196 118l11 11 21-23"/></g>',

# Go — 채널. 양방향 화살표가 든 파이프
"go": '<g stroke="#000" stroke-width="1.5"><rect x="148" y="68" width="152" height="64" rx="32"/>'
    '<path d="M180 88h88m-16-9 16 9-16 9"/><path d="M268 112h-88m16 9-16-9 16-9"/></g>',

# 알고리즘 — 정렬된 막대. 세로라 다른 막대 모티프와 겹치지 않는다
"algo": '<g fill="#000"><rect x="152" y="128" width="17" height="28" rx="3"/>'
    '<rect x="177" y="112" width="17" height="44" rx="3"/>'
    '<rect x="202" y="92" width="17" height="64" rx="3"/>'
    '<rect x="227" y="74" width="17" height="82" rx="3"/>'
    '<rect x="252" y="58" width="17" height="98" rx="3"/>'
    '<rect x="277" y="42" width="17" height="114" rx="3"/></g>',

# 개발 도구 — 터미널 창과 프롬프트
"tool": '<g stroke="#000" stroke-width="1.5">'
    '<rect x="148" y="44" width="152" height="112" rx="6"/><path d="M148 72h152"/></g>'
    '<g fill="#000"><circle cx="163" cy="58" r="3.1"/><circle cx="175" cy="58" r="3.1"/>'
    '<circle cx="187" cy="58" r="3.1"/></g>'
    '<g stroke="#000" stroke-width="1.9"><path d="M168 96l15 13-15 13"/><path d="M194 122h44"/></g>',

# 기록 — 접힌 문서
"note": '<g stroke="#000" stroke-width="1.5">'
    '<path d="M170 34h66l30 30v100a4 4 0 01-4 4h-92a4 4 0 01-4-4V38a4 4 0 014-4z"/>'
    '<path d="M236 34v30h30"/><path d="M186 88h64M186 108h64M186 128h42"/></g>',

# 14종 어디에도 안 걸리는 새 카테고리가 생겼을 때만 쓰인다. 중립적인 표식
"default": '<g stroke="#000" stroke-width="1.5" opacity=".7">'
    '<rect x="168" y="52" width="112" height="96" rx="6"/>'
    '<rect x="192" y="76" width="64" height="48" rx="4"/></g>',
}


def main():
    os.makedirs(OUT, exist_ok=True)
    total = 0
    for name, body in sorted(MOTIF.items()):
        svg = HEAD + body + "</svg>\n"
        with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as f:
            f.write(svg)
        total += len(svg)
        print(f"  {name + '.svg':<16} {len(svg):>5}B")
    print(f"\n{len(MOTIF)}장 · raw {total}B → 다음: node scripts/prep-placeholders.mjs --stub")


if __name__ == "__main__":
    main()
