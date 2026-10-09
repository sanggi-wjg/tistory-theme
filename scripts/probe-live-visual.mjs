// 라이브에서만 드러나는 화면 조건을 헤드리스 Chrome(CDP)으로 잰다 — 배포 뒤 「눈으로 본다」던 것을 숫자로.
// (이슈 #91·#92 — 결정 57 ②③, 결정 58)
//
//   node scripts/probe-live-visual.mjs [--base https://sanggi-jayg.tistory.com] [--shots <디렉터리>] [--self-test]
//   npm run probe:live
//
// 다섯을 라이트·다크에서 본다. 폭은 1440(사이드바 트리가 옆에 있는 데스크톱)과 390(헤더 규칙이 바뀌는 폰).
//   ① 홈 카드 삽화 스침(57 ②) — 대표이미지가 있는 카드(`.thumb > .thumb-img`)에서 2층 기본 이미지
//      `.thumb::before`가 그려지지 않는가. img가 lazy라 첫 페인트 뒤에 오는데, 그 사이 보이는 것은
//      이 ::before뿐이다 — 그래서 **타이밍을 재는 대신 그 층이 존재하는지를 잰다.** 로딩 시점에 상관없이
//      답이 같다. 대표이미지 없는 카드는 반대로 그려져야 한다(그래야 규칙이 「다 지운」 것이 아님을 안다).
//   ② 빈 메뉴 헤더(57 ③) — `[##_blog_menu_##]`가 `<ul></ul>`일 때 `.site-nav`가 높이 0인가. 빈 줄이 생기는 것은
//      767px 이하뿐이라(padding·border) **390이 이 항목을 지킨다** — 1440은 규칙이 빠져도 높이 0이다.
//   ③ 글 수 배지(58) — 모든 카테고리 줄에서 `.c_cnt`의 오른쪽 끝이 앵커 콘텐츠 상자의 오른쪽 끝인가.
//   ④ 새 글 표시(58, #92) — 티스토리가 앵커에 끼우는 `img`가 6×6 점이고 테두리가 `--link`이며,
//      이름 뒤·배지 앞에 있는가. **상위·하위 줄을 따로 센다** — 하위 카테고리에 새 글이 없으면 「미측」.
//   ⑤ 줄이 트리 상자를 넘지 않는다 — ③은 배지가 **제 줄의** 끝인지만 봐서, 줄 자체가 레일 밖으로 나간 것
//      (하위 줄 3px, 이슈 #122)을 통과시켰다. 스크린샷을 보고 알았다.
// 다크 실행은 바탕과 `--link`가 라이트와 달라야 한다 — 다크가 안 먹으면 모든 항목이 라이트를 두 번 잰 통과가 된다.
//
// 판정은 셋 — 통과 · 실패(exit 1) · 미측. **미측은 조건부 항목에만 쓴다**(메뉴가 비어 있지 않다, 새 글이 없다).
// 페이지를 못 열었거나 카드·메뉴·트리가 통째로 없는 것은 실패다 — 깨진 배포·바뀐 class와 「잴 것이 없다」를
// 같은 ❔로 내면 그것이 위조된 통과 신호다(docs/HARNESS.md 「핵심 위험」, 2026-10-09 코드 리뷰).
//
// `--self-test`: 라이브 페이지에 각 조건을 깨는 CSS를 주입해 **기준(주입 없음)과 다른 실패**가 나오는지
// 라이트에서 1440·390 둘 다 본다. 기준에서 이미 실패하는 항목(⑤가 #122를 고쳐 배포하기 전까지 그랬다)은 「주입하니 실패」가 아무 증거도 아니라서다.

import { spawn } from 'node:child_process'
import { existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const args = process.argv.slice(2)
const opt = (name, dflt) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt }
const BASE = opt('--base', 'https://sanggi-jayg.tistory.com').replace(/\/$/, '')
const SHOTS = opt('--shots', null)
const SELF_TEST = args.includes('--self-test')
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const CALL_TIMEOUT = 30000      // CDP 호출 하나
const RUN_TIMEOUT = 5 * 60000   // 실행 전체 — 넘으면 exit 2(판정 불가)
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const runTimer = setTimeout(() => { console.error('시간 초과 — 판정하지 못했다'); process.exit(2) }, RUN_TIMEOUT)
runTimer.unref()

