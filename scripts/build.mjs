// 티스토리 스킨 빌드.
//
// 산출물은 붙여넣는 파일 3개 + 업로드하는 파일 1개여야 한다. 배포를 사람이 손으로 하기 때문이다.
// images/에 파일이 2개 이상 생기면 설계가 잘못된 것이다 — 기본이미지 SVG는 data: URI로 CSS에 인라인한다.
//
//   node scripts/build.mjs
//   node scripts/build.mjs --watch

import { readFile, writeFile, mkdir, readdir, rm, cp } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import path from 'node:path'

const ROOT = process.cwd()
const SRC = path.join(ROOT, 'src')
const DIST = path.join(ROOT, 'dist')
const WATCH = process.argv.includes('--watch')

// 순서가 곧 특이도 순서다. 임의로 바꾸지 않는다.
const CSS_ORDER = ['tokens', 'base', 'layout', 'content', 'tistory', 'components']

async function readIf(p) {
  return existsSync(p) ? readFile(p, 'utf8') : null
}

/** 카테고리 기본이미지 SVG를 data: URI CSS 변수로 만든다. */
async function placeholderVars() {
  const dir = path.join(SRC, 'assets', 'placeholders')
  if (!existsSync(dir)) return ''
  const files = (await readdir(dir)).filter(f => f.endsWith('.svg')).sort()
  if (!files.length) return ''
  const lines = []
  for (const f of files) {
    const svg = await readFile(path.join(dir, f), 'utf8')
    const b64 = Buffer.from(svg, 'utf8').toString('base64')
    lines.push(`  --ph-${path.basename(f, '.svg')}: url("data:image/svg+xml;base64,${b64}");`)
  }
  return `:root {\n${lines.join('\n')}\n}\n`
}

/** 상대 휘도. 0.5 미만이면 어두운 색으로 본다. */
function luminance(hex) {
  const m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(hex.trim())
  if (!m) return null
  let s = m[1]
  if (s.length === 3) s = [...s].map(c => c + c).join('')
  const [r, g, b] = [0, 2, 4].map(i => parseInt(s.slice(i, i + 2), 16))
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255
}

/** 인라인 스타일 보정 CSS를 실측 데이터에서 생성한다.
 *
 *  손으로 쓰지 않는 이유:
 *  ① 실제 마크업은 `style="color: #000000;"` — 콜론 뒤에 공백이 있다(609곳 중 608곳).
 *     CSS 속성 선택자는 문자 그대로 매칭하므로 두 형태를 모두 써야 한다.
 *  ② 색 목록은 글이 늘면 바뀐다. 손으로 관리하면 실측과 어긋나고 그 사실이 조용히 묻힌다.
 */
async function inlineFixCss() {
  const p = path.join(ROOT, 'data', 'inline-styles.json')
  if (!existsSync(p)) {
    console.warn('  [주의] data/inline-styles.json 없음 — 인라인 스타일 보정 CSS를 생성하지 않는다.\n' +
                 '         기존 글의 인라인 색이 다크모드에서 배경에 묻힌다.\n' +
                 '         python3 .claude/skills/blog-census/scripts/census.py --posts --bodies')
    return ''
  }
  const d = JSON.parse(await readFile(p, 'utf8'))
  const DARK = ':root[data-theme="dark"] .contents_style'
  const LIGHT = ':root:not([data-theme="dark"]) .contents_style'
  // 강조색은 죽이지 않고 다크용으로 매핑한다
  const ACCENT = { '#006dd7': 'var(--link)', '#ee2323': 'var(--error)' }

  // 공백 유/무 두 형태를 모두 덮는다
  const sel = (scope, prop, hex) =>
    [`${scope} [style*="${prop}:${hex}"]`, `${scope} [style*="${prop}: ${hex}"]`]

  const darkText = [], lightText = [], darkBg = [], lightBg = [], accents = []
  for (const hex of Object.keys(d.color || {})) {
    const L = luminance(hex)
    if (L === null) continue
    if (ACCENT[hex.toLowerCase()]) {
      accents.push([hex, ACCENT[hex.toLowerCase()]])
    } else if (L < 0.5) darkText.push(...sel(DARK, 'color', hex))
    else lightText.push(...sel(LIGHT, 'color', hex))
  }
  for (const hex of Object.keys(d.backgroundColor || {})) {
    const L = luminance(hex)
    if (L === null) continue
    if (L >= 0.5) darkBg.push(...sel(DARK, 'background-color', hex))
    else lightBg.push(...sel(LIGHT, 'background-color', hex))
  }

  const block = (sels, decl, note) =>
    sels.length ? `/* ${note} */\n${sels.join(',\n')} { ${decl} }\n` : ''

  const out = [
    `/* ── 인라인 스타일 보정 (data/inline-styles.json ${d.crawledAt ?? ''}에서 생성 — 직접 수정하지 말 것) ── */`,
    `/* 폰트 — 전부 무력화. inherit이므로 <pre> 안에서는 --font-mono를 물려받는다 */`,
    `.contents_style [style*="font-family"] { font-family: inherit !important; }`,
    block(darkText, 'color: var(--ink-body) !important;', '다크에서 죽는 어두운 텍스트'),
    ...accents.map(([hex, v]) =>
      block(sel(DARK, 'color', hex), `color: ${v} !important;`, `강조색 ${hex} → 다크 대응색`)),
    block(lightText, 'color: var(--ink-body) !important;', '라이트에서 대비가 부족한 밝은 텍스트'),
    block(darkBg, 'background-color: var(--canvas-soft) !important;', '다크에서 흰 상자가 되는 배경'),
    block(lightBg, 'background-color: var(--canvas-soft-2) !important;', '라이트에서 검은 상자가 되는 배경'),
  ].filter(Boolean).join('\n')

  const n = darkText.length + lightText.length + darkBg.length + lightBg.length + accents.length * 2
  console.log(`  인라인 보정 CSS 생성 — 선택자 ${n}개 (색 ${Object.keys(d.color || {}).length}종 + 배경 ${Object.keys(d.backgroundColor || {}).length}종 × 공백 2형태)`)
  return out
}

