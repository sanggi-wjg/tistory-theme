// code.js의 감지 규칙(detect)을 실제 highlight.js로 돌려 임계를 검증한다.
// 브라우저 없이 확인할 수 있는 유일한 부분이라, 임계를 손볼 때마다 이걸 돌린다.
//
//   node scripts/probe-code-detect.mjs
//
// 사본이 아니라 src/js/code.js의 detect를 그대로 부른다 — 규칙이 갈라지지 않는다.

import { detect, authorLanguage } from '../src/js/code.js'

/* ── 칠해야 하는 것 (진짜 코드) ── */
const POSITIVE = {
  'py-mid': `import os
from datetime import datetime

def main():
    now = datetime.now()
    for f in os.listdir('.'):
        if f.endswith('.py'):
            print(f, now)

if __name__ == '__main__':
    main()`,
  'py-korean-comment': `# 사용자 목록을 가져온다
def get_users(conn):
    # 커서를 열고 조회한다
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM users WHERE active = 1")
    rows = cur.fetchall()
    return [dict(id=r[0], name=r[1]) for r in rows]`,
  'py-class': `class Repo:
    def __init__(self, conn):
        self.conn = conn

    def find(self, id):
        return self.conn.get(id)`,
  bash: `#!/bin/bash
set -euo pipefail
for f in *.log; do
  gzip -9 "$f"
  echo "compressed $f"
done
rm -rf /tmp/cache`,
  sql: `SELECT u.id, u.name, count(o.id) AS cnt
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.created_at > '2024-01-01'
GROUP BY u.id, u.name
ORDER BY cnt DESC
LIMIT 10;`,
  json: `{
  "name": "sanggi",
  "version": "1.0.0",
  "dependencies": { "highlight.js": "^11.11.0" },
  "scripts": { "build": "node scripts/build.mjs" }
}`,
  'yaml-compose': `version: "3.8"
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"`,
  // 실제 프리뷰 본문에 들어 있는 조각 (짧은 설정 블록)
  'yaml-short': `spring:
  datasource:
    hikari:
      max-lifetime: 240000
      keepalive-time: 120000`,
  kotlin: `data class User(val id: Long, val name: String)

fun main() {
    val users = listOf(User(1, "a"), User(2, "b"))
    users.filter { it.id > 1 }.forEach { println(it.name) }
}`,
  java: `public class Hello {
    public static void main(String[] args) {
        System.out.println("hello");
    }
}`,
  go: `package main

import "fmt"

func main() {
	nums := []int{1, 2, 3}
	for i, n := range nums {
		fmt.Println(i, n)
	}
}`,
  xml: `<dependency>
  <groupId>org.springframework</groupId>
  <artifactId>spring-core</artifactId>
  <version>5.3.9</version>
</dependency>`,
}

/* ── 칠하면 안 되는 것 ── */
const NEGATIVE = {
  'korean-memo': `설치 순서는 다음과 같다.
먼저 패키지를 내려받고, 압축을 푼 뒤에 설정 파일을 수정한다.
그다음 서비스를 재시작하면 반영된다.
주의: 반드시 백업을 먼저 받아야 한다.`,
  'korean-memo-mixed': `아래 명령을 순서대로 실행한다.
서버에 접속한 다음 디렉터리를 확인하고,
설정 파일에서 포트 번호를 바꾼 뒤에
서비스를 재시작하면 된다. 확인은 로그로 한다.`,
  // 프리뷰 본문의 실제 블록. data-ke-language="javascript"로 잘못 붙어 있다.
  'jcmd-output': `$ jcmd 1 VM.native_memory summary
Total: reserved=2841MB, committed=1974MB
-  Internal (reserved=612MB, committed=612MB)
-      Thread (reserved=318MB, committed=318MB)`,
  'plain-output': `Total 12 files
  ok      3
  failed  9
elapsed 1.2s`,
  'py-traceback': `Traceback (most recent call last):
  File "app.py", line 12, in <module>
    main()
ValueError: invalid literal for int() with base 10: 'x'`,
  'java-trace': `Exception in thread "main" java.lang.NullPointerException
	at com.example.Service.run(Service.java:42)
	at com.example.Main.main(Main.java:11)`,
  'nginx-log': `127.0.0.1 - - [10/Oct/2024:13:55:36 +0900] "GET /api/v1/users HTTP/1.1" 200 1043
127.0.0.1 - - [10/Oct/2024:13:55:37 +0900] "POST /api/v1/login HTTP/1.1" 401 22`,
  'english-prose': `The connection pool keeps sockets open until the database closes them.
When that happens the client does not notice, and the next borrow fails.
Setting a shorter lifetime on the client side avoids the race entirely.`,
  'ls-output': `total 48
drwxr-xr-x  5 raynor staff   160 Aug 25 13:09 dist
-rw-r--r--  1 raynor staff  1140 Aug 25 13:29 index.html`,
  'kv-output': `Total: reserved=2841MB, committed=1974MB
Internal: reserved=612MB, committed=612MB
Thread: reserved=318MB, committed=318MB`,
  'url-list': `https://example.com/a
https://example.com/b
https://example.com/c`,
  'jvm-flags': `-Xms2g -Xmx2g
-XX:+UseG1GC
-XX:MaxMetaspaceSize=256m`,
  'curl-headers': `HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 42`,
  'one-liner': '$ docker ps -a',
}

