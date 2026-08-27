// 파비콘·블로그 아이콘 생성 — DECISIONS.md 결정 49
//
//   node scripts/gen-icons.mjs      (npm run icons)
//
// 원본 src/assets/brand/favicon-src-150.png(인디고 바탕 + 흰 `>_`)을 스킨의 --link 파랑으로
// 다시 칠해 세 파일을 만든다. 셋 다 **스킨이 아니라 티스토리 관리 화면**에 올린다 —
// skin.html은 <link rel="icon">을 내보내지 않고(티스토리가 주입한다) images/에는 기본
// 이미지 말고 두지 않는다(결정 6).
//
//   favicon.ico          관리 → 블로그 → 파비콘.  16·32·48 엔트리(PNG 압축)
//   icon-48.png          관리 → 블로그 → 아이콘.  댓글·방명록 닉네임 옆(≤48px)
//   apple-touch-icon.png 예비. iOS 홈 화면 180px — 150에서 1.2배 확대
//
// 색을 바꾸는 방법: 원본은 인디고(#6366f1)와 흰색 두 색과 그 사이 안티앨리어싱뿐이다.
// 인디고→파랑 단순 치환이면 글리프 가장자리의 중간색이 그대로 남아 인디고 테가 생긴다.
// 픽셀마다 「얼마나 흰가」 t(빨강 채널이 인디고 99 → 흰 255로 단조 증가)를 재서
// --link와 흰색 사이로 다시 섞는다. 알파는 그대로 둔다(둥근 모서리).
import sharp from 'sharp'
import fs from 'node:fs'
import path from 'node:path'

const DIR = 'src/assets/brand'
const SRC = path.join(DIR, 'favicon-src-150.png')
const LINK = [0x00, 0x64, 0xda]   // tokens.css --link (라이트). 바꾸면 여기만
const INDIGO_R = 99               // 원본 바탕색 #6366f1의 빨강 채널
const MAX_ICO_BYTES = 8 * 1024

const { data, info } = await sharp(SRC).ensureAlpha().raw().toBuffer({ resolveWithObject: true })
for (let i = 0; i < data.length; i += 4) {
  if (data[i + 3] === 0) continue
  const t = Math.min(1, Math.max(0, (data[i] - INDIGO_R) / (255 - INDIGO_R)))
  for (let c = 0; c < 3; c++) data[i + c] = Math.round(LINK[c] + (255 - LINK[c]) * t)
}
const base = () => sharp(data, { raw: { width: info.width, height: info.height, channels: 4 } })
const png = (s) => base().resize(s, s, { kernel: 'lanczos3' }).png({ compressionLevel: 9 }).toBuffer()

// ICO 컨테이너 — 엔트리를 PNG로 넣는다(모든 현행 브라우저가 읽는다). BMP보다 1/10 크기.
function ico(entries) {
  const head = Buffer.alloc(6); head.writeUInt16LE(0, 0); head.writeUInt16LE(1, 2); head.writeUInt16LE(entries.length, 4)
  const dir = Buffer.alloc(16 * entries.length)
  let off = 6 + dir.length
  entries.forEach(({ size, buf }, i) => {
    const o = 16 * i
    dir.writeUInt8(size >= 256 ? 0 : size, o); dir.writeUInt8(size >= 256 ? 0 : size, o + 1)
    dir.writeUInt8(0, o + 2); dir.writeUInt8(0, o + 3)
    dir.writeUInt16LE(1, o + 4); dir.writeUInt16LE(32, o + 6)
    dir.writeUInt32LE(buf.length, o + 8); dir.writeUInt32LE(off, o + 12)
    off += buf.length
  })
  return Buffer.concat([head, dir, ...entries.map((e) => e.buf)])
}

const sizes = [16, 32, 48]
const entries = []
for (const size of sizes) entries.push({ size, buf: await png(size) })
const out = {
  'favicon.ico': ico(entries),
  'icon-48.png': entries[2].buf,
  'apple-touch-icon.png': await png(180),
}
const problems = []
for (const [name, buf] of Object.entries(out)) {
  fs.writeFileSync(path.join(DIR, name), buf)
  console.log(`  ${name.padEnd(22)} ${buf.length}B`)
}
if (out['favicon.ico'].length > MAX_ICO_BYTES) problems.push(`favicon.ico ${out['favicon.ico'].length}B > ${MAX_ICO_BYTES}B`)
if (problems.length) { console.error('✗ ' + problems.join('\n✗ ')); process.exit(1) }
console.log(`\n  ${Object.keys(out).length}개 → ${DIR}/  (관리 화면에 올린다 — USAGE.md 「파비콘·아이콘」)`)
