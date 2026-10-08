#!/usr/bin/env node
// 설명 애니메이션 HTML을 GIF로 굽는다. Chrome 하나를 CDP로 붙잡고 window.__render(t)를
// 프레임마다 불러 스크린샷을 찍은 뒤 ffmpeg 팔레트 두 패스로 묶는다.
//
//   node render-gif.mjs <html> [--out x.gif] [--fps 12] [--theme light] [--scale 1.5]
//   node render-gif.mjs <html> --stills 3,10.5,21     # 정지 장면만 PNG로 (GIF는 안 굽는다)
//   node render-gif.mjs <html> --check                # 계약 검사만
//
// 프레임마다 Chrome을 새로 띄우면 340장에 10분이 넘고 중간에 멈춘다(2026-10-08 실측, 338/340에서 정지).
// 그래서 브라우저 하나에 장면만 바꿔 그린다.
import { spawn, spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync, statSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve, dirname, basename, extname } from 'node:path';

const args = process.argv.slice(2);
const html = args.find((a) => !a.startsWith('--') && !isFlagValue(a));
function isFlagValue(a) { const i = args.indexOf(a); return i > 0 && ['--out', '--fps', '--theme', '--scale', '--stills'].includes(args[i - 1]); }
function opt(name, dflt) { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; }

if (!html) {
  console.error('사용: node render-gif.mjs <html> [--out x.gif] [--fps 12] [--theme light|dark] [--scale 1.5] [--stills t1,t2] [--check]');
  process.exit(2);
}
const HTML = resolve(html);
if (!existsSync(HTML)) fail(`HTML이 없다: ${HTML}`);
const FPS = Number(opt('--fps', 12));
const THEME = opt('--theme', 'light');
const SCALE = Number(opt('--scale', 1.5));
const STILLS = opt('--stills', null);
const CHECK_ONLY = args.includes('--check');
const OUT = resolve(opt('--out', join(dirname(HTML), basename(HTML, extname(HTML)) + '.gif')));

const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
if (!existsSync(CHROME)) fail(`Chrome이 없다: ${CHROME} (환경변수 CHROME으로 경로를 준다)`);
if (typeof WebSocket !== 'function') fail('Node 22 이상이 필요하다 (내장 WebSocket)');
if (!STILLS && !CHECK_ONLY && spawnSync('ffmpeg', ['-version']).status !== 0) fail('ffmpeg가 없다 — brew install ffmpeg');

function fail(msg) { console.error('✗ ' + msg); process.exit(1); }

// ── Chrome + CDP
const profile = mkdtempSync(join(tmpdir(), 'anim-profile-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--disable-gpu', '--hide-scrollbars', '--remote-debugging-port=0',
  `--user-data-dir=${profile}`, 'about:blank',
], { stdio: ['ignore', 'ignore', 'pipe'] });
// Chrome은 죽는 중에도 프로필에 쓴다 — 지우기는 재시도하고, 그래도 남으면 임시 폴더라 둔다
const cleanup = () => {
  try { chrome.kill('SIGKILL'); } catch {}
  try { rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch {}
};
process.on('exit', cleanup);

const wsUrl = await new Promise((res, rej) => {
  let buf = '';
  chrome.stderr.on('data', (d) => { buf += d; const m = buf.match(/DevTools listening on (ws:\/\/\S+)/); if (m) res(m[1]); });
  setTimeout(() => rej(new Error('Chrome이 15초 안에 뜨지 않았다')), 15000);
}).catch((e) => fail(e.message));

const ws = new WebSocket(wsUrl);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let seq = 0;
const pending = new Map();
ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result); }
});
function send(method, params = {}, sessionId) {
  return new Promise((res, rej) => {
    const id = ++seq;
    const timer = setTimeout(() => { pending.delete(id); rej(new Error(`CDP ${method} 10초 무응답`)); }, 10000);
    pending.set(id, { res: (v) => { clearTimeout(timer); res(v); }, rej: (e) => { clearTimeout(timer); rej(e); } });
    ws.send(JSON.stringify({ id, method, params, sessionId }));
  });
}

