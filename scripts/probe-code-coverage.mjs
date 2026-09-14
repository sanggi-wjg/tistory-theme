// 전수 코드블록에 code.js의 판정 경로를 그대로 돌려 **몇 %가 칠해지는지** 센다.
// (TODO codeblock-readability ②) — 임계를 검증하는 probe-code-detect.mjs와 다르다:
// 그쪽은 픽스처로 «임계가 맞는가», 이쪽은 실물로 «그 임계의 대가가 얼마인가».
//
//   python3 .claude/skills/blog-census/scripts/census.py --posts --bodies   # → _workspace/code-blocks.json
//   node scripts/probe-code-coverage.mjs [_workspace/code-blocks.json]
//
// enhance()와 같은 순서로 판정한다 — 사본이 아니라 code.js의 함수·상수를 부른다.
//   ① authorLanguage(<code class>)가 번들 언어 → 칠한다 (author)
//   ② authorLanguage가 라벨만 아는 이름 → 라벨만, 칠하지 않는다 (label-only)
//   ③ MAX_CHARS 초과 → 감지 안 함 (too-long)
//   ④ detect() → 칠한다 (auto) / 원문 그대로 (skip)
// skip의 이유 분류(짧다·한글·신뢰도)는 detect 안의 관문 순서를 따라 다시 본다 — 그 임계는
// code.js에서 export하지 않으므로 여기 숫자는 **보고용**이고 판정은 detect()가 한다.

import { readFileSync } from 'node:fs'
import { detect, authorLanguage, MAX_CHARS } from '../src/js/code.js'

const file = process.argv[2] || '_workspace/code-blocks.json'
const { crawledAt, blocks } = JSON.parse(readFileSync(file, 'utf8'))

const tally = { author: 0, 'label-only': 0, 'too-long': 0, auto: 0, skip: 0 }
const autoLangs = {}
const authorLangs = {}
const skipReason = { short: 0, hangul: 0, lowRelevance: 0 }
const skipByLines = { '1-3': 0, '4-7': 0, '8+': 0 }
const skipSamples = []

function hangulRatio(src) {
  const solid = src.replace(/\s/g, '')
  if (!solid.length) return 0
  const han = solid.match(/[가-힣ㄱ-ㆎ]/g)
  return han ? han.length / solid.length : 0
}

let empty = 0
for (const b of blocks) {
  const src = (b.text || '').replace(/\s+$/, '')
  if (!src) {
    empty++
    continue
  }
  const author = authorLanguage(b.codeClass || '')
  let verdict
  if (author && author.lang) {
    verdict = 'author'
    authorLangs[author.lang] = (authorLangs[author.lang] || 0) + 1
  } else if (author) verdict = 'label-only'
  else if (src.length > MAX_CHARS) verdict = 'too-long'
  else {
    const r = detect(src)
    if (r) {
      verdict = 'auto'
      autoLangs[r.language] = (autoLangs[r.language] || 0) + 1
    } else {
      verdict = 'skip'
      const lines = src.split('\n').length
      skipByLines[lines <= 3 ? '1-3' : lines <= 7 ? '4-7' : '8+']++
      if (src.length < 12) skipReason.short++
      else if (hangulRatio(src) > 0.25) skipReason.hangul++
      else {
        skipReason.lowRelevance++
        if (skipSamples.length < 15 && lines >= 8) {
          skipSamples.push({ lines, head: src.split('\n')[0].slice(0, 72) })
        }
      }
    }
  }
  tally[verdict]++
}

const total = Object.values(tally).reduce((a, b) => a + b, 0)
const pct = (n) => (total ? ((n / total) * 100).toFixed(1) + '%' : '-')
const painted = tally.author + tally.auto
console.log(`코드블록 ${total}개 (수집 ${crawledAt}${empty ? `, 빈 블록 ${empty} 제외` : ''})`)
console.log(`  칠해진다     ${painted}개 (${pct(painted)})  = 글쓴이 지정 ${tally.author} + 자동 감지 ${tally.auto}`)
console.log(`  라벨만       ${tally['label-only']}개 (${pct(tally['label-only'])})  글쓴이가 쓴 언어가 번들에 없다`)
console.log(`  감지 생략    ${tally['too-long']}개 (${pct(tally['too-long'])})  ${MAX_CHARS}자 초과`)
console.log(`  원문 그대로  ${tally.skip}개 (${pct(tally.skip)})  = 짧다 ${skipReason.short} · 한글 ${skipReason.hangul} · 신뢰도 미달 ${skipReason.lowRelevance}`)
console.log(`               줄 수 분포: 1~3줄 ${skipByLines['1-3']} · 4~7줄 ${skipByLines['4-7']} · 8줄+ ${skipByLines['8+']}`)
console.log(`  글쓴이 지정 언어: ${JSON.stringify(authorLangs)}`)
console.log(`  자동 감지 언어:   ${JSON.stringify(autoLangs)}`)
console.log('\n신뢰도 미달인데 8줄 이상인 블록 (첫 줄) — 진짜 코드가 섞여 있으면 임계를 볼 근거다:')
for (const s of skipSamples) console.log(`  ${String(s.lines).padStart(3)}줄  ${s.head}`)
