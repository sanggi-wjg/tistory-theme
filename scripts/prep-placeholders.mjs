// 기본 이미지 원본 → WebP 30장 (상위 14 + 기본값 1) × (light · dark).
//
//   src/assets/placeholders-src/<slug>-<theme>.{png,jpg,jpeg,webp,svg}   ← 원본 (AI 생성 이미지를 여기에 둔다)
//   src/assets/placeholders/<slug>-<theme>.webp                          ← 변환 결과. 커밋한다. 빌드가 읽는 것은 이것뿐
//
//   node scripts/prep-placeholders.mjs           원본 전부 변환
//   node scripts/prep-placeholders.mjs --stub    원본이 없는 자리를 src/assets/motifs/의 SVG로 채운 뒤 변환
//
// 빌드(scripts/build.mjs)에 넣지 않는다 — 원본이 바뀔 때만 사람이 돌린다. gen-preview.mjs와 같은 위치다.
//
// 규격 — DESIGN.md §6.2
//   · 16:10 (.thumb의 aspect-ratio). 다른 비율은 가운데 기준으로 cover 크롭한다
//   · 800×500, WebP q75, 장당 100KB 이하. 넘으면 실패한다 — 30장이 한 목록 페이지에 같이 뜰 수 있다
//   · slug는 DESIGN.md §6.2 선택자 블록의 --ph-<slug>와 같아야 한다. 틀리면 그 카테고리가 조용히 --ph-default로 떨어진다
//
// AI 이미지를 넣을 때
//   · 글자를 넣지 않는다 — 확산모델의 글자는 깨지고, alt도 없다
//   · 30장을 같은 스타일·같은 팔레트로 — 홈·검색 목록에서 카테고리가 섞여 나란히 놓인다
//   · dark는 배경이 어두운 판이어야 한다. 라이트 그림을 그대로 어둡게 깎은 것은 다크 캔버스(#0a0a0a) 위에서 뜬다
//   · 같은 키에 원본이 둘이면(예: 임시 stub .svg + 새 .png) 래스터가 이긴다 (EXT_PRIORITY). stub는 지워도 된다
//
// 임시본(--stub)의 색은 src/styles/tokens.css에서 읽는다. 여기에 색을 적지 않는다 (TOK001의 정신).

import sharp from 'sharp'
import { readdir, readFile, writeFile, mkdir, rm, stat } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import path from 'node:path'

const ROOT = process.cwd()
const SRC_DIR = path.join(ROOT, 'src', 'assets', 'placeholders-src')
const OUT_DIR = path.join(ROOT, 'src', 'assets', 'placeholders')
const MOTIF_DIR = path.join(ROOT, 'src', 'assets', 'motifs')
const TOKENS = path.join(ROOT, 'src', 'styles', 'tokens.css')

const W = 800, H = 500, QUALITY = 75, MAX_BYTES = 100 * 1024
const THEMES = ['light', 'dark']
const EXT_PRIORITY = ['png', 'jpg', 'jpeg', 'webp', 'svg']
const STUB = process.argv.includes('--stub')

/** tokens.css에서 selector로 시작하는 블록의 본문을 꺼낸다. */
function cssBlock(css, selectorRe) {
  const m = selectorRe.exec(css)
  if (!m) throw new Error(`tokens.css에서 블록을 못 찾았다: ${selectorRe}`)
  let depth = 0, start = -1
  for (let i = m.index; i < css.length; i++) {
    if (css[i] === '{') { if (depth++ === 0) start = i + 1 }
    else if (css[i] === '}') { if (--depth === 0) return css.slice(start, i) }
  }
  throw new Error('블록이 닫히지 않았다')
}

function token(block, name) {
  const m = new RegExp(`${name}\\s*:\\s*(#[0-9a-fA-F]{3,8})\\s*;`).exec(block)
  if (!m) throw new Error(`tokens.css 블록에 ${name}이 없다`)
  return m[1]
}

