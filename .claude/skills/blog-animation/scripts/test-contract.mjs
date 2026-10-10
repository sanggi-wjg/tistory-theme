#!/usr/bin/env node
// render-gif.mjs의 계약 검사가 실제로 위반을 잡는지 본다.
// 템플릿에서 계약을 하나씩 깬 사본을 만들어 --check가 전부 실패하고, 원본·예시는 전부 통과해야 한다.
// 처음 짠 검사는 Math.random과 CSS transition을 통과시켰고, 고친 판도 늦은 단계에만 생기는 애니메이션과
// 나타나기 구간에만 섞인 난수를 놓쳤다(2026-10-08 코드 리뷰) — 검사를 고치면 이걸 다시 돌린다.
// 예시는 템플릿의 엔진을 글자 그대로 써야 한다 — 엔진을 고쳐도 예시에서 출발한 장면에 안 닿는 것을 막는다.
//
// 변이는 **계약 위반으로** 실패해야 잡힌 것이다 — 그냥 0이 아닌 종료면 Chrome이 안 떠도 여덟 개가 전부 「잡힘」이 된다.
//
//   node .claude/skills/blog-animation/scripts/test-contract.mjs   (npm run test:anim — npm run check·CI가 돈다, 이슈 #105)
import { spawnSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdtempSync, readdirSync, rmSync, chmodSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const assets = join(here, '..', 'assets');
const render = join(here, 'render-gif.mjs');
const template = join(assets, 'template.html');
const src = readFileSync(template, 'utf8');

const MUTATIONS = {
  '난수':          ['var appear = ease(p * 3);', 'var appear = Math.random();'],
  'CSS transition': ['svg { display: block;', 'svg rect { transition: opacity 1s; } svg { display: block;'],
  'capture 누락':   ["document.body.classList.add('capture');", ''],
  '__size 누락':    ['window.__size = [W, H];', ''],
  't 무시':         ['var r = stateAt(t);', 'var r = stateAt(0);'],
  // 아래 셋은 t=0에는 없고 B가 기다리는 단계(약 4~8초)나 짧은 나타나기 구간에만 생긴다
  '늦은 CSS 애니메이션': ["out.push(text(350, 256, '대기',", "out.push('<rect style=\"animation: pulse 1s infinite\" width=\"1\" height=\"1\"/>'); out.push(text(350, 256, '대기',"],
  '늦은 SMIL':     ["out.push(text(350, 256, '대기',", "out.push('<rect width=\"1\" height=\"1\"><animate attributeName=\"x\" from=\"0\" to=\"9\" dur=\"1s\"/></rect>'); out.push(text(350, 256, '대기',"],
  '나타나기 구간의 난수': ["var o = (s.fresh === 'lockA' || s.fresh === 'lockB') ? appear : 1;", "var o = (s.fresh === 'lockA' || s.fresh === 'lockB') ? (p < 0.33 ? Math.random() : 1) : 1;"],
};

// render-gif는 Chrome·CDP가 멈추거나 죽으면 Chrome을 다시 띄우고 stderr에 ↻를 남긴다(이슈 #135). 다시 띄운 횟수를
// 모아 끝에 적는다 — 재시도가 조용히 실패를 삼키면 「가끔 느리다」가 「늘 멈춘다」로 자라도 아무도 모른다
let retries = 0, planned = 0;
const check = (file, env) => {
  const r = spawnSync('node', [render, file, '--check'], { encoding: 'utf8', env: env ? { ...process.env, ...env } : process.env });
  retries += (r.stderr.match(/^↻ /gm) || []).length;
  return r;
};
const work = mkdtempSync(join(tmpdir(), 'anim-contract-'));
let bad = 0;

for (const file of [template, ...readdirSync(join(assets, 'examples')).map((f) => join(assets, 'examples', f))]) {
  const r = check(file);
  const ok = r.status === 0;
  if (!ok) bad++;
  console.log(`${ok ? '✓' : '✗'} 기준선 통과   ${file.replace(assets + '/', '')}${ok ? '' : '\n    ' + (r.stderr || r.stdout).trim()}`);
}
// 엔진 칸과 <style>이 템플릿과 같은가
const ENGINE = '  // 엔진 — 보통은 손대지 않는다';
const engineOf = (h) => h.slice(h.indexOf(ENGINE));
const styleOf = (h) => h.slice(h.indexOf('<style>'), h.indexOf('</style>'));
for (const f of readdirSync(join(assets, 'examples'))) {
  const h = readFileSync(join(assets, 'examples', f), 'utf8');
  const same = h.includes(ENGINE) && engineOf(h) === engineOf(src) && styleOf(h) === styleOf(src);
  if (!same) bad++;
  console.log(`${same ? '✓' : '✗'} 엔진 동일     examples/${f}${same ? '' : ' — 엔진 칸이나 <style>이 템플릿과 다르다. 템플릿 엔진을 그대로 옮긴다'}`);
}
for (const [name, [from, to]] of Object.entries(MUTATIONS)) {
  if (src.split(from).length !== 2) { console.log(`✗ 변이 「${name}」: 템플릿에서 원문을 못 찾았다 — 변이를 갱신한다`); bad++; continue; }
  const f = join(work, `${name}.html`);
  writeFileSync(f, src.replace(from, to));
  const r = check(f);
  const caught = r.status !== 0 && r.stderr.includes('계약 위반');
  if (!caught) bad++;
  console.log(`${caught ? '✓' : '✗'} 변이 잡힘   「${name}」${caught ? ''
    : r.status === 0 ? ' — 계약 위반인데 통과했다' : ' — 계약 위반이 아닌 이유로 실패했다: ' + (r.stderr || r.stdout).trim()}`);
}
// ── 다시 띄우기가 실제로 동작하는가 — 처음 N번은 바로 죽는 가짜 Chrome으로 본다(이슈 #135).
// 멈춤(무응답)은 재현에 10초씩 걸려 여기서는 「뜨기 전에 끝났다」로 같은 갈래(InfraError → 다시 띄움)를 지난다
// 진짜 Chrome은 render-gif에게 묻는다 — 찾는 규칙을 여기에 베끼면 둘이 갈렸을 때 가짜가 엉뚱한 것을 부른다
const realChrome = spawnSync('node', [render, '--print-chrome'], { encoding: 'utf8' }).stdout.trim();
const flaky = join(work, 'flaky-chrome.sh');
writeFileSync(flaky, '#!/bin/sh\nn=$(cat "$FLAKY_COUNTER" 2>/dev/null || echo 0)\necho $((n+1)) > "$FLAKY_COUNTER"\n'
  + '[ "$n" -lt "$FLAKY_FAIL_FIRST" ] && exit 3\nexec "$FLAKY_REAL" "$@"\n');
chmodSync(flaky, 0o755);
const flakyRun = (failFirst, tag) => {
  const counter = join(work, `count-${tag}`);
  const before = retries;
  const r = check(template, { CHROME: flaky, FLAKY_COUNTER: counter, FLAKY_FAIL_FIRST: String(failFirst), FLAKY_REAL: realChrome });
  const retried = retries - before;
  planned += Math.min(retried, failFirst);   // 일부러 죽인 횟수만 계획된 것이다 — 그 뒤 진짜 Chrome이 멈춘 것은 계획 밖
  // 가짜가 한 번도 안 불렸으면(render-gif가 먼저 멈췄다) 계수 파일이 없다 — 예외로 죽지 말고 0으로 보고 ✗로 남긴다
  return { r, launches: existsSync(counter) ? Number(readFileSync(counter, 'utf8')) : 0, retried };
};
{
  const { r, launches, retried } = flakyRun(1, 'once');
  // 두 번째부터는 진짜 Chrome이라 그것이 또 멈출 수 있다(#135) — 횟수를 못박지 않고 「통과했고 ↻ = 띄움 − 1」만 본다
  const ok = r.status === 0 && launches >= 2 && retried === launches - 1;
  if (!ok) bad++;
  console.log(`${ok ? '✓' : '✗'} 다시 띄움   첫 Chrome이 죽어도 두 번째로 통과한다 (띄움 ${launches}회 · ↻ ${retried})${ok ? '' : '\n    ' + (r.stderr || r.stdout).trim()}`);
}
{
  const { r, launches, retried } = flakyRun(99, 'always');
  const ok = r.status !== 0 && launches === 3 && retried === 2 && !r.stderr.includes('계약 위반') && r.stderr.includes('3번 띄워도');
  if (!ok) bad++;
  console.log(`${ok ? '✓' : '✗'} 다시 띄움   매번 죽으면 3번에서 멈추고 계약 위반으로 읽히지 않는다 (띄움 ${launches}회 · ↻ ${retried})${ok ? '' : '\n    ' + (r.stderr || r.stdout).trim()}`);
}
// 일부러 죽여서 낸 ↻는 빼고 나머지만 보고한다 — 계획된 수를 3으로 가정하면 검사가 어긋날 때 수가 거짓이 된다
const unplanned = retries - planned;
console.log(unplanned ? `↻ 계획에 없던 Chrome 재시작 ${unplanned}회 — 통과는 했지만 Chrome·CDP가 멈췄다는 뜻이다. 늘면 이슈 #135를 다시 본다`
  : '✓ 계획에 없던 Chrome 재시작 0회');
rmSync(work, { recursive: true, force: true });
process.exit(bad ? 1 : 0);
