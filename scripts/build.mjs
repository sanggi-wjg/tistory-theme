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
