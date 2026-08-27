// 티스토리 스킨 빌드.
//
// 산출물은 붙여넣는 파일 3개 + 업로드하는 파일 35개다. 배포를 사람이 손으로 하기 때문에 이 수를 늘리지 않는다.
//   images/  = script.js 1 + 기본 이미지 WebP 30 (상위 14 + 기본값 1, light·dark — 결정 5·6 개정)
//   루트     = 미리보기 4종. 파일업로드 탭이 그 이름들만 스킨 루트로 보낸다(2026-08-25 실측)
// 기본 이미지는 이미지가 바뀐 배포에서만 다시 올린다. 파일명에 버전이 박혀 있어(package.json placeholderVersion)
// CDN 캐시를 비켜 간다 — 같은 이름으로 다시 올리면 한동안 옛 그림이 보인다.
//
//   node scripts/build.mjs
//   node scripts/build.mjs --watch

import { readFile, writeFile, mkdir, readdir, rm, cp, stat } from 'node:fs/promises'
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

// 기본 이미지 URL의 앞부분. 스킨 편집기의 파일 개수 상한(DECISIONS.md 미결 1)에 막히면
// 이 값만 jsDelivr 같은 외부 CDN으로 바꾼다 — CSS 선택자·변수명은 그대로다.
const PLACEHOLDER_BASE = './images/'
const PH_MAX_BYTES = 100 * 1024
// 산출물 용량 예산(결정 51). 넘으면 빌드가 실패한다 — 방문자가 매번 받는 렌더 차단 자원이다.
// 2026-08-27 실측: style.css 159KB 중 77KB(50%)가 주석이었다. 주석을 벗긴 뒤 78KB, script.js 67KB.
const CSS_MAX_BYTES = 96 * 1024
const JS_MAX_BYTES = 80 * 1024
// 폴백 SVG의 선 색. url() 안의 SVG는 페이지 토큰을 못 받으므로 색을 박는다 — 라이트 #fafafa·다크 #121212
// 양쪽에서 읽히는 중간 회색 하나로 두 테마를 한 벌로 간다. 아래 1층 점격자는 토큰을 따르므로 테마감은 거기서 난다.
const PH_SVG_INK = '#8a8a8a'
let phCount = 0   // placeholderVars가 실제로 복사한 장수. run()의 images/ 개수 검사가 쓴다

/** 카테고리 기본 이미지 WebP를 dist/images/로 복사하고 --ph-<slug> 변수를 만든다.
 *  같은 slug의 모티프 SVG(src/assets/motifs/)는 --ph-<slug>-svg 로 data: 인라인한다 — WebP가 404·네트워크 실패면
 *  CSS 다중 배경의 아래 레이어로 드러나는 **폴백**이다(DESIGN.md §6.2). 모티프가 없는 slug는 빌드 오류다:
 *  `background-image: var(--ph-x), var(--ph-x-svg)`에서 한쪽 변수가 없으면 선언 전체가 무효가 되어 **둘 다** 사라진다.
 *
 *  tokens.css와 같은 3블록 패턴이다 — :root에서 라이트를 정의하고, 시스템 다크와 명시 다크에서
 *  재정의한다(DESIGN.md §7 "미디어쿼리 안에서 색을 처음 정의하지 않는다").
 *  light·dark 한 쌍이 빠지면 그 카테고리는 한쪽 테마에서 점격자만 남는데 에러가 없다 — 그래서 빌드를 멈춘다. */
