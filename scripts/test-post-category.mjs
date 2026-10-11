// 글 페이지에서 레일·칩이 이 글의 카테고리를 고르는 판정 — 이슈 #163.
//
//   node scripts/test-post-category.mjs
//
// 글 페이지에는 티스토리 li.selected가 없어서, 글 머리 .entry-cat의 href로 현재 가지를 고른다.
// 레일(category.js markPostCategory)과 칩(cat-chips.js)이 같은 postCategoryHits()로 판정한다.
// 이 판정이 틀려도 화면에는 신호가 없다 — 알약이 엉뚱한 줄에 붙거나 아무 데도 안 붙을 뿐이다.
//
// 두 단계로 본다. 브라우저 단계는 미뤄 둔 상태라(2026-10-07 사용자 판단) 둘 다 브라우저 없이 돈다.
//   ① 판정 — postCategoryHits는 문자열만 받는 순수 함수다. 경로는 라이브 모양 그대로 퍼센트
//      인코딩으로 넣는다 — 디코딩을 건너뛰면 한글 경로가 안 맞는다.
//   ② 연결 — ①만 보면 markPostCategory 호출이 빠지거나 칩 쪽 연결이 끊겨도 초록불이다(1차 QA 지적).
//      그래서 initCategory·initCatChips를 **그대로** 최소 가짜 DOM에서 돌린다. 트리는 프리뷰
//      render.py build_category_list_html이 옮긴 라이브 실측 모양(앵커 안 앞뒤 공백·c_cnt·새 글 img·
//      li class="")을 손으로 다시 적었다 — 프리뷰를 돌리지 않고 도는 검사라 산출물을 읽지 않는다.
//      레일 href는 날 유니코드(프리뷰)와 퍼센트 인코딩(라이브) 두 벌, .entry-cat은 퍼센트 인코딩이다.
//
// 사본이 아니라 src/js/category.js · cat-chips.js를 그대로 import한다.
import initCategory, { postCategoryHits } from '../src/js/category.js'
import initCatChips from '../src/js/cat-chips.js'

const enc = (p) => p.split('/').map(encodeURIComponent).join('/')
const ARCH = enc('/category/아키텍처')
const ARCH_PRIN = enc('/category/아키텍처/원칙')
const ARCH_DDD = enc('/category/아키텍처/DDD')

let fails = 0
function eq(got, want, msg) {
  const ok = JSON.stringify(got) === JSON.stringify(want)
  console.log((ok ? '  ✅  ' : '  ❌  ') + msg + (ok ? '' : `\n        got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`))
  if (!ok) fails++
}

console.log('postCategoryHits — 글 페이지의 현재 가지')

eq(
  postCategoryHits(ARCH_PRIN, ARCH, [ARCH_DDD, ARCH_PRIN]),
  { top: true, subs: [1] },
  '하위 카테고리 글 — 상위 줄과 그 하위 줄 하나만 켜진다 (라이브 예: 아키텍처/원칙)'
)
eq(
  postCategoryHits(ARCH, ARCH, [ARCH_DDD, ARCH_PRIN]),
  { top: true, subs: [] },
  '상위 카테고리에 바로 속한 글 — 상위 줄만 켜지고 하위는 안 켜진다'
)
eq(
  postCategoryHits(ARCH_PRIN, enc('/category/인프라'), [enc('/category/인프라/AWS')]),
  { top: false, subs: [] },
  '다른 가지 — 아무것도 안 켜진다'
)
eq(
  postCategoryHits('/category/IT', '/category/ITSM', []),
  { top: false, subs: [] },
  '이름이 앞부분만 같은 가지(/category/IT ↔ /category/ITSM) — 경계를 /로 끊는다'
)
eq(
  postCategoryHits(enc('/category/원칙'), ARCH, [ARCH_DDD, enc('/category/원칙')]),
  { top: true, subs: [1] },
  '하위 URL이 계층 없이 와도 — 하위가 맞으면 상위도 따라 켜진다'
)
eq(
  postCategoryHits(ARCH_PRIN + '/', ARCH, [ARCH_PRIN]),
  { top: true, subs: [0] },
  '끝 / 가 붙은 경로도 같은 카테고리로 본다'
)
eq(
  postCategoryHits('', ARCH, [ARCH_PRIN]),
  { top: false, subs: [] },
  '.entry-cat이 없는 페이지(경로 빈 값) — 아무것도 안 켜진다'
)
eq(
  postCategoryHits(ARCH_PRIN, ARCH, ['', ARCH_PRIN]),
  { top: true, subs: [1] },
  'href 없는 하위 링크(빈 경로)는 건너뛴다'
)
eq(
  postCategoryHits('/category', ARCH, [ARCH_PRIN]),
  { top: false, subs: [] },
  '「분류 전체보기」 경로(/category) — 어느 가지도 켜지 않는다'
)