async function buildCss() {
  const dir = path.join(SRC, 'styles')
  if (!existsSync(dir)) {
    console.warn('  [건너뜀] src/styles/ 없음')
    return ''
  }
  const present = (await readdir(dir)).filter(f => f.endsWith('.css')).map(f => path.basename(f, '.css'))
  const ordered = [...CSS_ORDER.filter(n => present.includes(n)),
                   ...present.filter(n => !CSS_ORDER.includes(n)).sort()]
  const unknown = present.filter(n => !CSS_ORDER.includes(n))
  if (unknown.length) console.warn(`  [주의] 순서 정의에 없는 CSS: ${unknown.join(', ')} — 맨 뒤에 붙인다`)

  const parts = [await placeholderVars()]
  for (const n of ordered) {
    parts.push(`/* ── ${n}.css ── */\n` + await readFile(path.join(dir, `${n}.css`), 'utf8'))
  }
  parts.push(await inlineFixCss())

  // minify하지 않는다. [style*="color:#000000"] 같은 인라인 보정 선택자의 공백 처리가
  // minifier마다 달라 매칭이 조용히 깨질 수 있다. style.css 크기보다 정확성이 중요하다.
  return parts.filter(Boolean).join('\n\n')
}

async function buildJs() {
  const entry = path.join(SRC, 'js', 'index.js')
  if (!existsSync(entry)) {
    console.warn('  [건너뜀] src/js/index.js 없음')
    return null
  }
  // esbuild는 JS가 실제로 있을 때만 필요하다. 미설치 상태에서 스택 트레이스 대신
  // 무엇을 해야 하는지 알려준다.
  let build
  try {
    ({ build } = await import('esbuild'))
  } catch {
    console.error('\n  ❌ esbuild가 없다. 먼저 의존성을 설치하라:\n\n     npm install\n')
    process.exit(1)
  }
  const r = await build({
    entryPoints: [entry],
    bundle: true, minify: true, format: 'iife', target: ['es2020'],
    write: false, legalComments: 'none',
  })
  return r.outputFiles[0].text
}

async function run() {
  await rm(DIST, { recursive: true, force: true })
  await mkdir(path.join(DIST, 'images'), { recursive: true })

  // skin.html은 치환자가 있으므로 어떤 변환도 하지 않는다.
  // HTML 파서는 <s_list_rep>를 알 수 없는 태그로 보고 재배치하거나 제거할 수 있다.
  const skin = await readIf(path.join(SRC, 'skin.html'))
  if (skin) await writeFile(path.join(DIST, 'skin.html'), skin)
  else console.warn('  [건너뜀] src/skin.html 없음')

  const xml = await readIf(path.join(SRC, 'index.xml'))
  if (xml) await writeFile(path.join(DIST, 'index.xml'), xml)

  const css = await buildCss()
  if (css) await writeFile(path.join(DIST, 'style.css'), css)

  const js = await buildJs()
  if (js) await writeFile(path.join(DIST, 'images', 'script.js'), js)

  // 스킨 미리보기 이미지가 있으면 그대로 복사한다
  const prev = path.join(SRC, 'preview')
  if (existsSync(prev)) await cp(prev, DIST, { recursive: true })

  const uploads = existsSync(path.join(DIST, 'images'))
    ? (await readdir(path.join(DIST, 'images'))).length : 0
  console.log(`\n  dist/  skin.html ${skin ? '✓' : '—'}  style.css ${css ? '✓' : '—'}` +
              `  index.xml ${xml ? '✓' : '—'}  images/ ${uploads}개`)
  if (uploads > 1) {
    console.warn('  ⚠️ images/에 파일이 2개 이상이다. 배포가 수동이므로 1개로 줄여야 한다 —\n' +
                 '     SVG는 data: URI로 CSS에 인라인하고, 폰트는 CDN에서 받는다.')
  }
  console.log('  다음: npm run lint  ·  npm run preview')
}

await run()

if (WATCH) {
  const { watch } = await import('node:fs')
  console.log('\n  변경 감시 중… (Ctrl+C로 종료)')
  let t
  watch(SRC, { recursive: true }, () => {
    clearTimeout(t)
    t = setTimeout(() => run().catch(e => console.error(e.message)), 120)
  })
}
