// 인라인색 JS 안전망 — DESIGN.md §5.2 끝줄
//
// 기존 글 275편에 박힌 인라인 색은 빌드가 data/inline-styles.json에서 만든 CSS가 덮는다.
// 이 모듈은 그 열거 목록에 없는 색(앞으로 쓸 새 글)만 상대한다.
//
// 동작 원리: CSS 보정은 !important라 이미 계산된 색에 반영되어 있다.
// 따라서 "계산된 색과 실제 배경의 대비"만 보면, 보정이 먹은 색은 자연히 통과하고
// 목록에 없는 색만 걸린다. 어느 색이 목록에 있는지 JS가 알 필요가 없다.
//
// 걸린 색은 지우기만 한다(부모에서 물려받게). 새 색을 칠하지 않는다 —
// 미디어쿼리·data-theme 밖에서 색을 처음 정의하지 않는다는 규칙과 같은 이유다.

import { contentRoots, onMediaChange } from './util.js'

// 3.0 미만 = 큰 글씨조차 읽기 어려운 수준. 의도가 있는 낮은 채도색까지
// 걷어내지 않도록 AA(4.5)가 아니라 "확실히 깨진 것"만 자른다.
const MIN_CONTRAST = 3

/** 'rgb(r, g, b)' / 'rgba(r, g, b, a)' → [r,g,b,a]. 그 밖의 표기는 null. */
function parseColor(v) {
  if (!v) return null
  const m = /^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)(?:[\s,/]+([\d.%]+))?\s*\)$/i.exec(v.trim())
  if (!m) return null
  let a = 1
  if (m[4] != null) a = m[4].indexOf('%') > -1 ? parseFloat(m[4]) / 100 : parseFloat(m[4])
  return [parseFloat(m[1]), parseFloat(m[2]), parseFloat(m[3]), isNaN(a) ? 1 : a]
}

/** WCAG 상대 휘도. */
function luminance(c) {
  const ch = [c[0], c[1], c[2]].map(function (v) {
    const s = v / 255
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
  })
  return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]
}

function contrast(fg, bg) {
  const a = luminance(fg)
  const b = luminance(bg)
  return a > b ? (a + 0.05) / (b + 0.05) : (b + 0.05) / (a + 0.05)
}

/** 반투명 전경을 배경 위에 합성한다. */
function flatten(fg, bg) {
  if (fg[3] >= 1) return fg
  const a = fg[3]
  return [fg[0] * a + bg[0] * (1 - a), fg[1] * a + bg[1] * (1 - a), fg[2] * a + bg[2] * (1 - a), 1]
}

/** OS가 다크인가. matchMedia가 없으면 라이트로 본다(기존 동작). */
function systemDark() {
  try {
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  } catch (e) {
    return false
  }
}

/** 실제로 뒤에 깔린 색. 불투명한 배경을 만날 때까지 조상을 거슬러 오른다. */
function effectiveBackground(el) {
  let node = el
  let acc = null
  while (node && node.nodeType === 1) {
    const c = parseColor(getComputedStyle(node).backgroundColor)
    if (c && c[3] > 0) {
      acc = acc ? flatten(acc, c) : c
      if (acc[3] >= 1) return acc
    }
    node = node.parentElement
  }
  // 전부 투명이면 캔버스를 추정한다. 다크에서 흰색으로 잘못 보는 것을 막는다.
  //
  // ⚠ data-theme만 보면 안 된다. **stamp 없음 + 시스템 다크**가 저장된 선택이 없는
  //    첫 방문자의 기본 상태이고, 거기서 속성은 null이다. theme.js의 current()와
  //    같은 판단을 해야 한다 — 세 상태 중 하나를 빠뜨리는 실수를 이 프로젝트에서
  //    이미 두 번 했다(DESIGN.md §8.1).
  const stamped = document.documentElement.getAttribute('data-theme')
  const dark = stamped === 'dark' || (stamped !== 'light' && systemDark())
  const fallback = dark ? [0, 0, 0, 1] : [255, 255, 255, 1]
  return acc ? flatten(acc, fallback) : fallback
}

const originals = new Map() // el → { color, backgroundColor } (손대기 전의 인라인 값)

function remember(el) {
  if (originals.has(el)) return
  originals.set(el, { color: el.style.color, backgroundColor: el.style.backgroundColor })
}

function restoreAll() {
  originals.forEach(function (v, el) {
    el.style.color = v.color
    el.style.backgroundColor = v.backgroundColor
  })
}

function fix(el) {
  const style = getComputedStyle(el)
  const fg = parseColor(style.color)
  if (!fg) return

  let bg = effectiveBackground(el)
  if (contrast(flatten(fg, bg), bg) >= MIN_CONTRAST) return

  // ① 인라인 배경이 원인일 수 있다 (다크에서 흰 상자, 라이트에서 검은 상자)
  if (el.style.backgroundColor) {
    remember(el)
    el.style.backgroundColor = ''
    bg = effectiveBackground(el)
    if (contrast(flatten(fg, bg), bg) >= MIN_CONTRAST) return
  }

  // ② 그래도 안 보이면 인라인 글자색을 지운다 → 본문 색을 물려받는다
  if (el.style.color) {
    remember(el)
    el.style.color = ''
  }
}

function run() {
  contentRoots().forEach(function (root) {
    Array.prototype.slice.call(root.querySelectorAll('[style]')).forEach(function (el) {
      const s = el.getAttribute('style') || ''
      if (s.indexOf('color') === -1) return // color / background-color 둘 다 걸린다
      try {
        fix(el)
      } catch (e) {
        /* 요소 하나가 실패해도 나머지는 본다 */
      }
    })
  })
}

export default function initInlineFix() {
  run()

  // 테마가 바뀌면 판단 근거가 통째로 바뀐다. 원래 값으로 되돌린 뒤 다시 계산한다.
  // (지우기만 하는 모듈이라 되돌릴 수 있게 원본을 들고 있는다.)
  function recompute() {
    restoreAll()
    run()
  }

  document.addEventListener('skin:theme', recompute) // theme.js의 토글
  try {
    onMediaChange(window.matchMedia('(prefers-color-scheme: dark)'), recompute) // 시스템 변경
  } catch (e) {
    /* matchMedia 없음 — 토글만 반응한다 */
  }
}
