// CSS 구문 검사 — SYN001 (npm run test:css, npm run check 안에서 돈다)
//
// 왜 필요한가 — 2026-08-27 하네스 리뷰. 린트 45종이 있는데 `components.css` 끝에
// `.x { color: var(--ink);`(닫는 괄호 없음)를 넣어도 **오류 0 · 경고 0**이었다. 이어붙인
// style.css에서 괄호 하나가 어긋나면 그 뒤 규칙이 전부 죽고 티스토리는 에러를 안 낸다 —
// 3천 줄 손편집 CSS에서 가장 흔한 회귀인데 어느 규칙도 안 봤다. 규칙 #46이 아니라
// 파서 하나가 그 부류를 통째로 덮는다.
//
// 보는 것:
//   ① 파싱 오류(css-tree onParseError) — 괄호·세미콜론·따옴표
//   ② 모르는 속성 이름(`colr:`) — css-tree 어휘에 없는 표준/벤더 속성
//   ③ `var()`가 **없는** 값의 문법 오류(`display: flx`) — var()가 섞이면 css-tree가
//      대조를 못 하므로 건너뛴다(이 저장소는 대부분 var()라 ③이 보는 범위는 좁다)
//
// 대상: src/styles/*.css 각각 + dist/style.css(있을 때 — 생성된 인라인 보정 규칙 포함)
import * as csstree from 'css-tree'
import fs from 'node:fs'
import path from 'node:path'

const SRC_DIR = 'src/styles'
const files = fs.readdirSync(SRC_DIR).filter((f) => f.endsWith('.css')).sort().map((f) => path.join(SRC_DIR, f))
if (fs.existsSync('dist/style.css')) files.push('dist/style.css')

const errors = []
let declarations = 0

// 괄호 균형. CSS 문법은 EOF가 열린 블록을 닫아 주므로 **파일 끝의 `{` 누락은 파서가 조용히
// 넘긴다** — 그런데 그 파일이 이어붙인 style.css의 중간이면 뒤 파일의 규칙이 통째로 그 블록
// 안으로 삼켜진다. 파서와 별개로 문자열·주석을 건너뛰며 직접 센다.
function braceBalance(src) {
  const open = []
  const problems = []
  let i = 0, line = 1
  while (i < src.length) {
    const c = src[i]
    if (c === '\n') { line++; i++; continue }
    if (c === '/' && src[i + 1] === '*') { const end = src.indexOf('*/', i + 2); if (end < 0) { problems.push(`${line}행: 닫히지 않은 주석`); break } line += (src.slice(i, end).match(/\n/g) || []).length; i = end + 2; continue }
    if (c === '"' || c === "'") {
      // 문자열. `\` 다음 글자는 무엇이든(개행 포함 — CSS는 줄 잇기를 허용한다) 건너뛴다.
      let j = i + 1, closed = false
      while (j < src.length) {
        const d = src[j]
        if (d === '\\') { if (src[j + 1] === '\n') line++; j += 2; continue }
        if (d === c) { closed = true; break }
        if (d === '\n') break
        j++
      }
      if (!closed) problems.push(`${line}행: 닫히지 않은 문자열`)
      i = closed ? j + 1 : j   // 실패하면 개행 자리에서 멈춰 위 분기가 line++을 처리하게 한다
      continue
    }
    if (c === 'u' && src.startsWith('url(', i)) {
      // url(…) 안은 따옴표 없이도 `{`·`}`가 올 수 있다(data: SVG). css-tree가 받아들이는 것을
      // 여기서 오류로 내면 안 된다 — 닫는 `)`까지 통째로 건너뛴다(안의 따옴표는 위 분기가 맡지 않는다).
      let j = i + 4, depth = 1, q = null
      while (j < src.length && depth) {
        const d = src[j]
        if (q) { if (d === '\\') j++; else if (d === q) q = null }
        else if (d === '"' || d === "'") q = d
        else if (d === '(') depth++
        else if (d === ')') depth--
        if (src[j] === '\n') line++
        j++
      }
      i = j
      continue
    }
    if (c === '{') open.push(line)
    else if (c === '}') { if (!open.length) problems.push(`${line}행: 여는 괄호 없는 \`}\``); else open.pop() }
    i++
  }
  for (const l of open) problems.push(`${l}행: 닫히지 않은 \`{\` (파일 끝까지)`)
  return problems
}

for (const file of files) {
  const src = fs.readFileSync(file, 'utf8')
  for (const p of braceBalance(src)) errors.push(`${file}:${p}`)
  const ast = csstree.parse(src, {
    positions: true,
    filename: file,
    onParseError(e) {
      errors.push(`${file}:${e.line}:${e.column} — ${e.message}`)
    },
  })
  csstree.walk(ast, {
    visit: 'Declaration',
    enter(node) {
      declarations++
      const prop = node.property
      if (prop.startsWith('--')) return
      const value = csstree.generate(node.value)
      const r = csstree.lexer.matchProperty(prop, node.value)
      if (!r.error) return
      const where = `${file}:${node.loc.start.line}:${node.loc.start.column}`
      if (r.error.name === 'SyntaxReferenceError') {
        errors.push(`${where} — 모르는 속성 \`${prop}\` (${r.error.message})`)
      } else if (!/var\(/.test(value)) {
        errors.push(`${where} — \`${prop}: ${value.slice(0, 60)}\` 값이 문법에 안 맞는다: ${r.error.message.split('\n')[0]}`)
      }
      // var()가 섞인 값은 css-tree가 대조하지 못한다 — 건너뛴다
    },
  })
}

if (errors.length) {
  for (const e of errors) console.log(`❌ [SYN001] ${e}`)
  console.log(`\nCSS 구문 오류 ${errors.length}건 (파일 ${files.length}개 · 선언 ${declarations}개)`)
  process.exit(1)
}
console.log(`CSS 구문 — 파일 ${files.length}개 · 선언 ${declarations}개 · 오류 0 (SYN001)`)