// 포트는 0으로 맡기고 프로필의 DevToolsActivePort에서 읽는다 — 정한 번호를 쓰면 이미 떠 있는 다른 Chrome에
// 붙어 그것을 재고, 끝에 Browser.close로 닫아 버린다(코드 리뷰).
async function launch() {
  const profile = mkdtempSync(join(tmpdir(), 'probe-live-'))
  const cleanup = () => { try { rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 }) } catch {} }
  let proc
  try {
    proc = spawn(CHROME, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`,
      '--no-first-run', '--no-default-browser-check', '--disable-extensions', '--lang=ko-KR'], { stdio: 'ignore' })
    const spawnError = new Promise((_, rej) => proc.once('error', (e) => rej(new Error('Chrome을 띄우지 못했다: ' + e.message))))
    spawnError.catch(() => {})
    const portFile = join(profile, 'DevToolsActivePort')
    let wsUrl
    for (let i = 0; i < 75 && !wsUrl; i++) {
      await Promise.race([sleep(200), spawnError])
      if (existsSync(portFile)) {
        const [port, path] = readFileSync(portFile, 'utf8').split('\n')
        if (port && path) wsUrl = `ws://127.0.0.1:${port}${path}`
      }
    }
    if (!wsUrl) throw new Error('Chrome이 15초 안에 뜨지 않았다: ' + CHROME)
    const ws = new WebSocket(wsUrl)
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error('CDP 연결 실패')) })
    let id = 0
    const pending = new Map()
    const listeners = []
    ws.onmessage = (m) => {
      const msg = JSON.parse(m.data)
      if (msg.id && pending.has(msg.id)) {
        const { res, rej, t } = pending.get(msg.id)
        clearTimeout(t)
        pending.delete(msg.id)
        msg.error ? rej(new Error(JSON.stringify(msg.error))) : res(msg.result)
      } else if (msg.method) listeners.forEach((l) => l(msg))
    }
    const send = (method, params = {}, sessionId) => new Promise((res, rej) => {
      const mid = ++id
      const t = setTimeout(() => { pending.delete(mid); rej(new Error(`CDP ${method}이 ${CALL_TIMEOUT / 1000}초 안에 답하지 않았다`)) }, CALL_TIMEOUT)
      pending.set(mid, { res, rej, t })
      ws.send(JSON.stringify({ id: mid, method, params, sessionId }))
    })
    return {
      send, listeners,
      async close() {
        const exited = new Promise((res) => { if (proc.exitCode !== null) res(); else proc.once('exit', res) })
        try { await send('Browser.close') } catch {}
        ws.close()
        proc.kill()
        await Promise.race([exited, sleep(5000)])
        cleanup()
      },
    }
  } catch (e) {
    if (proc && proc.exitCode === null) proc.kill()
    cleanup()
    throw e
  }
}

