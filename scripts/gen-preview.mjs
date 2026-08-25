#!/usr/bin/env node
// 스킨 미리보기 이미지 4종을 만든다.
//
// 티스토리는 스킨 **루트**에서 이 파일들을 찾는다 (docs/tistory-skin-reference.txt:51).
// images/ 아래가 아니다 — 그래서 스킨 편집기의 파일업로드 탭으로는 올릴 수 없고,
// 없으면 관리 화면과 스킨 보관함에 깨진 이미지가 뜬다.
//
//   preview.gif      112x84    기본 (아래 셋이 없을 때)
//   preview256.jpg   256x192   사용 중인 스킨
//   preview560.jpg   560x420   스킨 목록
//   preview1600.jpg  1600x1200 스킨 상세
//
// 전부 4:3이다. 로컬 프리뷰의 홈 페이지를 1600x1200으로 찍어 내려받는다.
//
// 왜 빌드에 넣지 않는가 — Chrome과 sips(macOS)가 필요하다. 빌드가 그 둘에 묶이면
// 다른 환경에서 빌드가 통째로 죽는다. 결과물은 src/preview/에 커밋하고,
// 빌드는 그것을 dist/로 복사만 한다.
//
// 사용: npm run preview && node scripts/gen-preview.mjs

import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { readFile, writeFile, mkdir, rm, copyFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import path from 'node:path'
import os from 'node:os'

const exec = promisify(execFile)
const ROOT = path.resolve(import.meta.dirname, '..')
const OUT = path.join(ROOT, 'src', 'preview')
const SRC_PAGE = path.join(ROOT, '_preview', 'pages', 'index.html')
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

// [파일명, 폭, 높이, 포맷]
const SIZES = [
  ['preview1600.jpg', 1600, 1200, 'jpeg'],
  ['preview560.jpg', 560, 420, 'jpeg'],
  ['preview256.jpg', 256, 192, 'jpeg'],
  ['preview.gif', 112, 84, 'gif'],
]

/** 프리뷰 HTML을 "스킨 미리보기용"으로 손본다.
 *
 *  로컬 프리뷰는 개발용이라 스킨에 없는 것들이 들어 있다. 그대로 찍으면
 *  스킨 소개 이미지에 "[광고 자리]" 같은 문구가 박힌다. */
function forPreviewShot(html) {
  // ① 라이트로 고정한다. headless Chrome은 prefers-color-scheme를 dark로 잡는다.
  //    스킨의 기본 캔버스는 근백색이고(DESIGN.md), 티스토리 관리 화면도 밝다.
  html = html.replace(/<html\b([^>]*)>/i, '<html$1 data-theme="light">')

  // ② 프리뷰 전용 광고 자리 표시를 지운다. 스킨에는 치환자만 있고 이 문구는 없다.
  html = html.replace(/<div class="_ad"[^>]*>[\s\S]*?<\/div>/g, '')

  // ③ 공지를 지운다. 픽스처의 공지 2건이 1600x1200의 위쪽 절반을 먹어서,
  //    정작 보여 줘야 할 카드 그리드가 잘린다. 공지 유무는 블로그마다 다르다.
  html = html.replace(/<article class="notice">[\s\S]*?<\/article>/g, '')

  // ④ 썸네일 <img>를 뺀다. 픽스처는 placehold.co의 "thumb" 회색 상자를 쓰는데,
  //    그게 화면의 절반을 차지하면 스킨이 아니라 자리표시자를 소개하는 꼴이 된다.
  //    빼면 그 아래 층인 **기본이미지 도안**(CSS 마스크, 카테고리별 14종)이 드러난다.
  //    실제 블로그에서 대표이미지 없는 글이 보게 될 화면이고, 우리가 그린 것이다.
  html = html.replace(/<img class="thumb-img"[^>]*>/g, '')

  return html
}

async function run() {
  if (!existsSync(SRC_PAGE)) {
    console.error(`  프리뷰가 없다: ${path.relative(ROOT, SRC_PAGE)}\n` +
                  '  먼저 npm run preview 를 돌려라.')
    process.exit(1)
  }
  if (!existsSync(CHROME)) {
    console.error('  Google Chrome을 찾지 못했다. 이 스크립트는 macOS + Chrome 전용이다.\n' +
                  '  결과물은 src/preview/에 커밋되어 있으므로, 스킨을 크게 바꾸지 않았다면\n' +
                  '  다시 만들지 않아도 된다.')
    process.exit(1)
  }

  const tmp = await mkdir(path.join(os.tmpdir(), 'skin-preview-shot'), { recursive: true })
    .then(() => path.join(os.tmpdir(), 'skin-preview-shot'))
  const shot = path.join(tmp, 'shot.png')

  // 손본 HTML은 **원본 옆에** 쓴다. 프리뷰는 style.css와 script.js를 상대경로로
  // 걸기 때문에(../../dist/…), 다른 디렉터리로 옮기면 링크가 통째로 끊긴다.
  // 그러면 스타일 없는 맨 HTML이 찍히는데, 그게 스킨 미리보기로 올라간다.
  const page = path.join(path.dirname(SRC_PAGE), '_shot.html')

  await writeFile(page, forPreviewShot(await readFile(SRC_PAGE, 'utf8')))

  await exec(CHROME, [
    '--headless=new', '--disable-gpu', '--hide-scrollbars',
    '--force-device-scale-factor=1',
    // preferredColorScheme: 1 = light. data-theme와 이중으로 건다 —
    // 시스템 다크에서만 발화하는 규칙이 남아 있으면 한쪽만으로는 새어 나온다.
    '--blink-settings=preferredColorScheme=1',
    '--virtual-time-budget=5000',
    `--screenshot=${shot}`, '--window-size=1600,1200',
    `file://${page}`,
  ]).catch((e) => {
    // Chrome은 성공해도 stderr에 경고를 쏟는다. 파일이 생겼는지로 판단한다.
    if (!existsSync(shot)) throw e
  })

  if (!existsSync(shot)) {
    console.error('  스크린샷이 생성되지 않았다.')
    process.exit(1)
  }

  await rm(OUT, { recursive: true, force: true })
  await mkdir(OUT, { recursive: true })

  for (const [name, w, h, fmt] of SIZES) {
    const dest = path.join(OUT, name)
    await copyFile(shot, dest + '.png')
    // -z는 높이·폭 순서다. 1600x1200에서 4:3을 유지해 내려받으므로 잘림이 없다.
    await exec('sips', ['-s', 'format', fmt, '-z', String(h), String(w),
                        dest + '.png', '--out', dest])
    await rm(dest + '.png')
  }

  await rm(page, { force: true })

  console.log(`\n  src/preview/  ${SIZES.map(([n]) => n).join('  ')}`)
  console.log('  다음: npm run build (dist/ 루트로 복사된다)')
}

run()