/* ── ② 연결 — 최소 가짜 DOM ─────────────────────────────────────────────────────────────
   category.js·cat-chips.js·util.uniqueId가 쓰는 것만 있다. 없는 API를 부르면 TypeError로 빨간불이
   된다 — 조용히 undefined를 돌려주는 것보다 낫다. */
const BASE = 'https://sanggi-jayg.tistory.com'
const VOID = new Set(['img', 'br', 'hr', 'input', 'meta', 'link'])

class Node {
  constructor() {
    this.parentNode = null
  }
  get nextSibling() {
    const sibs = this.parentNode ? this.parentNode.childNodes : []
    return sibs[sibs.indexOf(this) + 1] || null
  }
}

class Text extends Node {
  constructor(v) {
    super()
    this.nodeType = 3
    this.nodeValue = v
  }
  get textContent() {
    return this.nodeValue
  }
}

class Element extends Node {
  constructor(tag) {
    super()
    this.nodeType = tag === '#fragment' ? 11 : 1
    this.tagName = tag.toUpperCase()
    this.attrs = new Map()
    this.childNodes = []
    const self = this
    const list = () => (self.getAttribute('class') || '').split(/\s+/).filter(Boolean)
    const put = (arr) => self.setAttribute('class', arr.join(' '))
    this.classList = {
      contains: (c) => list().includes(c),
      add: (c) => list().includes(c) || put(list().concat(c)),
      remove: (c) => put(list().filter((x) => x !== c)),
      toggle: (c, force) => {
        const on = force === undefined ? !list().includes(c) : !!force
        on ? self.classList.add(c) : self.classList.remove(c)
        return on
      },
    }
    this.scrollLeft = 0
  }
  getAttribute(n) {
    return this.attrs.has(n) ? this.attrs.get(n) : null
  }
  setAttribute(n, v) {
    this.attrs.set(n, String(v))
  }
  get id() {
    return this.getAttribute('id') || ''
  }
  set id(v) {
    this.setAttribute('id', v)
  }
  get className() {
    return this.getAttribute('class') || ''
  }
  set className(v) {
    this.setAttribute('class', v)
  }
  set href(v) {
    this.setAttribute('href', v)
  }
  // 브라우저처럼 비ASCII를 퍼센트 인코딩한 경로를 낸다(Node의 URL도 같다)
  get pathname() {
    return new URL(this.getAttribute('href') || '', BASE).pathname
  }
  get children() {
    return this.childNodes.filter((n) => n.nodeType === 1)
  }
  get firstChild() {
    return this.childNodes[0] || null
  }
  get firstElementChild() {
    return this.children[0] || null
  }
  get nextElementSibling() {
    let n = this.nextSibling
    while (n && n.nodeType !== 1) n = n.nextSibling
    return n
  }
  get textContent() {
    return this.childNodes.map((n) => n.textContent).join('')
  }
  set textContent(v) {
    this.childNodes = []
    this.appendChild(new Text(v))
  }
  // 레이아웃이 없다 — 칩 줄이 넘치지 않는 것으로 친다
  get scrollWidth() {
    return 0
  }
  get clientWidth() {
    return 0
  }
  get offsetLeft() {
    return 0
  }
  get offsetWidth() {
    return 0
  }
  appendChild(n) {
    return this.insertBefore(n, null)
  }
  insertBefore(n, ref) {
    const moved = n.nodeType === 11 ? n.childNodes.splice(0) : [n]
    for (const m of moved) {
      if (m.parentNode) m.parentNode.childNodes.splice(m.parentNode.childNodes.indexOf(m), 1)
      m.parentNode = this
      const at = ref ? this.childNodes.indexOf(ref) : -1
      at < 0 ? this.childNodes.push(m) : this.childNodes.splice(at, 0, m)
    }
    return n
  }
  insertAdjacentHTML(where, html) {
    if (where !== 'beforeend') throw new Error('가짜 DOM: beforeend만 있다')
    this.appendChild(parse(html))
  }
  addEventListener() {}
  contains(n) {
    for (; n; n = n.parentNode) if (n === this) return true
    return false
  }
  descendants() {
    return this.children.flatMap((c) => [c, ...c.descendants()])
  }
  getElementsByTagName(t) {
    return this.descendants().filter((e) => e.tagName === t.toUpperCase())
  }
  querySelectorAll(sel) {
    const parts = sel.trim().split(/\s+/).map(compound)
    return this.descendants().filter((e) => matches(e, parts, this))
  }
  querySelector(sel) {
    return this.querySelectorAll(sel)[0] || null
  }
}