async function placeholderVars() {
  const dir = path.join(SRC, 'assets', 'placeholders')
  if (!existsSync(dir)) throw new Error('src/assets/placeholders/ 없음. 먼저 `npm run placeholders -- --stub`')
  const bySlug = {}
  for (const f of (await readdir(dir)).sort()) {
    const m = /^([a-z0-9]+)-(light|dark)\.webp$/.exec(f)
    if (!m) { console.warn(`  [주의] 이름 규칙 밖의 기본 이미지 파일: ${f} — 무시`); continue }
    ;(bySlug[m[1]] ??= {})[m[2]] = f
  }
  const version = JSON.parse(await readFile(path.join(ROOT, 'package.json'), 'utf8')).placeholderVersion ?? 1

  const problems = []
  if (!bySlug.default) problems.push('default 슬러그가 없다 — 14종 밖의 카테고리가 빈 카드로 떨어진다')
  for (const [slug, t] of Object.entries(bySlug)) {
    for (const theme of ['light', 'dark']) {
      if (!t[theme]) { problems.push(`${slug}-${theme}.webp 없음`); continue }
      const { size } = await stat(path.join(dir, t[theme]))
      if (size > PH_MAX_BYTES) problems.push(`${t[theme]} ${(size / 1024).toFixed(0)}KB > ${PH_MAX_BYTES / 1024}KB`)
    }
  }
  // 실패는 던진다. 단발 빌드는 아래에서 exit 1로 바꾸고, --watch는 로그만 남기고 다음 변경을 기다린다 —
  // 여기서 exit하면 `npm run placeholders`가 30장을 차례로 다시 쓰는 중간에 감시자가 죽는다.
  const motifDir = path.join(SRC, 'assets', 'motifs')
  for (const slug of Object.keys(bySlug)) {
    if (!existsSync(path.join(motifDir, `${slug}.svg`))) problems.push(`폴백 모티프 src/assets/motifs/${slug}.svg 없음 — python3 scripts/gen-placeholders.py`)
  }
  if (problems.length) {
    throw new Error('기본 이미지: ' + problems.join('\n     기본 이미지: ') + '\n     npm run placeholders 로 다시 만든다.')
  }

  const light = [], dark = [], svg = []
  phCount = 0
  for (const slug of Object.keys(bySlug).sort()) {
    // 폴백 — 모티프는 마스크용이라 #000 고정. 선 색을 박고 62%로 눌러 옛 도안과 같은 농도로 만든다
    const motif = (await readFile(path.join(motifDir, `${slug}.svg`), 'utf8'))
      .replaceAll('#000', PH_SVG_INK)
      .replace(/(<svg[^>]*>)/, '$1<g opacity=".62">').replace(/<\/svg>\s*$/, '</g></svg>')
    svg.push(`  --ph-${slug}-svg: url("data:image/svg+xml;base64,${Buffer.from(motif, 'utf8').toString('base64')}");`)
    for (const theme of ['light', 'dark']) {
      const out = `ph-${slug}-${theme}.v${version}.webp`
      await cp(path.join(dir, bySlug[slug][theme]), path.join(DIST, 'images', out))
      phCount++
      ;(theme === 'light' ? light : dark).push(`  --ph-${slug}: url("${PLACEHOLDER_BASE}${out}");`)
    }
  }
  return [
    '/* ── 기본 이미지 (src/assets/placeholders/ — DESIGN.md §6.2, 결정 5·6) ──',
    '   라이트를 :root에서 정의하고 다크 두 상태에서 재정의한다. tokens.css의 3블록과 같은 패턴. */',
    `:root {\n${light.join('\n')}\n  /* 폴백 — WebP가 안 오면 다중 배경의 아래 레이어로 드러난다. 테마 공통 */\n${svg.join('\n')}\n}`,
    `@media (prefers-color-scheme: dark) {\n  :root:not([data-theme="light"]) {\n${dark.map(l => '  ' + l).join('\n')}\n  }\n}`,
    `:root[data-theme="dark"] {\n${dark.join('\n')}\n}`,
  ].join('\n') + '\n'
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
  // 다크 규칙은 두 스코프로 낸다.
  //   ① [data-theme="dark"]                      — 사용자가 다크를 명시
  //   ② @media dark + :not([data-theme="light"]) — stamp 없음(시스템 따름)
  // ②가 빠지면 저장된 선택이 없는 첫 방문자(=기본 상태)에게 보정이 하나도 걸리지 않는다.
  // 라이트도 같은 이유로 두 스코프다. 라이트 보정을 :not([data-theme="dark"]) 하나로만
  // 두면 stamp 없음 + 시스템 다크에서도 발화해, 다크에서 멀쩡히 읽히던 밝은 글자까지
  // --ink-body로 끌어내린다. 여섯 상태(명시 2 × OS 2 + stamp 없음 × OS 2) 전부에서
  // 다크 규칙과 라이트 규칙이 겹치지 않도록 대칭으로 만든다.
  const DARK_EXPLICIT  = ':root[data-theme="dark"] .contents_style'
  const DARK_SYSTEM    = ':root:not([data-theme="light"]) .contents_style'
  const LIGHT_EXPLICIT = ':root[data-theme="light"] .contents_style'
  const LIGHT_SYSTEM   = ':root:not([data-theme="dark"]) .contents_style'
  // 강조색은 죽이지 않고 다크용으로 매핑한다
  const ACCENT = { '#006dd7': 'var(--link)', '#ee2323': 'var(--error)' }

  // 공백 유/무 두 형태를 모두 덮는다
  const sel = (scope, prop, hex) =>
    [`${scope} [style*="${prop}:${hex}"]`, `${scope} [style*="${prop}: ${hex}"]`]

  // 색을 분류만 해 둔다 (선택자는 스코프별로 나중에 만든다)
  const darkTextHex = [], lightTextHex = [], darkBgHex = [], lightBgHex = [], accentHex = []
  for (const hex of Object.keys(d.color || {})) {
    const L = luminance(hex)
    if (L === null) continue
    if (ACCENT[hex.toLowerCase()]) accentHex.push(hex)
    else if (L < 0.5) darkTextHex.push(hex)
    else lightTextHex.push(hex)
  }
  for (const hex of Object.keys(d.backgroundColor || {})) {
    const L = luminance(hex)
    if (L === null) continue
    if (L >= 0.5) darkBgHex.push(hex)
    else lightBgHex.push(hex)
  }

  const block = (sels, decl, note) =>
    sels.length ? `/* ${note} */\n${sels.join(',\n')} { ${decl} }\n` : ''

  const flat = (scope, prop, list) => list.flatMap(h => sel(scope, prop, h))

  /** 한 스코프분의 다크 보정 규칙 전체 */
  const darkRules = (scope) => [
    block(flat(scope, 'color', darkTextHex),
          'color: var(--ink-body) !important;', '다크에서 죽는 어두운 텍스트'),
    ...accentHex.map(hex =>
      block(sel(scope, 'color', hex),
            `color: ${ACCENT[hex.toLowerCase()]} !important;`, `강조색 → 다크 대응색`)),
    block(flat(scope, 'background-color', darkBgHex),
          'background-color: var(--canvas-soft) !important;', '다크에서 흰 상자가 되는 배경'),
  ].filter(Boolean).join('\n')

  /** 한 스코프분의 라이트 보정 규칙 전체 */
  const lightRules = (scope) => [
    block(flat(scope, 'color', lightTextHex),
          'color: var(--ink-body) !important;', '라이트에서 대비가 부족한 밝은 텍스트'),
    block(flat(scope, 'background-color', lightBgHex),
          'background-color: var(--canvas-soft-2) !important;', '라이트에서 검은 상자가 되는 배경'),
  ].filter(Boolean).join('\n')

  const indent = (s) => s.split('\n').map(l => l ? '  ' + l : l).join('\n')
  const systemDark  = indent(darkRules(DARK_SYSTEM))
  const systemLight = indent(lightRules(LIGHT_SYSTEM))

  const out = [
    `/* ── 인라인 스타일 보정 (data/inline-styles.json ${d.crawledAt ?? ''}에서 생성 — 직접 수정하지 말 것) ── */`,
    `/* 폰트 — 전부 무력화. inherit이므로 <pre> 안에서는 --font-mono를 물려받는다 */`,
    `.contents_style [style*="font-family"] { font-family: inherit !important; }`,
    darkRules(DARK_EXPLICIT),
    `/* stamp 없음(시스템 따름) 상태 — 저장된 선택이 없는 첫 방문자의 기본값이다 */`,
    `@media (prefers-color-scheme: dark) {\n${systemDark}\n}`,
    lightRules(LIGHT_EXPLICIT),
    `/* stamp 없음 + 시스템 라이트 */`,
    `@media (prefers-color-scheme: light) {\n${systemLight}\n}`,
  ].filter(Boolean).join('\n')

  const n = (darkTextHex.length + darkBgHex.length + accentHex.length
             + lightTextHex.length + lightBgHex.length) * 2 * 2
  console.log(`  인라인 보정 CSS 생성 — 선택자 ${n}개 (색 ${Object.keys(d.color || {}).length}종 + 배경 ${Object.keys(d.backgroundColor || {}).length}종 × 공백 2형태)`)
  return out
}

