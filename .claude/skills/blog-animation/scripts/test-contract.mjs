#!/usr/bin/env node
// render-gif.mjs의 계약 검사가 실제로 위반을 잡는지 본다.
// 템플릿에서 계약을 하나씩 깬 사본을 만들어 --check가 전부 실패하고, 원본·예시는 전부 통과해야 한다.
// 처음 짠 검사는 Math.random과 CSS transition을 통과시켰다(2026-10-08) — 검사를 고치면 이걸 다시 돌린다.
//
//   node .claude/skills/blog-animation/scripts/test-contract.mjs
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
for (const [name, [from, to]] of Object.entries(MUTATIONS)) {
  if (src.split(from).length !== 2) { console.log(`✗ 변이 「${name}」: 템플릿에서 원문을 못 찾았다 — 변이를 갱신한다`); bad++; continue; }
  const f = join(work, `${name}.html`);
  writeFileSync(f, src.replace(from, to));
  const r = check(f);
  const caught = r.status !== 0;
  if (!caught) bad++;
  console.log(`${caught ? '✓' : '✗'} 변이 잡힘   「${name}」${caught ? '' : ' — 계약 위반인데 통과했다'}`);
}
rmSync(work, { recursive: true, force: true });
process.exit(bad ? 1 : 0);