/* 'tag.cls.cls' 꼴 하나. 두 모듈이 쓰는 선택자가 이 꼴과 후손 결합자뿐이다. */
function compound(c) {
  const m = c.match(/^([a-z]*)((?:\.[\w-]+)*)$/i)
  if (!m) throw new Error('가짜 DOM: 모르는 선택자 ' + c)
  return { tag: m[1].toUpperCase(), cls: m[2].split('.').filter(Boolean) }
}
const one = (e, p) => (!p.tag || e.tagName === p.tag) && p.cls.every((c) => e.classList.contains(c))
function matches(e, parts, scope) {
  if (!one(e, parts[parts.length - 1])) return false
  let i = parts.length - 2
  for (let a = e.parentNode; i >= 0 && a && a !== scope.parentNode; a = a.parentNode) {
    if (a.nodeType === 1 && one(a, parts[i])) i--
  }
  return i < 0
}

function parse(html) {
  const root = new Element('#fragment')
  const stack = [root]
  const re = /<!--[\s\S]*?-->|<\/([a-z][\w-]*)\s*>|<([a-z][\w-]*)((?:\s+[^\s=>/]+(?:="[^"]*")?)*)\s*(\/?)>|([^<]+)/gi
  for (const m of html.matchAll(re)) {
    const top = stack[stack.length - 1]
    if (m[1]) {
      const at = stack.map((e) => e.tagName).lastIndexOf(m[1].toUpperCase())
      if (at > 0) stack.length = at
    } else if (m[2]) {
      const el = new Element(m[2])
      for (const a of m[3].matchAll(/([^\s=]+)(?:="([^"]*)")?/g)) el.setAttribute(a[1], a[2] === undefined ? '' : a[2].replace(/&amp;/g, '&'))
      top.appendChild(el)
      if (!m[4] && !VOID.has(m[2].toLowerCase())) stack.push(el)
    } else if (m[5]) {
      top.appendChild(new Text(m[5].replace(/&amp;/g, '&')))
    }
  }
  return root
}

function makeDocument(html) {
  const body = new Element('body')
  body.appendChild(parse(html))
  return {
    body,
    querySelector: (s) => body.querySelector(s),
    querySelectorAll: (s) => body.querySelectorAll(s),
    getElementById: (id) => body.descendants().find((e) => e.id === id) || null,
    createElement: (t) => new Element(t),
    createTextNode: (v) => new Text(v),
    createDocumentFragment: () => new Element('#fragment'),
  }
}

/* 트리 — render.py build_category_list_html의 출력 모양(2026-08-25 라이브 실측을 옮긴 것).
   encode면 href를 라이브처럼 퍼센트 인코딩하고, 아니면 프리뷰처럼 날 유니코드로 둔다.
   selected는 li.selected를 붙일 카테고리 경로(카테고리 페이지) — 프리뷰처럼 그 li 하나에만. */
const NEW_ICO =
  '<img alt="N" src="https://tistory1.daumcdn.net/tistory_admin/blogs/image/category/new_ico_1.gif" style="vertical-align:middle;padding-left:2px;"/>'
const TREE = [
  ['아키텍처', 25, [['원칙', 12], ['분산 시스템', 13]]],
  ['코드 품질', 31, [['Clean Code', 16]]],
  ['데이터베이스', 28, [['MySQL', 23]]],
  ['AI', 19, []],
]
function tree({ encode, selected = '' }) {
  const h = (p) => (encode ? enc(p) : p)
  const li = (path) => (path === selected ? '<li class="selected">' : '<li class="">')
  const out = [
    `<ul class="tt_category"><li class=""><a href="/category" class="link_tit"> 분류 전체보기 <span class="c_cnt">(103)</span> ${NEW_ICO}</a>`,
    '<ul class="category_list">',
  ]
  TREE.forEach(([top, n, subs], i) => {
    out.push(`${li(top)}<a href="${h('/category/' + top)}" class="link_item"> ${top} <span class="c_cnt">(${n})</span> ${i === 0 ? NEW_ICO : ''}</a>`)
    if (subs.length) {
      out.push('<ul class="sub_category_list">')
      for (const [s, m] of subs) {
        out.push(`${li(top + '/' + s)}<a href="${h('/category/' + top + '/' + s)}" class="link_sub_item"> ${s} <span class="c_cnt">(${m})</span> </a></li>`)
      }
      out.push('</ul>')
    }
    out.push('</li>')
  })
  out.push('</ul></li></ul>')
  return out.join('\n')
}

/* 페이지 — skin.html의 훅만: 헤더의 빈 칩 그릇, 글 머리 .entry-cat, 사이드바 .side-category .side-body */
function page({ here, entryCat, encode, selected }) {
  const head = entryCat === undefined ? '' : `<header class="entry-head"><a class="entry-cat" href="${enc(entryCat)}">${entryCat}</a></header>`
  const doc = makeDocument(
    '<header class="site-header"><nav class="cat-chips" id="cat-chips" aria-label="카테고리"></nav></header>' +
      `<article class="entry">${head}</article>` +
      `<aside><div class="side-mod side-category"><h2 class="side-title">카테고리</h2><div class="side-body">${tree({ encode, selected })}</div></div></aside>`
  )
  const prev = [globalThis.document, globalThis.window]
  globalThis.document = doc
  globalThis.window = { location: { pathname: enc(here) } }
  try {
    initCategory()
    initCatChips()
  } finally {
    ;[globalThis.document, globalThis.window] = prev
  }
  const rail = doc.querySelector('.side-category .side-body')
  const railCurrent = (v) => rail.querySelectorAll('a').filter((a) => a.getAttribute('aria-current') === v)
  const chips = doc.getElementById('cat-chips').children
  return {
    railTrue: railCurrent('true').map((a) => a.textContent.replace(/\(\d+\)/, '').trim()),
    railPage: railCurrent('page').map((a) => a.textContent.replace(/\(\d+\)/, '').trim()),
    selected: rail.querySelectorAll('li.selected').length,
    expanded: rail.querySelectorAll('li.is-expanded').length,
    ariaExpanded: rail.querySelectorAll('button').map((b) => b.getAttribute('aria-expanded')),
    toggles: rail.querySelectorAll('button').length,
    chipCurrent: chips
      .filter((c) => c.classList.contains('is-current') || c.getAttribute('aria-current'))
      .map((c) => [c.firstChild.nodeValue, c.classList.contains('is-current'), c.getAttribute('aria-current')]),
    chipCount: chips.length,
  }
}

console.log('\n연결 — 가짜 DOM에서 initCategory·initCatChips를 그대로 돌린다')

for (const encode of [false, true]) {
  const tag = encode ? '레일 href 퍼센트 인코딩(라이브)' : '레일 href 날 유니코드(프리뷰)'
  const post = page({ here: '/entry/DI-다형성', entryCat: '/category/아키텍처/원칙', encode })
  // 토글이 실제로 달렸는가 — 0이면 아래 「접힌 채」 단언이 공허하게 참이 된다
  eq(post.toggles, 3, `[${tag}] 글 페이지 — 하위가 있는 상위 3줄에 토글이 달렸다`)
  eq(post.railTrue, ['아키텍처', '원칙'], `[${tag}] 글 페이지(아키텍처/원칙) — 레일의 상위·하위 줄 링크에 aria-current="true"`)
  eq(post.railPage, [], `[${tag}] 글 페이지 — aria-current="page"는 없다(결정 63)`)
  eq([post.selected, post.expanded], [0, 0], `[${tag}] 글 페이지 — li.selected·li.is-expanded를 붙이지 않는다(결정 62)`)
  eq(post.ariaExpanded, ['false', 'false', 'false'], `[${tag}] 글 페이지 — 가지는 접힌 채(aria-expanded 전부 false)`)
  eq(post.chipCurrent, [['아키텍처', true, 'true']], `[${tag}] 글 페이지 — 상위 칩 하나만 .is-current + aria-current="true"`)

  const spaced = page({ here: '/entry/clean-code', entryCat: '/category/코드 품질/Clean Code', encode })
  eq(spaced.railTrue, ['코드 품질', 'Clean Code'], `[${tag}] 이름에 공백이 든 카테고리(%20) — 상위·하위 줄`)
  eq(spaced.chipCurrent, [['코드 품질', true, 'true']], `[${tag}] 이름에 공백이 든 카테고리 — 상위 칩`)

  const flat = page({ here: '/entry/llm', entryCat: '/category/AI', encode })
  eq(flat.railTrue, ['AI'], `[${tag}] 하위가 없는 상위 카테고리 글 — 그 줄 하나만`)
  eq(flat.chipCurrent, [['AI', true, 'true']], `[${tag}] 하위가 없는 상위 카테고리 글 — 그 칩`)

  // 카테고리 페이지 — 티스토리 selected가 있다. .entry-cat을 **일부러** 다른 카테고리로 함께 둔다:
  // 없으면 가드(트리에 .selected가 있으면 물러난다)를 지워도 postCategory()가 빈 값이라 통과해 버린다.
  const cat = page({ here: '/category/아키텍처/원칙', entryCat: '/category/AI', encode, selected: '아키텍처/원칙' })
  eq(cat.railTrue, [], `[${tag}] 카테고리 페이지 — 레일에 aria-current="true" 0개(.entry-cat이 있어도)`)
  eq(cat.railPage, ['원칙'], `[${tag}] 카테고리 페이지 — 기존 동작: 자기 링크에 aria-current="page"`)
  eq(cat.chipCurrent, [['아키텍처', true, 'true']], `[${tag}] 카테고리 페이지 — 기존 동작: 상위 칩만 켜지고 .entry-cat의 AI는 안 켜진다`)

  const home = page({ here: '/', encode })
  eq([home.railTrue, home.railPage, home.chipCurrent], [[], [], []], `[${tag}] .entry-cat이 없는 페이지(홈) — 아무것도 안 켜진다`)
  eq(home.chipCount, 5, `[${tag}] 홈 — 칩은 그대로 만든다(전체 + 상위 4)`)
}

if (fails) {
  console.log(`\n❌ ${fails}건 실패`)
  process.exit(1)
}
console.log('\n✅ 통과')
