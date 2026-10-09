// 공지 본문 래퍼가 두 겹일 때 notice.js가 바깥 것을 떼는가 — 이슈 #112.
//
//   node scripts/test-notice-unwrap.mjs
//
// skin.html이 .notice-body에 contents_style을 처음부터 달고(린트 BND012), 티스토리가 안쪽에
// 래퍼를 달아 오면 notice.js가 바깥 것을 뗀다(hooks.md §5.7). 떼지 못하면 contentRoots()가 같은
// 본문을 두 번 내고, 루트마다 click 리스너를 거는 lightbox.js가 이미지 하나에 라이트박스를 두 번 연다.
// 그런데 화면 기하는 같아서(안쪽 래퍼가 같은 시트를 받는다) 프리뷰를 봐도, `npm run check`를 돌려도
// 신호가 없었다 — notice.js의 classList.remove를 지워도 초록불이었다.
//
// 브라우저 단계는 미뤄 둔 상태라(2026-10-07 사용자 판단) 브라우저 없이 본다. 두 가지다.
//   ① 사본이 아니라 src/js/notice.js를 그대로 import해, 프리뷰가 낸 **실제 공지 마크업**을 최소 DOM으로
//      옮겨 돌린다. JS 뒤에 겹친 본문 루트가 0이고, 그릇마다 본문 루트가 하나 있는지 본다.
//   ② 프리뷰가 두 경우(래퍼 없음·안쪽 래퍼)를 **계속 그리는지** 본다. 한쪽만 그리면 ①이 다른 쪽
//      경로를 시험하지 않고 초록불을 켠다 — #97 전의 픽스처가 정확히 그랬다(래퍼 없는 쪽만).
//
// 프리뷰 산출물(_preview/pages)을 읽으므로 `npm run check`에서 preview:only **뒤**에 돈다.
// 없으면 통과가 아니라 실패다.
import { readFileSync, existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import initNotice from '../src/js/notice.js'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const PAGES = ['index', 'page', 'page_toc']

/* ── 최소 DOM — notice.js가 쓰는 것만: document.querySelectorAll · el.querySelector · el.classList ── */
function el(classes, children = []) {
  const set = new Set(classes)
  const node = {
    children,
    classList: {
      contains: (c) => set.has(c),
      add: (c) => set.add(c),
      remove: (c) => set.delete(c),
    },
    // 자손 전체에서 찾는다 — 자기 자신은 제외(DOM의 querySelector와 같다). '.x' 꼴만 쓴다
    querySelector(sel) {
      return descendants(node).find((n) => n.classList.contains(sel.slice(1))) || null
    },
  }
  return node
}
const descendants = (n) => n.children.flatMap((c) => [c, ...descendants(c)])

/* 프리뷰 HTML의 공지 본문 그릇 → 최소 DOM. 그릇의 class와, 그 안에서 class 속성을 가진 요소들을 자손으로 옮긴다. */
function noticeBodies(html) {
  const out = []
  for (const m of html.matchAll(/<div class="([^"]*\bnotice-body\b[^"]*)">([\s\S]*?)<\/article>/g)) {
    const inner = [...m[2].matchAll(/<[a-z][^>]*\bclass="([^"]*)"/g)].map((x) => el(x[1].split(/\s+/)))
    out.push(el(m[1].split(/\s+/), inner))
  }
  return out
}

let fails = 0
const ok = (cond, msg) => {
  console.log((cond ? '  ✅  ' : '  ❌  ') + msg)
  if (!cond) fails++
}

for (const page of PAGES) {
  const file = join(ROOT, '_preview', 'pages', page + '.html')
  if (!existsSync(file)) {
    ok(false, `${page} — 프리뷰가 없다(${file}). npm run preview:only 뒤에 돈다`)
    continue
  }
  const bodies = noticeBodies(readFileSync(file, 'utf8'))
  const wrapped = bodies.filter((b) => b.querySelector('.contents_style')).length
  // ② 두 경우를 다 그리는가
  ok(bodies.length >= 2 && wrapped >= 1 && wrapped < bodies.length,
    `${page} — 픽스처가 두 경우를 그린다(그릇 ${bodies.length} · 안쪽 래퍼 ${wrapped})`)
  // 서버 HTML 그대로 — 그릇마다 contents_style이 있다(BND012가 skin.html에서 보는 것의 결과)
  ok(bodies.every((b) => b.classList.contains('contents_style')),
    `${page} — JS 전 그릇이 모두 contents_style을 단다`)

  // ① notice.js를 그대로 돌린다
  const prev = globalThis.document
  globalThis.document = { querySelectorAll: (sel) => (sel === '.notice-body' ? bodies : []) }
  try {
    initNotice()
  } finally {
    globalThis.document = prev
  }
  const nested = bodies.filter((b) => b.classList.contains('contents_style') && b.querySelector('.contents_style'))
  const rootless = bodies.filter((b) => !b.classList.contains('contents_style') && !b.querySelector('.contents_style'))
  ok(nested.length === 0, `${page} — JS 뒤 겹친 본문 루트 0 (${nested.length})`)
  ok(rootless.length === 0, `${page} — JS 뒤 그릇마다 본문 루트가 하나 (없는 그릇 ${rootless.length})`)
}

console.log(fails ? `\n실패 ${fails}건` : '\n실패 0건')
process.exit(fails ? 1 : 0)