/* ── 알려진 한계 (실패로 세지 않는다) ──
 * 코드가 아닌 영문 텍스트의 relevance는 줄당 약 1씩 쌓인다. 길이에 비례한 문턱을
 * 두면 막을 수 있지만, 그러면 파이썬(11줄 8)·Go(10줄 9)를 통째로 놓친다.
 * 이 블로그의 코드블록 149개가 파이썬이므로 그 대가가 더 크다. */
const KNOWN_GAP = {
  'nginx x30': Array.from({ length: 30 }, (_, i) => `127.0.0.1 - - [10/Oct/2024:13:55:${i} +0900] "GET /api/v1/users HTTP/1.1" 200 104${i}`).join('\n'),
  'prose x30': Array.from({ length: 30 }, (_, i) => `The connection pool keeps sockets open until the database closes them (${i}).`).join('\n'),
}

const w = [22, 5, 9, 6, 22]
let bad = 0

function section(title, samples, want) {
  console.log('\n── ' + title + ' ──')
  for (const [name, raw] of Object.entries(samples)) {
    const src = raw.replace(/\s+$/, '')
    const r = detect(src)
    const got = r ? 'highlight' : 'skip'
    const ok = want === null || got === want
    if (!ok) bad++
    console.log(
      [
        name,
        String(src.split('\n').length),
        r ? r.language : '-',
        r ? String(Math.round(r.relevance * 10) / 10) : '-',
        ok ? got : got + ' ✗ (기대 ' + want + ')',
      ]
        .map((c, i) => c.padEnd(w[i]))
        .join('')
    )
  }
}

console.log(['sample', 'ln', 'lang', 'rel', 'result'].map((h, i) => h.padEnd(w[i])).join(''))
section('칠해야 하는 것', POSITIVE, 'highlight')
section('칠하면 안 되는 것', NEGATIVE, 'skip')
section('알려진 한계 — 긴 영문 로그·산문 (실패로 세지 않음)', KNOWN_GAP, null)

/* ── 글쓴이가 쓴 언어 (결정 43) ──────────────────────────────────────
 *
 * `authorLanguage()`는 **어떤 클래스를 믿는가**를 정하는 함수다. 여기가 틀리면
 * 에디터가 박은 `reasonml`·`angelscript` 같은 쓰레기를 다시 믿게 되고,
 * 화면에는 그럴듯한 라벨이 붙어 **틀린 줄도 모른다.** 그래서 표본으로 고정한다.
 *
 * 형식: [클래스 문자열, 기대 lang, 기대 label] — 'NONE'은 null 반환을 뜻한다.
 */
const AUTHOR_CASES = [
  // 글쓴이가 쓴 것 — 번들에 있다
  ['language-python', 'python', 'Python'],
  ['language-Kotlin', 'kotlin', 'Kotlin'], // 대소문자 무시
  ['language-yml', 'yaml', 'YAML'], // 별칭
  ['language-py', 'python', 'Python'],
  ['hljs language-sql', 'sql', 'SQL'], // 다른 클래스와 섞여 있어도
  // 언어인 줄은 알지만 번들에 없다 — 칠하지 않고 라벨만
  ['language-typescript', null, 'TypeScript'],
  ['language-dockerfile', null, 'Dockerfile'],
  ['language-c++', null, 'C++'],
  // 라벨을 일부러 비우는 것 — "평문"은 정보가 없다
  ['language-text', null, null],
  // 언어가 아닌 이름 — 아무것도 하지 않고 자동 감지로 넘어간다.
  // ⚠ info·warning은 콜아웃 표식 후보다. 여기서 "Info" 라벨이 붙으면 안 된다.
  ['language-info', 'NONE', 'NONE'],
  ['language-warning', 'NONE', 'NONE'],
  ['language-nosuchlang', 'NONE', 'NONE'],
  // 에디터가 붙이는 형태 — **절대 걸리면 안 된다** (language- 접두가 없다)
  ['reasonml', 'NONE', 'NONE'],
  ['angelscript', 'NONE', 'NONE'],
  ['isbl', 'NONE', 'NONE'],
  ['', 'NONE', 'NONE'],
]

console.log('\n── 글쓴이가 쓴 언어 (authorLanguage) ──')
for (const [cls, wantLang, wantLabel] of AUTHOR_CASES) {
  const r = authorLanguage(cls)
  const gotLang = r === null ? 'NONE' : r.lang
  const gotLabel = r === null ? 'NONE' : r.label
  const ok = gotLang === wantLang && gotLabel === wantLabel
  if (!ok) bad++
  console.log(
    [
      cls || '(빈 클래스)',
      String(gotLang),
      String(gotLabel),
      ok ? 'ok' : '✗ 기대 ' + wantLang + ' / ' + wantLabel,
    ]
      .map((c, i) => c.padEnd([24, 10, 14, 30][i]))
      .join('')
  )
}

const total =
  Object.keys(POSITIVE).length + Object.keys(NEGATIVE).length + AUTHOR_CASES.length
console.log('\n어긋난 표본 ' + bad + '개 / ' + total)
process.exit(bad ? 1 : 0)