/**
 * CSS 주석을 벗긴다 — minify가 아니다(결정 51).
 * 공백·선택자·선언은 한 글자도 건드리지 않는다. `[style*="color: #000000"]` 같은 인라인 보정
 * 선택자의 공백이 매칭 조건이라 minifier를 쓰지 않는 것인데, 주석 제거는 그 조건과 무관하다.
 * 문자열과 url(…) 안은 건너뛴다 — data: SVG에 `/*`가 올 수 있다.
 */
function stripCssComments(css) {
  let out = ''
  let i = 0
  while (i < css.length) {
    const c = css[i]
    if (c === '/' && css[i + 1] === '*') {
      const end = css.indexOf('*/', i + 2)
      i = end < 0 ? css.length : end + 2
      continue
    }
    if (c === '"' || c === "'") {
      let j = i + 1
      while (j < css.length && css[j] !== c) { if (css[j] === '\\') j++; j++ }
      out += css.slice(i, j + 1)
      i = j + 1
      continue
    }
    if (c === 'u' && css.startsWith('url(', i)) {
      let j = i + 4, depth = 1, q = null
      while (j < css.length && depth) {
        const d = css[j]
        if (q) { if (d === '\\') j++; else if (d === q) q = null }
        else if (d === '"' || d === "'") q = d
        else if (d === '(') depth++
        else if (d === ')') depth--
        j++
      }
      out += css.slice(i, j)
      i = j
      continue
    }
    out += c
    i++
  }
  // 주석이 빠진 자리의 빈 줄과 줄 끝 공백을 접는다
  return out.replace(/[ \t]+$/gm, '').replace(/\n{3,}/g, '\n\n').trim() + '\n'
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

  // 주석은 여기서 벗긴다(결정 51). 파일 경계 마커 한 줄씩만 남겨 라이브 CSS를 읽을 때 어느
  // 조각인지 알 수 있게 한다. 근거·사고 서술은 src/styles/*.css 안에 그대로 있다.
  const parts = [stripCssComments(await placeholderVars())]
  for (const n of ordered) {
    parts.push(`/* ── ${n}.css ── */\n` + stripCssComments(await readFile(path.join(dir, `${n}.css`), 'utf8')))
  }
  parts.push(stripCssComments(await inlineFixCss()))

  // minify하지 않는다. [style*="color:#000000"] 같은 인라인 보정 선택자의 공백 처리가
  // minifier마다 달라 매칭이 조용히 깨질 수 있다. style.css 크기보다 정확성이 중요하다.
  // (주석 제거는 minify가 아니다 — 공백·선택자를 건드리지 않는다.)
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

  // 용량 예산(결정 51). 조용히 커지는 것을 막는다 — 넘으면 무엇을 뺄지 정하고 예산을 고친다.
  const cssBytes = css ? Buffer.byteLength(css) : 0
  const jsBytes = js ? Buffer.byteLength(js) : 0
  const over = []
  if (cssBytes > CSS_MAX_BYTES) over.push(`style.css ${(cssBytes / 1024).toFixed(1)}KB > ${CSS_MAX_BYTES / 1024}KB`)
  if (jsBytes > JS_MAX_BYTES) over.push(`images/script.js ${(jsBytes / 1024).toFixed(1)}KB > ${JS_MAX_BYTES / 1024}KB`)
  if (over.length) throw new Error('용량 예산 초과: ' + over.join(', ') + '\n     예산은 scripts/build.mjs의 CSS_MAX_BYTES·JS_MAX_BYTES (결정 51)')

  // 스킨 미리보기 이미지가 있으면 스킨 **루트**로 복사한다.
  // 티스토리는 여기서 찾는다 — images/ 아래가 아니다.
  const prev = path.join(SRC, 'preview')
  if (existsSync(prev)) await cp(prev, DIST, { recursive: true })

  const uploads = existsSync(path.join(DIST, 'images'))
    ? (await readdir(path.join(DIST, 'images'))).length : 0
  console.log(`\n  dist/  skin.html ${skin ? '✓' : '—'}  style.css ${css ? (cssBytes / 1024).toFixed(1) + 'KB' : '—'}  script.js ${js ? (jsBytes / 1024).toFixed(1) + 'KB' : '—'}` +
              `  index.xml ${xml ? '✓' : '—'}  images/ ${uploads}개` +
              `  preview ${existsSync(path.join(DIST, 'preview.gif')) ? '✓' : '—'}`)
  // script.js 1 + 기본 이미지 30. 더 생기면 배포가 그만큼 손이 더 가고, 덜 생기면 어느 카테고리가 빈 카드다.
  // 기대치는 placeholderVars가 **실제로 복사한** 장수다 — 디렉터리의 .webp를 세면 이름 규칙 밖 파일까지 세어 메시지가 뒤집힌다.
  const expected = 1 + phCount
  if (uploads !== expected) {
    console.warn(`  ⚠️ images/가 ${uploads}개다. script.js 1 + 기본 이미지 ${expected - 1} = ${expected}개여야 한다 —\n` +
                 '     기본 이미지 말고는 images/에 두지 않는다. 폰트는 CDN, 도안은 WebP 30장뿐이다.')
  }
  console.log('  다음: npm run lint  ·  npm run preview')
}

try {
  await run()
} catch (e) {
  console.error(`\n  ❌ ${e.message}\n`)
  process.exit(1)
}

if (WATCH) {
  const { watch } = await import('node:fs')
  console.log('\n  변경 감시 중… (Ctrl+C로 종료)')
  let t
  watch(SRC, { recursive: true }, () => {
    clearTimeout(t)
    t = setTimeout(() => run().catch(e => console.error(`\n  ❌ ${e.message}\n  (감시는 계속된다)`)), 120)
  })
}