const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
const s = (m, p) => send(m, p, sessionId);
async function ev(expr) {
  const r = await s('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) fail(`페이지 스크립트 오류: ${r.exceptionDetails.exception?.description || r.exceptionDetails.text}`);
  return r.result.value;
}

await s('Page.enable');
await s('Runtime.enable');
const loaded = new Promise((r) => ws.addEventListener('message', function on(e) {
  if (JSON.parse(e.data).method === 'Page.loadEventFired') { ws.removeEventListener('message', on); r(); }
}));
await s('Page.navigate', { url: `file://${HTML}?capture=1&theme=${THEME}&t=0` });
await loaded;
await ev('document.fonts.ready.then(() => true)');

// ── 계약 검사: 하나라도 어긋나면 GIF는 조용히 틀린 그림이 된다
const contract = await ev(`(() => {
  const ok = typeof window.__render === 'function' && typeof window.__total === 'number' && window.__total > 0
    && Array.isArray(window.__size) && window.__size.length === 2;
  if (!ok) return { ok };
  const snap = () => document.body.innerHTML;
  // 순수성은 여러 시점에서 본다 — t=0 한 점만 보면 단계 안의 효과(나타나기 등)에 섞인 난수를 못 잡는다
  const ts = Array.from({ length: 24 }, (_, i) => window.__total * (i + 0.37) / 24);
  const fwd = ts.map((t) => (window.__render(t), snap()));
  const back = ts.slice().reverse().map((t) => (window.__render(t), snap())).reverse();
  const impure = ts.filter((_, i) => fwd[i] !== back[i]).map((t) => +t.toFixed(2));
  // 움직임을 CSS나 SMIL에 맡기면 프레임을 t로 찍어도 그 움직임은 안 따라온다
  let timed = 0;
  for (const el of document.body.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    if (cs.animationName !== 'none' || cs.transitionDuration.split(',').some((d) => parseFloat(d) > 0)) timed++;
  }
  timed += document.querySelectorAll('animate, animateTransform, animateMotion, set').length;
  return { ok, total: window.__total, size: window.__size,
    moves: new Set(fwd).size > 1, // t에 따라 그림이 바뀌는가
    impure,                       // 같은 t인데 그림이 다른 시점 (Date·Math.random·누적 상태)
    timed,
    controlsHidden: document.body.classList.contains('capture') };
})()`);
if (!contract.ok) fail('계약 위반: window.__render(t)·window.__total(초)·window.__size([w,h])가 모두 있어야 한다');
if (!contract.moves) fail('계약 위반: 24개 시점의 그림이 전부 같다 — __render가 t를 읽지 않는다');
if (contract.impure.length) fail(`계약 위반: 같은 t인데 그림이 다르다 (t=${contract.impure.slice(0, 5).join(', ')}…) — Date·Math.random·이전 프레임 상태를 쓰지 않는다`);
if (contract.timed) fail(`계약 위반: CSS animation/transition·SMIL이 걸린 요소 ${contract.timed}개 — 움직임은 전부 t의 함수로 그린다`);
if (!contract.controlsHidden) fail('계약 위반: ?capture=1에서 body.capture가 없다 — 조작 막대가 GIF에 찍힌다');
const [W, H] = contract.size;
console.log(`✓ 계약: ${contract.total.toFixed(2)}초, ${W}×${H}`);
if (CHECK_ONLY) process.exit(0);

await s('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: SCALE, mobile: false });

async function shot(t, file) {
  await ev(`window.__render(${t})`);
  const { data } = await s('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: 0, width: W, height: H, scale: 1 } });
  writeFileSync(file, Buffer.from(data, 'base64'));
}

// ── 정지 장면
if (STILLS) {
  const base = join(dirname(OUT), basename(OUT, '.gif'));
  for (const t of STILLS.split(',').map(Number)) {
    const f = `${base}.still-${t}.png`;
    await shot(t, f);
    console.log(f);
  }
  process.exit(0);
}

// ── 프레임 → GIF
const work = mkdtempSync(join(tmpdir(), 'anim-frames-'));
const n = Math.floor(contract.total * FPS);
for (let i = 0; i < n; i++) await shot(i / FPS, join(work, `${String(i).padStart(5, '0')}.png`));

// 평면 도형이라 128색이면 충분하고, 디더링을 끄면 면이 깨끗하고 파일도 작다
const ff = (a) => { const r = spawnSync('ffmpeg', ['-loglevel', 'error', '-y', ...a], { stdio: 'inherit' }); if (r.status !== 0) fail('ffmpeg 실패'); };
ff(['-framerate', String(FPS), '-i', join(work, '%05d.png'), '-vf', 'palettegen=max_colors=128:stats_mode=full', join(work, 'pal.png')]);
ff(['-framerate', String(FPS), '-i', join(work, '%05d.png'), '-i', join(work, 'pal.png'), '-lavfi', 'paletteuse=dither=none', '-loop', '0', OUT]);
rmSync(work, { recursive: true, force: true });

const kb = Math.round(statSync(OUT).size / 1024);
console.log(`✓ ${OUT}\n  ${n}프레임 · ${FPS}fps · ${contract.total.toFixed(1)}초 · ${Math.round(W * SCALE)}×${Math.round(H * SCALE)} · ${kb}KB`);
process.exit(0);
