// 글 초안이 어느 깊이에 있어도 커밋 대상에서 빠지는가 — 이슈 #108.
//
//   node scripts/test-gitignore-drafts.mjs
//
// 저장소가 공개이고 초안에는 회사 코드 이야기가 들어갈 수 있다(.gitignore 「블로그 글 초안」). 처음 규칙
// `/posts/_drafts`는 최상위만 막아, 초안을 `posts/<카테고리>/…/_drafts/`에 두면 `git status`에 `??`로
// 뜰 뿐 다른 신호 없이 `git add -A` 한 번에 올라갈 수 있었다 — 2026-10-08 처음 정리했을 때 실제로 그 구조였다.
//
// 두 가지다.
//   ① 빈 임시 저장소에 이 저장소의 .gitignore만 복사하고 **실제 파일**을 만든 뒤, 사고가 나는 명령
//      `git add -A`를 --dry-run으로 돌려 무엇이 올라가는지 본다. 초안은 하나도 없어야 하고, 올린 글은
//      전부 있어야 한다(규칙을 넓히다 글까지 막으면 그것도 조용한 실패다). 전역·시스템 git 설정은 끈다 —
//      사용자의 전역 무시 목록이 초안을 대신 막아 주면 초록불이 이 저장소 규칙의 것이 아니게 된다.
//   ② 이 저장소에서 이미 커밋된 posts/ 파일 중 무시 규칙에 걸리는 것이 0인가.
import { execFileSync } from 'node:child_process'
import { copyFileSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')

const DRAFTS = [
  'posts/_drafts/2026-10-08-x/draft.md',
  'posts/데이터베이스/MySQL/_drafts/alter-table/draft.md', // 이슈 #108이 실제로 겪은 구조
  'posts/데이터베이스/MySQL/_drafts/alter-table/assets/a.gif',
  'posts/백엔드/_drafts/note.md',
  'posts/a/b/c/_drafts/d.md',
]
const POSTS = [
  'posts/데이터베이스/MySQL/2026-10-08-deadlock/index.md',
  'posts/데이터베이스/MySQL/2026-10-08-deadlock/assets/a.gif',
  'posts/백엔드/2026-10-09-di/index.md',
  'posts/a/drafts/index.md', // 밑줄 없는 이름은 초안 폴더가 아니다
]

let fails = 0
function ok(cond, msg) {
  console.log(`${cond ? '✓' : '✗'} ${msg}`)
  if (!cond) fails++
}

const env = { ...process.env, GIT_CONFIG_GLOBAL: '/dev/null', GIT_CONFIG_NOSYSTEM: '1' }
const git = (cwd, args) => execFileSync('git', ['-c', 'core.quotePath=false', ...args], { cwd, env, encoding: 'utf8' })

/* ── ① 임시 저장소에서 git add -A가 무엇을 올리는가 ── */
const tmp = mkdtempSync(join(tmpdir(), 'gitignore-drafts-'))
try {
  git(tmp, ['init', '-q'])
  copyFileSync(join(ROOT, '.gitignore'), join(tmp, '.gitignore'))
  for (const p of [...DRAFTS, ...POSTS]) {
    mkdirSync(dirname(join(tmp, p)), { recursive: true })
    writeFileSync(join(tmp, p), 'x\n')
  }
  const added = new Set(
    git(tmp, ['add', '-A', '--dry-run'])
      .split('\n')
      .map((l) => l.match(/^add '(.*)'$/))
      .filter(Boolean)
      .map((m) => m[1]),
  )
  ok(added.has('.gitignore'), `dry-run 출력을 읽는다(.gitignore가 보인다 — 못 읽으면 아래가 모두 공허하게 통과한다)`)
  for (const p of DRAFTS) ok(!added.has(p), `초안이 올라가지 않는다 — ${p}`)
  for (const p of POSTS) ok(added.has(p), `올린 글은 올라간다 — ${p}`)
} finally {
  rmSync(tmp, { recursive: true, force: true })
}

/* ── ② 이미 커밋된 글이 무시 규칙에 걸리지 않는가 ── */
const tracked = git(ROOT, ['ls-files', '--', 'posts']).split('\n').filter(Boolean)
const shadowed = git(ROOT, ['ls-files', '-ci', '--exclude-standard', '--', 'posts']).split('\n').filter(Boolean)
ok(tracked.length > 0, `커밋된 글 파일을 읽는다 (${tracked.length}개)`)
ok(shadowed.length === 0, `커밋된 글 중 무시 규칙에 걸리는 것 0 (${shadowed.length}${shadowed.length ? ': ' + shadowed.join(', ') : ''})`)

console.log(fails ? `\n실패 ${fails}건` : '\n실패 0건')
process.exit(fails ? 1 : 0)
