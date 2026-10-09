// dist/·_preview/ 동시 쓰기 시험 — 이슈 #100.
//
//   node scripts/test-build-lock.mjs      (npm run test:build-lock)
//
// 빌드(scripts/build.mjs)와 프리뷰 렌더(render.py)를 **실제로 겹쳐** 돌리고, 그동안 다른 쪽이 산출물을 읽는다.
// 2026-10-09 옛 빌드로 잰 것: 겹친 빌드 12회 중 4회가 ENOTEMPTY·ENOENT로 죽었고, 빌드 중 dist/style.css가
// **없는 순간**을 10/10 봤다(rm(DIST)부터 하므로 — 「빌드 중 린트가 빈 dist/를 읽는다」). 그래서 본다:
//   ① 겹친 실행이 모두 0으로 끝난다(잠금으로 줄을 선다)
//   ② 도는 동안 읽은 dist/style.css·_preview/pages/index.html이 한 번도 없거나 잘리지 않았다(파일마다 원자 교체)
//   ③ 끝난 뒤 산출물 목록이 단독 실행과 같다
//   ④ 죽은 프로세스의 잠금은 치우고 진행한다 · 살아 있는 잠금은 기다리다 시간이 넘으면 크게 실패한다
// 옛 코드에서 ②가 매 회차 깨진다 — 이 검사가 빨간불을 켤 수 있다는 근거다.

import { spawn } from 'node:child_process'
import { existsSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs'
import path from 'node:path'

const ROOT = process.cwd()
const ROUNDS = 5
const BUILD = ['node', ['scripts/build.mjs']]
const RENDER = ['python3', ['.claude/skills/skin-preview/scripts/render.py']]
const LOCKS = { build: path.join(ROOT, '.dist.lock'), render: path.join(ROOT, '.preview.lock') }

let fails = 0
const report = (ok, label, detail = '') => {
  console.log(`  ${ok ? '✅' : '❌'}  ${label}${detail ? ' — ' + detail : ''}`)
  if (!ok) fails++
}

function run([cmd, args], env = {}) {
  return new Promise((resolve) => {
    const p = spawn(cmd, args, { cwd: ROOT, env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'] })
    let err = ''
    p.stdout.resume()
    p.stderr.on('data', (d) => { err += d })
    p.on('close', (code) => resolve({ code, err }))
  })
}

function listing(dir) {
  const out = []
  const walk = (d, rel) => {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      if (e.isDirectory()) walk(path.join(d, e.name), rel + e.name + '/')
      else out.push(rel + e.name)
    }
  }
  if (existsSync(dir)) walk(dir, '')
  return out.sort().join('\n')
}

// 겹친 실행 둘이 도는 동안 file을 계속 읽는다. 없음·기준과 다른 내용(잘림)을 센다
async function race(job, file, ref) {
  const done = Promise.all([run(job), run(job)])
  let finished = false
  done.then(() => { finished = true })
  let reads = 0, missing = 0, partial = 0
  while (!finished) {
    try {
      const s = readFileSync(file, 'utf8')
      reads++
      if (s !== ref) partial++
    } catch (e) {
      if (e.code !== 'ENOENT') throw e
      missing++
    }
    await new Promise((r) => setImmediate(r))
  }
  return { results: await done, reads, missing, partial }
}

async function overlap(name, job, file, outDir) {
  const first = await run(job)
  if (first.code !== 0) { report(false, `${name} 단독 실행`, first.err.trim().split('\n').pop()); return }
  const ref = readFileSync(file, 'utf8')
  const refList = listing(outDir)
  let bad = 0, missing = 0, partial = 0, reads = 0, lastErr = ''
  for (let i = 0; i < ROUNDS; i++) {
    const r = await race(job, file, ref)
    for (const x of r.results) if (x.code !== 0) { bad++; lastErr = x.err.trim().split('\n').pop() }
    missing += r.missing; partial += r.partial; reads += r.reads
  }
  const rel = path.relative(ROOT, file)
  report(bad === 0, `① ${name} 둘을 겹쳐 ${ROUNDS}회 — 모두 0으로 끝난다`, bad ? `${bad}/${ROUNDS * 2} 실패: ${lastErr}` : '')
  report(missing === 0 && partial === 0, `② 도는 동안 ${rel}이 없거나 잘린 적이 없다`,
    `읽기 ${reads}회 · 없음 ${missing} · 잘림 ${partial}`)
  report(listing(outDir) === refList, `③ 끝난 뒤 ${path.relative(ROOT, outDir)}/ 목록이 단독 실행과 같다`)
}

async function locks(name, job, lock, outFile) {
  // 죽은 프로세스의 잠금 — 그 pid는 방금 끝난 자식이다
  const dead = await new Promise((resolve) => { const p = spawn('node', ['-e', '']); p.on('close', () => resolve(p.pid)) })
  writeFileSync(lock, String(dead))
  const a = await run(job)
  report(a.code === 0 && !existsSync(lock), `④ ${name} — 죽은 pid ${dead}의 잠금을 치우고 진행한다`,
    a.code ? a.err.trim().split('\n').pop() : existsSync(lock) ? '잠금이 남았다' : '')
  // 살아 있는 잠금(이 시험 프로세스) — 기다리다 시간이 넘으면 0이 아닌 코드로 끝나야 한다
  writeFileSync(lock, String(process.pid))
  const b = await run(job, { LOCK_TIMEOUT_MS: '400' })
  const held = existsSync(lock) && readFileSync(lock, 'utf8').trim() === String(process.pid)
  // 남이 쓰는 중인 산출물은 건드리지 않는다 — 「실패하면 dist/를 지운다」는 잠금을 쥔 뒤의 실패에만 해당한다
  const kept = existsSync(outFile)
  report(b.code !== 0 && held && kept && b.err.includes(String(process.pid)),
    `④ ${name} — 살아 있는 잠금(pid ${process.pid})이면 기다리다 크게 실패하고 남의 잠금·산출물을 건드리지 않는다`,
    `rc=${b.code}${held ? '' : ' · 잠금이 사라졌다'}${kept ? '' : ' · ' + path.relative(ROOT, outFile) + '이 사라졌다'}`)
  rmSync(lock, { force: true })
}

try {
  await overlap('빌드', BUILD, path.join(ROOT, 'dist', 'style.css'), path.join(ROOT, 'dist'))
  await overlap('프리뷰 렌더', RENDER, path.join(ROOT, '_preview', 'pages', 'index.html'), path.join(ROOT, '_preview'))
  await locks('빌드', BUILD, LOCKS.build, path.join(ROOT, 'dist', 'style.css'))
  await locks('프리뷰 렌더', RENDER, LOCKS.render, path.join(ROOT, '_preview', 'pages', 'index.html'))
} finally {
  for (const l of Object.values(LOCKS)) {
    if (existsSync(l) && readFileSync(l, 'utf8').trim() === String(process.pid)) rmSync(l, { force: true })
  }
}
// 마지막 상태를 단독 실행으로 맞춰 둔다 — 뒤에 오는 검사가 온전한 산출물을 읽게
await run(BUILD)
await run(RENDER)
console.log(`\n실패 ${fails}건`)
process.exit(fails ? 1 : 0)
