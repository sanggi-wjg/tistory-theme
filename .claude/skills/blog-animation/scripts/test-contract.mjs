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
import { readFileSync, writeFileSync, mkdtempSync, readdirSync, rmSync } from 'node:fs';
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

const check = (file) => spawnSync('node', [render, file, '--check'], { encoding: 'utf8' });
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
rmSync(work, { recursive: true, force: true });
process.exit(bad ? 1 : 0);