async function themeColors() {
  const css = await readFile(TOKENS, 'utf8')
  const light = cssBlock(css, /^:root\s*\{/m)
  const dark = cssBlock(css, /^:root\[data-theme="dark"\]\s*\{/m)
  return {
    light: { bg: token(light, '--canvas-soft'), ink: token(light, '--ink-mute') },
    dark:  { bg: token(dark,  '--canvas-soft'), ink: token(dark,  '--ink-mute') },
  }
}

/** 모티프 SVG(마스크용, #000 고정)를 테마 색 판 위에 얹은 독립 SVG. */
function stubSvg(motif, { bg, ink }) {
  const inner = motif.replace(/^[\s\S]*?<svg[^>]*>/, '').replace(/<\/svg>\s*$/, '')
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 200" width="${W}" height="${H}">\n` +
         `<rect width="320" height="200" fill="${bg}"/>\n` +
         `<g fill="none" stroke-linecap="round" stroke-linejoin="round" opacity=".62">` +
         inner.replaceAll('#000', ink) + `</g>\n</svg>\n`
}

/** placeholders-src/를 훑어 {slug: {theme: 파일경로}}로 만든다. 같은 키가 여럿이면 EXT_PRIORITY 앞이 이긴다. */
async function sources() {
  if (!existsSync(SRC_DIR)) return {}
  const map = {}
  for (const f of (await readdir(SRC_DIR)).sort()) {
    const m = /^([a-z0-9]+)-(light|dark)\.(png|jpe?g|webp|svg)$/i.exec(f)
    if (!m) { console.warn(`  [무시] 이름 규칙 밖: ${f}  (<slug>-<light|dark>.<png|jpg|webp|svg>)`); continue }
    const [, slug, theme, ext] = m
    const cur = map[slug]?.[theme]
    if (!cur || EXT_PRIORITY.indexOf(ext.toLowerCase()) < EXT_PRIORITY.indexOf(path.extname(cur).slice(1).toLowerCase())) {
      ;(map[slug] ??= {})[theme] = f
    } else {
      console.warn(`  [무시] ${f} — 같은 키에 ${cur}가 있어 그쪽을 쓴다`)
    }
  }
  return map
}

async function makeStubs(map) {
  if (!existsSync(MOTIF_DIR)) throw new Error('--stub인데 src/assets/motifs/가 없다. python3 scripts/gen-placeholders.py')
  const colors = await themeColors()
  await mkdir(SRC_DIR, { recursive: true })
  let made = 0
  for (const f of (await readdir(MOTIF_DIR)).filter(f => f.endsWith('.svg')).sort()) {
    const slug = path.basename(f, '.svg')
    const motif = await readFile(path.join(MOTIF_DIR, f), 'utf8')
    for (const theme of THEMES) {
      if (map[slug]?.[theme]) continue
      const name = `${slug}-${theme}.svg`
      await writeFile(path.join(SRC_DIR, name), stubSvg(motif, colors[theme]))
      ;(map[slug] ??= {})[theme] = name
      made++
    }
  }
  console.log(`  임시본 ${made}장 생성 (${JSON.stringify(colors)})`)
}

async function main() {
  const map = await sources()
  if (STUB) await makeStubs(map)

  const slugs = Object.keys(map).sort()
  if (!slugs.length) {
    console.error('  ❌ 원본이 없다. src/assets/placeholders-src/에 <slug>-<theme>.png를 두거나 --stub로 임시본을 만든다.')
    process.exit(1)
  }

  await mkdir(OUT_DIR, { recursive: true })
  // 결과 디렉터리는 생성물이다 — 원본에 없는 옛 파일이 남으면 빌드가 그것을 배포한다
  for (const f of await readdir(OUT_DIR)) {
    const m = /^([a-z0-9]+)-(light|dark)\.webp$/.exec(f)
    if (!m || !map[m[1]]?.[m[2]]) { await rm(path.join(OUT_DIR, f)); console.warn(`  [정리] 원본 없는 결과 삭제: ${f}`) }
  }

  const problems = []
  if (!map.default) problems.push('default 슬러그가 없다 — 14종 밖의 카테고리가 빈 카드로 떨어진다')
  let total = 0
  console.log(`  ${'slug'.padEnd(10)} ${'light'.padStart(8)} ${'dark'.padStart(8)}   원본`)
  for (const slug of slugs) {
    const sizes = {}, from = []
    for (const theme of THEMES) {
      const src = map[slug][theme]
      if (!src) { problems.push(`${slug}-${theme} 원본 없음`); sizes[theme] = '—'; continue }
      const input = path.join(SRC_DIR, src)
      const meta = await sharp(input).metadata()
      const ratio = meta.width / meta.height
      if (Math.abs(ratio - W / H) > 0.02) from.push(`${src}(${meta.width}×${meta.height} → cover 크롭)`)
      else from.push(src)
      const out = path.join(OUT_DIR, `${slug}-${theme}.webp`)
      await sharp(input).resize(W, H, { fit: 'cover', position: 'centre' }).webp({ quality: QUALITY, effort: 6 }).toFile(out)
      const { size } = await stat(out)
      total += size
      sizes[theme] = `${(size / 1024).toFixed(1)}K`
      if (size > MAX_BYTES) problems.push(`${slug}-${theme}.webp ${(size / 1024).toFixed(0)}KB > ${MAX_BYTES / 1024}KB`)
    }
    console.log(`  ${slug.padEnd(10)} ${sizes.light.padStart(8)} ${sizes.dark.padStart(8)}   ${from.join(' · ')}`)
  }
  console.log(`\n  ${slugs.length}종 × 2 = ${slugs.length * 2}장 · 합계 ${(total / 1024).toFixed(0)}KB → src/assets/placeholders/`)

  if (problems.length) {
    console.error('\n  ❌ ' + problems.join('\n  ❌ '))
    process.exit(1)
  }
  console.log('  다음: npm run build')
}

await main()
