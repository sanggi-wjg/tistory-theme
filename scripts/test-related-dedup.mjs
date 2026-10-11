// 관련 글에서 이전/다음 글과 같은 줄을 related.js가 빼는가 — 이슈 #162.
//
//   node scripts/test-related-dedup.mjs
//
// 화면에는 「같은 제목이 두 번」이라는 신호뿐이라, 중복 제거가 꺼져도 프리뷰는 멀쩡해 보인다.
// 비교의 함정은 모양이다 — 라이브는 관련 글 링크에만 `?category=<번호>`를 붙이고(2026-10-11 실측),
// 한글 슬러그는 퍼센트 인코딩으로 온다. 문자열 그대로 비교하면 하나도 안 겹쳐 아무것도 빼지 않는다.
// 브라우저 단계는 미뤄 둔 상태라(2026-10-07 사용자 판단) 브라우저 없이 본다. 세 가지다.
//   ① 경로 대조(entryPath·duplicateIndexes)를 라이브 모양의 href로 직접 친다.
//   ② 사본이 아니라 src/js/related.js를 그대로 import해, 프리뷰가 낸 **실제 글 마크업**을 최소 DOM으로
//      옮겨 돌린다. 픽스처가 라이브 모양(겹치는 줄 + 관련 글에만 쿼리 + 안 겹치는 줄)을 계속 그리는지도 본다 —
//      겹치지 않는 목록을 그리면 ②가 빼는 경로를 시험하지 않고 초록불을 켠다(#162 전의 픽스처가 그랬다).
//
//   ③ 실제로 **연결돼 있는지**. ①②는 related.js를 직접 import하므로 index.js의 safe('related', …) 한 줄을
//      지워도 초록이었다(1차 QA가 재현 — 그 번들로 프리뷰 글을 열면 관련 글 4줄이 그대로 남았다).
//      소스(index.js가 import하고 boot() 안에서 부른다)와 번들(dist/images/script.js에 '.postnav-item'이 있다 —
//      그 이름을 읽는 모듈은 related.js뿐이고, esbuild는 부르지 않는 모듈을 털어 낸다) 양쪽을 본다.
//      다른 모듈이 '.postnav-item'을 읽게 되면 번들 쪽은 무뎌진다 — 소스 쪽이 그때를 맡는다.
//
// 프리뷰 산출물(_preview/pages)과 번들(dist/)을 읽으므로 `npm run check`에서 build·preview:only **뒤**에 돈다.
// 없으면 통과가 아니라 실패다.
import { readFileSync, existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import initRelated, { entryPath, duplicateIndexes } from '../src/js/related.js'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const BASE = 'https://sanggi-jayg.tistory.com/entry/post-0'

let fails = 0
const ok = (cond, msg) => {
  console.log((cond ? '  ✅  ' : '  ❌  ') + msg)
  if (!cond) fails++
}

/* ── ① 경로 대조 ── */
// 라이브 글 「멱등성 (Idempotence)와 HTTP API 설계」 꼴의 한글 슬러그(인코딩은 여기서 만든다)
const SLUG = '/entry/' + encodeURIComponent('멱등성-Idempotence와-HTTP-API-설계')
const same = (a, b) => duplicateIndexes([a], [b], BASE).length === 1

ok(same(SLUG + '?category=1325373', SLUG), '관련 글에만 ?category= — 같은 글')
ok(same('/entry/멱등성-Idempotence와-HTTP-API-설계?category=1', SLUG), '원문 한글 ↔ 퍼센트 인코딩 — 같은 글')
ok(same(SLUG.replace(/%[0-9A-F]{2}/g, (m) => m.toLowerCase()), SLUG), '인코딩 16진 소문자 ↔ 대문자 — 같은 글')
ok(same(SLUG + '/', SLUG), '끝 / — 같은 글')
ok(same(SLUG + '#comment', SLUG), '해시 — 같은 글')
ok(same('https://sanggi-jayg.tistory.com' + SLUG + '?category=1', SLUG), '절대 URL ↔ 상대 경로 — 같은 글')
ok(!same('/entry/post-1?category=1', '/entry/post-2'), '다른 글 — 안 겹친다')
ok(!same('/entry/post-1', '/entry/post-12'), '앞부분만 같은 경로 — 안 겹친다')
ok(!same('/entry/post-0?category=1', ''), '빈 이전/다음 href는 지금 페이지로 풀리지 않는다')
ok(!same('/entry/post-0?category=1', '#'), "'#' 이전/다음 href — 안 겹친다")
ok(!same('/?category=1', '/'), '루트 경로끼리는 겹친다고 하지 않는다')
let threw = false
try {
  same('/entry/%E0%A4%A', '/entry/%E0%A4%A')
} catch (e) {
  threw = true
}
ok(!threw, '잘못된 퍼센트 인코딩에도 던지지 않는다')
ok(entryPath('/entry/a?x=1#y', BASE) === '/entry/a', "entryPath — 쿼리·해시를 뗀다 ('" + entryPath('/entry/a?x=1#y', BASE) + "')")
ok(
  JSON.stringify(duplicateIndexes(['/entry/a?c=1', '/entry/b?c=1', '/entry/c?c=1'], ['/entry/c', '/entry/a'], BASE)) === '[0,2]',
  '여럿 중 겹치는 번호만 낸다'
)

/* ── 최소 DOM — related.js가 쓰는 것만 ── */
function node(classes, attrs = {}, children = []) {
  const set = new Set(classes)
  const n = {
    classes: set,
    children,
    parentNode: null,
    hidden: false,
    getAttribute: (k) => (k in attrs ? attrs[k] : null),
    removeChild(c) {
      n.children = n.children.filter((x) => x !== c)
      c.parentNode = null
    },
    // '.x' 꼴만. 자손 전체, 자기 자신 제외
    querySelectorAll: (sel) => descendants(n).filter((d) => d.classes.has(sel.slice(1))),
    querySelector: (sel) => n.querySelectorAll(sel)[0] || null,
  }
  children.forEach((c) => (c.parentNode = n))
  return n
}
const descendants = (n) => n.children.flatMap((c) => [c, ...descendants(c)])
const norm = (h) => decodeURIComponent(h.split(/[?#]/)[0]).replace(/\/+$/, '') // 검사 쪽의 독립 정규화

function run(section, navs) {
  const prev = [globalThis.document, globalThis.window]
  globalThis.document = {
    querySelector: (sel) => (sel === '.related' ? section : null),
    querySelectorAll: (sel) => (sel === '.postnav-item' ? navs : []),
  }
  globalThis.window = { location: { href: BASE } }
  try {
    initRelated()
  } finally {
    ;[globalThis.document, globalThis.window] = prev
  }
}

function fakeSection(hrefs) {
  const lis = hrefs.map((h) => node(['related-item'], {}, [node(['related-link'], { href: h })]))
  return node(['related'], {}, [node(['related-list'], {}, lis)])
}
const navOf = (hrefs) => hrefs.map((h) => node(['postnav-item'], { href: h }))

{
  const s = fakeSection(['/entry/a?category=1', '/entry/b?category=1'])
  run(s, navOf(['/entry/a', '/entry/b']))
  ok(s.querySelectorAll('.related-item').length === 0 && s.hidden, '전부 겹치면 줄을 다 빼고 섹션을 감춘다')
}
{
  const s = fakeSection(['/entry/a?category=1', '/entry/b?category=1'])
  run(s, [])
  ok(s.querySelectorAll('.related-item').length === 2 && !s.hidden, '이전/다음이 없으면 손대지 않는다')
}
{
  const s = fakeSection(['/entry/a?category=1', '/entry/b?category=1'])
  s.children[0].children[1].children = [] // 둘째 줄의 링크가 없다
  run(s, navOf(['/entry/a', '/entry/b']))
  ok(s.querySelectorAll('.related-item').length === 1 && !s.hidden, '링크를 못 읽은 줄은 남기고 섹션도 감추지 않는다')
}

/* ── ② 프리뷰가 낸 실제 글 마크업 ── */
function fromHtml(html) {
  const sec = html.match(/<section class="related">([\s\S]*?)<\/section>/)
  const relHrefs = sec ? [...sec[1].matchAll(/<li class="related-item[^"]*">\s*<a class="related-link" href="([^"]*)"/g)].map((m) => m[1]) : []
  const navHrefs = [...html.matchAll(/<a class="postnav-item[^"]*" href="([^"]*)"/g)].map((m) => m[1])
  return { hasSection: !!sec, relHrefs, navHrefs }
}

for (const page of ['page', 'page_toc']) {
  const file = join(ROOT, '_preview', 'pages', page + '.html')
  if (!existsSync(file)) {
    ok(false, `${page} — 프리뷰가 없다(${file}). npm run preview:only 뒤에 돈다`)
    continue
  }
  const { hasSection, relHrefs, navHrefs } = fromHtml(readFileSync(file, 'utf8'))
  const navSet = new Set(navHrefs.map(norm))
  const dup = relHrefs.filter((h) => navSet.has(norm(h)))
  ok(hasSection && relHrefs.length > 0 && navHrefs.length > 0,
    `${page} — 관련 글 ${relHrefs.length}줄 · 이전/다음 ${navHrefs.length}개를 읽었다`)
  ok(dup.length > 0 && dup.length < relHrefs.length,
    `${page} — 픽스처가 겹치는 줄과 안 겹치는 줄을 함께 그린다(겹침 ${dup.length}/${relHrefs.length})`)
  ok(dup.length > 0 && dup.every((h) => /\?category=/.test(h)) && navHrefs.every((h) => !/\?/.test(h)),
    `${page} — 라이브 모양: 쿼리는 관련 글에만 붙는다`)

  const s = fakeSection(relHrefs)
  run(s, navOf(navHrefs))
  const left = s.querySelectorAll('.related-link').map((a) => a.getAttribute('href'))
  ok(left.length === relHrefs.length - dup.length && !left.some((h) => navSet.has(norm(h))),
    `${page} — JS 뒤 겹치는 줄 0, ${left.length}줄 남는다`)
  ok(!s.hidden, `${page} — 남은 줄이 있으니 섹션은 보인다`)
}

{
  // 대표이미지·관련 글·다음 글이 빈 글 — 섹션이 없어도 죽지 않는다
  const file = join(ROOT, '_preview', 'pages', 'page_bare.html')
  if (!existsSync(file)) ok(false, `page_bare — 프리뷰가 없다(${file})`)
  else {
    const { hasSection, navHrefs } = fromHtml(readFileSync(file, 'utf8'))
    let err = null
    try {
      run(hasSection ? fakeSection([]) : null, navOf(navHrefs))
    } catch (e) {
      err = e
    }
    ok(!hasSection && !err, `page_bare — 관련 글이 없는 글에서 아무 일 없이 끝난다${err ? ' (' + err.message + ')' : ''}`)
  }
}

/* ── ③ 연결 — 소스와 번들 ── */
{
  // 줄 전체가 주석인 줄과 블록 주석을 지운다 — 주석으로 꺼 둔 호출을 연결로 세지 않는다
  const src = readFileSync(join(ROOT, 'src', 'js', 'index.js'), 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .split('\n')
    .filter((l) => !/^\s*\/\//.test(l))
    .join('\n')
  const imp = src.match(/^import\s+(\w+)\s+from\s+'\.\/related\.js'/m)
  const boot = src.match(/function boot\(\)\s*\{([\s\S]*?)\n\}/)
  const called = !!(imp && boot && new RegExp("safe\\('related',\\s*" + imp[1] + '\\)').test(boot[1]))
  ok(called, "index.js — related.js를 import하고 boot() 안에서 safe('related', …)로 부른다")

  const bundle = join(ROOT, 'dist', 'images', 'script.js')
  if (!existsSync(bundle)) ok(false, `번들이 없다(${bundle}). npm run build 뒤에 돈다`)
  else {
    const n = readFileSync(bundle, 'utf8').split('.postnav-item').length - 1
    ok(n > 0, `dist/images/script.js — related.js가 번들에 들어 있다('.postnav-item' ${n}회)`)
  }
}

console.log(fails ? `\n실패 ${fails}건` : '\n실패 0건')
process.exit(fails ? 1 : 0)