// 새 탭 하나 — 폭·색 모드를 에뮬레이트하고 url을 연다. 열지 못하면(네트워크 오류·시간 초과·2xx 아님) 던진다.
// 테마는 prefers-color-scheme로만 정한다 — 실행마다 새 프로필이라 저장된 선택이 없고, theme.js는 토글할 때만 쓴다.
async function openPage(b, url, { width, height = 900, scheme, mobile = false }) {
  const { targetId } = await b.send('Target.createTarget', { url: 'about:blank' })
  const { sessionId } = await b.send('Target.attachToTarget', { targetId, flatten: true })
  const s = (m, p) => b.send(m, p, sessionId)
  await s('Page.enable')
  await s('Runtime.enable')
  await s('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile })
  await s('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: scheme }] })
  const loaded = new Promise((res) => {
    const t = setTimeout(() => { b.listeners.splice(b.listeners.indexOf(l), 1); res(false) }, 25000)
    const l = (msg) => { if (msg.sessionId === sessionId && msg.method === 'Page.loadEventFired') { clearTimeout(t); b.listeners.splice(b.listeners.indexOf(l), 1); res(true) } }
    b.listeners.push(l)
  })
  const nav = await s('Page.navigate', { url })
  if (nav.errorText) throw new Error(`${url}을 열지 못했다: ${nav.errorText}`)
  if (!(await loaded)) throw new Error(`${url}이 25초 안에 load되지 않았다`)
  await sleep(1500)
  const evaluate = async (expr) => {
    const r = await s('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text)
    return r.result.value
  }
  const status = await evaluate(`(performance.getEntriesByType('navigation')[0] || {}).responseStatus || 0`)
  if (status && (status < 200 || status >= 300)) throw new Error(`${url}이 HTTP ${status}를 냈다`)
  return {
    evaluate,
    async shot(file, clip) {
      const { data } = await s('Page.captureScreenshot', { format: 'png', ...(clip ? { clip: { ...clip, scale: 1 }, captureBeyondViewport: true } : {}) })
      writeFileSync(file, Buffer.from(data, 'base64'))
    },
    close: () => b.send('Target.closeTarget', { targetId }),
  }
}

// 페이지 안에서 도는 측정. 값만 돌려주고 판정은 바깥에서 한다.
const MEASURE = `(() => {
  const out = {}
  const probe = document.createElement('span')
  probe.style.color = 'var(--link)'
  document.body.appendChild(probe)
  out.link = getComputedStyle(probe).color
  probe.remove()
  out.canvas = getComputedStyle(document.body).backgroundColor

  // ① 홈 카드
  out.cards = [...document.querySelectorAll('.post .thumb')].map((t) => ({
    hasImg: !!t.querySelector(':scope > .thumb-img'),
    before: getComputedStyle(t, '::before').display,
  }))

  // ② 빈 메뉴
  const nav = document.querySelector('.site-nav')
  out.nav = nav && { html: nav.innerHTML.trim(), items: nav.querySelectorAll('li').length,
    display: getComputedStyle(nav).display, height: nav.getBoundingClientRect().height }

  // ③④⑤ 카테고리 줄
  out.rows = [...document.querySelectorAll('.tt_category a')].filter((a) => a.offsetParent).map((a) => {
    const cs = getComputedStyle(a)
    const r = a.getBoundingClientRect()
    const cnt = a.querySelector('.c_cnt')
    const img = a.querySelector(':scope > img')
    const textNode = [...a.childNodes].find((n) => n.nodeType === 3 && n.textContent.trim())
    let nameRight = null
    if (textNode) { const range = document.createRange(); range.selectNodeContents(textNode); const rr = range.getClientRects(); nameRight = rr.length ? rr[0].right : null }
    const row = { level: a.className, name: textNode ? textNode.textContent.trim() : '', right: r.right,
      contentRight: r.right - parseFloat(cs.paddingRight) - parseFloat(cs.borderRightWidth) }
    if (cnt) { const c = cnt.getBoundingClientRect(); row.cnt = { left: c.left, right: c.right } }
    if (img) {
      const ir = img.getBoundingClientRect()
      const ics = getComputedStyle(img)
      row.img = { w: ir.width, h: ir.height, left: ir.left, right: ir.right, nameRight,
        border: ics.borderTopColor, borderW: ics.borderTopWidth }
    }
    return row
  })
  const tree = document.querySelector('.tt_category')
  if (tree && tree.offsetParent) {
    const t = tree.getBoundingClientRect()
    out.treeRight = t.right
    out.treeClip = { x: t.left, y: t.top + scrollY, width: t.width + 8, height: t.height }
  }
  return out
})()`

const results = []
const report = (state, label, detail = '') => results.push({ state, label, detail })

// 라벨에는 측정값을 넣지 않는다 — self-test가 라벨로 기준과 짝을 짓는다
function judge(m, ctx, report) {
  // ① 카드 — 대표이미지 있는 카드는 ::before 없음, 없는 카드는 있음. 카드가 통째로 없으면 실패
  const withImg = m.cards.filter((c) => c.hasImg)
  const without = m.cards.filter((c) => !c.hasImg)
  if (!m.cards.length) report('실패', `${ctx} ① 홈 카드`, '.post .thumb가 하나도 없다 — 홈 목록이 깨졌거나 class가 바뀌었다')
  else {
    const bad = withImg.filter((c) => c.before !== 'none')
    report(bad.length ? '실패' : withImg.length ? '통과' : '미측', `${ctx} ① 대표이미지 카드에 삽화 층이 없다`,
      `${withImg.length - bad.length}/${withImg.length}` + (bad.length ? ` — ::before display=${bad[0].before}` : ''))
    const off = without.filter((c) => c.before === 'none')
    report(off.length ? '실패' : without.length ? '통과' : '미측', `${ctx} ① 대표이미지 없는 카드는 삽화가 그려진다`,
      `${without.length - off.length}/${without.length}`)
  }
  // ② 빈 메뉴 — 메뉴가 있으면 조건이 없는 것(미측), .site-nav가 없으면 실패
  if (!m.nav) report('실패', `${ctx} ② 빈 메뉴`, '.site-nav가 없다 — 헤더 마크업이 바뀌었다')
  else if (m.nav.items) report('미측', `${ctx} ② 빈 메뉴`, `메뉴 ${m.nav.items}개 — 비어 있지 않다`)
  else report(m.nav.height === 0 ? '통과' : '실패', `${ctx} ② 빈 메뉴 높이 0`,
    `${JSON.stringify(m.nav.html)} display=${m.nav.display} height=${m.nav.height}`)
  // ③ 배지 — 트리가 없거나 배지가 없는 줄은 실패
  if (!m.rows.length) { report('실패', `${ctx} ③④⑤ 카테고리 트리`, '보이는 .tt_category 줄이 없다 — 트리가 빠졌거나 폴더형이다'); return }
  const off = m.rows.filter((r) => !r.cnt || Math.abs(r.cnt.right - r.contentRight) > 0.5)
  report(off.length ? '실패' : '통과', `${ctx} ③ 글 수 배지가 모든 줄에서 오른쪽 끝`,
    `${m.rows.length - off.length}/${m.rows.length}` + (off.length ? ` — ${off[0].name}: ` + (off[0].cnt
      ? `배지 ${off[0].cnt.right.toFixed(1)} / 끝 ${off[0].contentRight.toFixed(1)}` : '배지가 없다') : ''))
  // ④ 새 글 점 — 상위(link_tit·link_item)와 하위(link_sub_item)를 따로. 새 글이 없으면 미측
  for (const [label, levels] of [['상위', ['link_tit', 'link_item']], ['하위', ['link_sub_item']]]) {
    const dots = m.rows.filter((r) => r.img && levels.some((l) => r.level.includes(l)))
    if (!dots.length) { report('미측', `${ctx} ④ ${label} 카테고리 새 글 점`, '새 글이 있는 줄이 없다'); continue }
    const bad = dots.filter((r) => {
      const i = r.img
      return Math.abs(i.w - 6) > 0.5 || Math.abs(i.h - 6) > 0.5 || i.border !== m.link || i.borderW !== '3px'
        || !(i.nameRight !== null && i.left >= i.nameRight) || !(r.cnt && i.right <= r.cnt.left)
    })
    report(bad.length ? '실패' : '통과', `${ctx} ④ ${label} 카테고리 새 글 점(6×6·--link·이름 뒤·배지 앞)`,
      dots.map((r) => `${r.name} ${r.img.w}×${r.img.h} ${r.img.border}`).join(', ')
      + (bad.length ? ` — 어긋남: ${bad.map((r) => r.name).join(', ')}` : ''))
  }
  // ⑤ 줄이 트리 상자 안에 있는가
  const over = m.rows.filter((r) => r.right > m.treeRight + 0.5)
  report(over.length ? '실패' : '통과', `${ctx} ⑤ 카테고리 줄이 트리 상자를 넘지 않는다`,
    `${m.rows.length - over.length}/${m.rows.length}, 상자 오른쪽 ${m.treeRight}` + (over.length
      ? ` — ${over.length}줄이 넘친다(${over[0].name} ${over[0].right}, ${[...new Set(over.map((r) => r.level))].join('·')}). 이슈 #122` : ''))
}

// 한 조합을 연다 → 접힌 가지를 펼친다 → (self-test면 CSS를 주입한다) → 잰다.
async function measure(b, { width, scheme, mobile, inject }) {
  const p = await openPage(b, BASE + '/', { width, scheme, mobile })
  // 하위 카테고리는 접혀 있다(category.js — 현재 가지만 펼친다). 접힌 줄은 화면에 없어 잴 수 없으므로
  // 방문자가 하듯 토글을 눌러 다 펼친다. 2026-10-09 첫 판은 이걸 빼먹어 하위의 새 글 점을 「없다」고 했다.
  const opened = await p.evaluate(`(() => { const t = [...document.querySelectorAll('.tt_category .cat-toggle[aria-expanded="false"]')]; t.forEach((b) => b.click()); return t.length })()`)
  if (inject) await p.evaluate(`(() => { const st = document.createElement('style'); st.textContent = ${JSON.stringify(inject)}; document.head.appendChild(st) })()`)
  await sleep(400)
  const m = await p.evaluate(MEASURE)
  return { p, m, opened }
}

// 각 항목을 깨는 CSS — 실제로 일어날 법한 회귀로 쓴다(규칙이 빠지거나 덮인다)
const MUTANTS = [
  ['①', '.post .thumb:has(> .thumb-img)::before { display: block !important }'],
  ['②', '.site-nav { display: block !important }'],  // :has(> ul:empty) 규칙이 빠진 상태 — 390에서만 빈 줄이 생긴다
  ['③', '.tt_category .c_cnt { order: 0 !important; margin-left: 0 !important } .tt_category a > img { order: 2 !important; margin-left: auto !important }'],
  ['④', '.tt_category a > img { width: auto !important; height: auto !important; border-width: 0 !important }'],
  ['⑤', '.tt_category .link_item { margin-right: -10px !important }'],
]
const SELF_VIEWS = [[1440, false], [390, true]]

let b
try {
  b = await launch()
  if (SELF_TEST) {
    const judged = async (inject, width, mobile) => {
      const got = []
      const { p, m } = await measure(b, { width, scheme: 'light', mobile, inject })
      judge(m, '', (state, label, detail = '') => got.push({ state, label, detail }))
      await p.close()
      return got
    }
    const base = {}
    for (const [w, mob] of SELF_VIEWS) base[w] = await judged(null, w, mob)
    for (const [mark, css] of MUTANTS) {
      const hits = []
      for (const [w, mob] of SELF_VIEWS) {
        const before = new Map(base[w].filter((r) => r.label.includes(mark)).map((r) => [r.label, r]))
        const got = await judged(css, w, mob)
        hits.push(...got.filter((r) => r.label.includes(mark) && r.state === '실패'
          && !(before.get(r.label)?.state === '실패' && before.get(r.label)?.detail === r.detail)).map((r) => ({ ...r, w })))
      }
      report(hits.length ? '통과' : '실패', `[self-test] ${mark}을 깨는 CSS를 주입하면 ${mark}이 새로 실패한다`,
        hits.length ? `${[...new Set(hits.map((h) => h.w))].join('·')}px에서 — ${hits[0].label.trim()}: ${hits[0].detail}`
          : '기준과 달라진 실패가 없다 — 이 검사는 그 조건을 못 잡는다')
    }
  } else {
    const seen = {}
    for (const scheme of ['light', 'dark']) {
      for (const [width, mobile] of [[1440, false], [390, true]]) {
        const ctx = `[${scheme} ${width}]`
        const { p, m, opened } = await measure(b, { width, scheme, mobile })
        if (width === 1440) {
          report('정보', `${ctx} 접힌 가지 ${opened}개를 펼쳤다 · --link ${m.link} · 바탕 ${m.canvas}`)
          seen[scheme] = m
        }
        judge(m, ctx, report)
        if (SHOTS && m.treeClip) {
          mkdirSync(SHOTS, { recursive: true })
          await p.shot(join(SHOTS, `category-${scheme}-${width}.png`), m.treeClip)
        }
        await p.close()
      }
    }
    // 다크가 실제로 먹었는가 — 안 먹으면 위의 다크 결과는 라이트를 두 번 잰 것이다
    const same = seen.light.canvas === seen.dark.canvas || seen.light.link === seen.dark.link
    report(same ? '실패' : '통과', '다크 실행이 다크로 그려졌다(바탕·--link가 라이트와 다르다)',
      `라이트 ${seen.light.canvas}·${seen.light.link} / 다크 ${seen.dark.canvas}·${seen.dark.link}`)
  }
} catch (e) {
  report('실패', '측정을 끝내지 못했다', e.message)
} finally {
  if (b) await b.close()
}

const icon = { 통과: '✅', 실패: '❌', 미측: '❔', 정보: 'ℹ️ ' }
for (const r of results) console.log(`${icon[r.state]} ${r.label}${r.detail ? ' — ' + r.detail : ''}`)
const n = (s) => results.filter((r) => r.state === s).length
console.log(`\n통과 ${n('통과')} · 실패 ${n('실패')} · 미측 ${n('미측')}`)
process.exit(n('실패') ? 1 : 0)
