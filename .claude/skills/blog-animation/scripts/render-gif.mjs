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
import { pathToFileURL } from 'node:url';

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
// 잘못 친 값은 조용히 틀린 결과가 된다 — 'drak'은 어느 규칙에도 안 맞아 라이트로 굽히고, '9.5x'는 NaN 장면이 된다
if (!['light', 'dark'].includes(THEME)) fail(`--theme은 light 또는 dark: ${THEME}`);
if (!(FPS > 0 && FPS <= 50)) fail(`--fps는 0보다 크고 50 이하: ${opt('--fps')}`);
if (!(SCALE > 0 && SCALE <= 4)) fail(`--scale은 0보다 크고 4 이하: ${opt('--scale')}`);
const STILL_TS = STILLS ? STILLS.split(',').map((x) => (/^\s*\d+(\.\d+)?\s*$/.test(x) ? Number(x) : NaN)) : [];
if (STILL_TS.some(Number.isNaN)) fail(`--stills는 쉼표로 구분한 초: ${STILLS}`);
const CHECK_ONLY = args.includes('--check');
const OUT = resolve(opt('--out', join(dirname(HTML), basename(HTML, extname(HTML)) + '.gif')));

// 환경변수 CHROME → macOS 앱 → PATH의 리눅스 이름들. CI(ubuntu 러너)는 google-chrome이 깔려 있다(이슈 #105)
const MAC_CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const onPath = (name) => (process.env.PATH || '').split(':').map((d) => join(d, name)).find(isFile);
function isFile(f) { try { return statSync(f).isFile(); } catch { return false; } }
const CHROME = process.env.CHROME || (existsSync(MAC_CHROME) ? MAC_CHROME
  : ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser'].map(onPath).find(Boolean));
if (!CHROME || !existsSync(CHROME)) fail(`Chrome이 없다: ${CHROME || MAC_CHROME + ' · PATH의 google-chrome·chromium'} (환경변수 CHROME으로 경로를 준다)`);
if (typeof WebSocket !== 'function') fail('Node 22 이상이 필요하다 (내장 WebSocket)');
if (!STILLS && !CHECK_ONLY && spawnSync('ffmpeg', ['-version']).status !== 0) fail('ffmpeg가 없다 — brew install ffmpeg');

function fail(msg) { console.error('✗ ' + msg); process.exit(1); }

// ── 시도 고리. 계약 위반(fail)은 몇 번을 돌려도 같으니 즉시 끝내고, 다시 돌리는 것은 Chrome·CDP가
// 멈추거나 죽었을 때(InfraError)뿐이다. 다시 띄울 때마다 stderr에 ↻를 남겨 숨지 않게 한다 —
// test-contract가 그 횟수를 센다(이슈 #135: 무응답 1회가 npm run check를 통째로 빨갛게 만들었다)
class InfraError extends Error {}
const ATTEMPTS = 3;
// Chrome은 죽는 중에도 프로필에 쓴다 — 지우기는 재시도하고, 그래도 남으면 임시 폴더라 둔다.
// 프레임 폴더도 여기서 지운다 — ffmpeg가 실패해 fail()로 나가도 수십 MB가 남지 않게
let chrome = null, profile = null, work = null;
const teardown = () => {
  try { chrome?.kill('SIGKILL'); } catch {}
  for (const d of [profile, work]) if (d) try { rmSync(d, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch {}
  chrome = profile = work = null;
};
process.on('exit', teardown);

for (let n = 1; ; n++) {
  try {
    await attempt();
    break;
  } catch (e) {
    if (!(e instanceof InfraError)) throw e;
    teardown();
    if (n >= ATTEMPTS) fail(`${e.message} — Chrome을 ${ATTEMPTS}번 띄워도 같았다`);
    console.error(`↻ ${e.message} — Chrome을 다시 띄운다 (${n + 1}/${ATTEMPTS})`);
  }
}

async function attempt() {
  // ── Chrome + CDP — 한 번의 시도. 멈추거나 죽으면 InfraError를 던지고 바깥 고리가 Chrome을 새로 띄운다
  profile = mkdtempSync(join(tmpdir(), 'anim-profile-'));
  chrome = spawn(CHROME, [
    '--headless=new', '--disable-gpu', '--hide-scrollbars', '--remote-debugging-port=0',
    `--user-data-dir=${profile}`, 'about:blank',
  ], { stdio: ['ignore', 'ignore', 'pipe'] });
  const pending = new Map();
  // Chrome이나 탭이 죽으면 기다리던 응답은 영영 오지 않는다 — 시한까지 기다리지 말고 바로 끊는다
  const dead = (why) => { for (const [id, p] of pending) { pending.delete(id); p.rej(new InfraError(why)); } };
  chrome.on('exit', (code, sig) => dead(`Chrome이 끝났다 (${code ?? sig})`));

  const wsUrl = await new Promise((res, rej) => {
    let buf = '';
    chrome.stderr.on('data', (d) => { buf += d; const m = buf.match(/DevTools listening on (ws:\/\/\S+)/); if (m) res(m[1]); });
    chrome.on('exit', () => rej(new InfraError('Chrome이 뜨기 전에 끝났다')));
    setTimeout(() => rej(new InfraError('Chrome이 15초 안에 뜨지 않았다')), 15000);
  });

  const ws = new WebSocket(wsUrl);
  await new Promise((res, rej) => {
    ws.addEventListener('open', res, { once: true });
    ws.addEventListener('error', () => rej(new InfraError('CDP 소켓을 열지 못했다')), { once: true });
    setTimeout(() => rej(new InfraError('CDP 소켓이 10초 안에 열리지 않았다')), 10000);
  });
  ws.addEventListener('close', () => dead('CDP 소켓이 닫혔다'));
  let seq = 0;
  ws.addEventListener('message', (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result); }
    else if (m.method === 'Inspector.targetCrashed') dead('탭의 렌더러가 죽었다');
    else if (m.method === 'Target.detachedFromTarget') dead('탭에서 떨어졌다');
  });
  // 시한은 「멈춤」을 알아보는 장치다. 무거운 여러 개를 함께 돌려도(16개 동시) 가장 느린 호출이 1.3초였고,
  // 멈출 때는 120초를 기다려도 오지 않았다(2026-10-10 실측, 이슈 #135) — 늘려서 고칠 것이 아니라 다시 띄울 일이다
  function send(method, params = {}, sessionId) {
    return new Promise((res, rej) => {
      const id = ++seq;
      const timer = setTimeout(() => { pending.delete(id); rej(new InfraError(`CDP ${method} 10초 무응답`)); }, 10000);
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
  const loaded = new Promise((r, rej) => {
    ws.addEventListener('message', function on(e) {
      if (JSON.parse(e.data).method === 'Page.loadEventFired') { ws.removeEventListener('message', on); r(); }
    });
    setTimeout(() => rej(new InfraError('페이지가 10초 안에 로드되지 않았다')), 10000);
  });
  // pathToFileURL — 경로의 #·?·공백이 조각·쿼리로 잘리지 않게
  const pageUrl = pathToFileURL(HTML);
  pageUrl.search = `?capture=1&theme=${THEME}&t=0`;
  await s('Page.navigate', { url: pageUrl.href });
  await loaded;
  await ev('document.fonts.ready.then(() => true)');

  // ── 계약 검사: 하나라도 어긋나면 GIF는 조용히 틀린 그림이 된다
  const contract = await ev(`(() => {
    const ok = typeof window.__render === 'function' && typeof window.__total === 'number' && window.__total > 0
      && Array.isArray(window.__size) && window.__size.length === 2;
    if (!ok) return { ok };
    const snap = () => document.body.innerHTML;
    // 검사는 **실제로 찍을 프레임 시각 전부**에서 한다. 처음엔 t=0 한 점, 다음엔 24점만 봤다 —
    // 둘 다 짧은 단계·나타나기 구간에만 섞인 난수나 늦게 생기는 애니메이션을 놓쳤다(코드 리뷰 2026-10-08)
    const ts = Array.from({ length: Math.floor(window.__total * ${FPS}) }, (_, i) => i / ${FPS});
    // 움직임을 CSS나 SMIL에 맡기면 프레임을 t로 찍어도 그 움직임은 안 따라온다
    const timedAt = () => {
      let n = document.querySelectorAll('animate, animateTransform, animateMotion, set').length;
      for (const el of document.body.querySelectorAll('*')) {
        const cs = getComputedStyle(el);
        if (cs.animationName !== 'none' || cs.transitionDuration.split(',').some((d) => parseFloat(d) > 0)) n++;
      }
      return n;
    };
    let timed = 0, timedT = null;
    const fwd = ts.map((t) => {
      window.__render(t);
      const n = timedAt();
      if (n > timed) { timed = n; timedT = t; }
      return snap();
    });
    const back = ts.slice().reverse().map((t) => (window.__render(t), snap())).reverse();
    const impure = ts.filter((_, i) => fwd[i] !== back[i]).map((t) => +t.toFixed(2));
    return { ok, total: window.__total, size: window.__size,
      frames: ts.length,
      moves: new Set(fwd).size > 1, // t에 따라 그림이 바뀌는가
      impure,                       // 같은 t인데 그림이 다른 시점 (Date·Math.random·누적 상태)
      timed, timedT,
      controlsHidden: document.body.classList.contains('capture') };
  })()`);
  if (!contract.ok) fail('계약 위반: window.__render(t)·window.__total(초)·window.__size([w,h])가 모두 있어야 한다');
  if (!contract.moves) fail(`계약 위반: 프레임 ${contract.frames}장의 그림이 전부 같다 — __render가 t를 읽지 않는다`);
  if (contract.impure.length) fail(`계약 위반: 같은 t인데 그림이 다르다 (t=${contract.impure.slice(0, 5).join(', ')}…) — Date·Math.random·이전 프레임 상태를 쓰지 않는다`);
  if (contract.timed) fail(`계약 위반: CSS animation/transition·SMIL이 걸린 요소 ${contract.timed}개 (t=${contract.timedT.toFixed(2)}) — 움직임은 전부 t의 함수로 그린다`);
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
    for (const t of STILL_TS) {
      const f = `${base}.still-${t}.png`;
      await shot(t, f);
      console.log(f);
    }
    process.exit(0);
  }

  // ── 프레임 → GIF
  work = mkdtempSync(join(tmpdir(), 'anim-frames-'));
  const n = Math.floor(contract.total * FPS);
  for (let i = 0; i < n; i++) await shot(i / FPS, join(work, `${String(i).padStart(5, '0')}.png`));

  // 평면 도형이라 128색이면 충분하고, 디더링을 끄면 면이 깨끗하고 파일도 작다. 팔레트 생성과 적용을 한 번의 디코드로
  const r = spawnSync('ffmpeg', ['-loglevel', 'error', '-y', '-framerate', String(FPS), '-i', join(work, '%05d.png'),
    '-filter_complex', 'split[a][b];[a]palettegen=max_colors=128:stats_mode=full[p];[b][p]paletteuse=dither=none',
    '-loop', '0', OUT], { stdio: 'inherit' });
  if (r.status !== 0) fail('ffmpeg 실패');

  const kb = Math.round(statSync(OUT).size / 1024);
  console.log(`✓ ${OUT}\n  ${n}프레임 · ${FPS}fps · ${contract.total.toFixed(1)}초 · ${Math.round(W * SCALE)}×${Math.round(H * SCALE)} · ${kb}KB`);
  process.exit(0);
}
