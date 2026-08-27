// 코드블록 — 자동 감지 하이라이팅 + 복사 버튼 + 언어 라벨 + 조건부 줄번호
// DESIGN.md §6.3 · hooks.md §5.6
//
// ── 라벨을 믿는 기준: 누가 썼는가 (결정 18 · 43) ──
// **에디터가 붙인 것은 안 믿는다.** `data-ke-language` 285개(39%) 중 `javascript`
// 44개가 전부 오답이었고(셸·설정·SQL·한국어 메모), `<pre>`의 클래스는 더 나쁘다 —
// 2026-08-26 실측에서 홈 12편 41블록의 최빈값이 `reasonml` 6개였다.
// **글쓴이가 마크다운 펜스로 쓴 `<code class="language-X">`만 믿는다.**
// 둘 중 어느 것도 없으면 highlightAuto로 넘어간다.
//
// ── 왜 신뢰도 임계를 두는가 ──
// 코드블록의 33%(239개)에 한국어가 섞여 있다. 한국어 메모 블록이 엉뚱한 언어로
// 물드는 것보다, 칠하지 않고 원문 그대로 두는 편이 낫다.
// 임계 미만이면 하이라이팅도 언어 라벨도 하지 않는다.

import hljs from 'highlight.js/lib/core'
import bash from 'highlight.js/lib/languages/bash'
import go from 'highlight.js/lib/languages/go'
import java from 'highlight.js/lib/languages/java'
import json from 'highlight.js/lib/languages/json'
import kotlin from 'highlight.js/lib/languages/kotlin'
import python from 'highlight.js/lib/languages/python'
import shell from 'highlight.js/lib/languages/shell'
import sql from 'highlight.js/lib/languages/sql'
import xml from 'highlight.js/lib/languages/xml'
import yaml from 'highlight.js/lib/languages/yaml'

import { contentRoots } from './util.js'

// 후보 언어를 좁힌다 — 넓히면 짧은 블록이 엉뚱한 언어로 튄다.
// (DESIGN.md §6.3에 명시된 목록. 번들 크기도 이 목록이 결정한다.)
const LANGS = { python, bash, shell, sql, java, kotlin, go, json, yaml, xml }
const SUBSET = Object.keys(LANGS)

// ⚠ highlight.js의 xml 모듈은 HTML도 함께 처리한다. 그래서 HTML 코드블록에
//   "XML" 라벨이 붙는다. **고치지 않는 것이 결정이다**(코드리뷰 ④).
//   실측: 728개 중 html 라벨 4개, xml 라벨 0개. 다만 라벨이 붙은 건 39%뿐이고
//   그마저 틀리므로, 나머지 443개에 Spring·Maven XML이 섞였을 가능성을 배제할 수 없다.
//   xml을 목록에서 빼면 그런 블록이 하이라이팅을 통째로 잃는다 — 라벨 하나 틀리는
//   쪽이 싸다. 내용을 보고 HTML/XML을 갈라 라벨을 새로 짓는 것도 하지 않는다:
//   추측 라벨을 믿을 수 없어서 data-ke-language를 버린 것이 결정 9의 근거였다.
const LABEL = {
  python: 'Python', bash: 'Bash', shell: 'Shell', sql: 'SQL', java: 'Java',
  kotlin: 'Kotlin', go: 'Go', json: 'JSON', yaml: 'YAML', xml: 'XML',
}

/* ── 글쓴이가 직접 쓴 언어 (결정 43) ──────────────────────────────────
 *
 * 마크다운 펜스 ```python 은 `<pre><code class="language-python">`으로 저장된다.
 * 이건 **글쓴이가 친 글자**라서 믿을 수 있다. 반면 `<pre>`의 클래스와
 * `data-ke-language`는 에디터의 자동 감지 결과라 믿지 않는다 —
 * 실측(2026-08-26, 홈 12편 41블록)에서 `<pre class>`의 최빈값이 `reasonml` 6개였다.
 * 이 블로그에 ReasonML은 없다. 그래서 **`<code>`의 클래스만 본다.**
 *
 * ⚠ 이 신호는 **편집 왕복 한 번에 사라진다**(측정됨: language-python → pre.isbl,
 *   kotlin·javascript → 둘 다 pre.angelscript). 사라지면 아래 자동 감지로
 *   조용히 되돌아간다 — 화면에 신호가 없다. 되돌아간 상태가 지금과 같아서
 *   **나빠지지는 않는다**는 근거로 이 설계를 골랐다 (DECISIONS.md 결정 43).
 */
const AUTHOR_CLASS = /^language-([a-zA-Z0-9#+._-]+)$/

/** 번들에 없지만 **언어인 줄 아는** 이름. 하이라이팅은 못 해도 라벨은 맞게 단다.
 *  여기에 없는 이름은 **라벨도 달지 않는다.** 펜스에는 언어가 아닌 것도 들어온다
 *  (`info`·`warning` 같은 표식, 그리고 오타). 그런 이름에 "Info" 라벨을 달면
 *  틀린 정보를 화면에 새로 만드는 것이다 — 모르면 아무 말도 하지 않는다. */
const KNOWN_ONLY_LABEL = {
  javascript: 'JavaScript', js: 'JavaScript', typescript: 'TypeScript', ts: 'TypeScript',
  html: 'HTML', css: 'CSS', scss: 'SCSS', dockerfile: 'Dockerfile',
  c: 'C', cpp: 'C++', 'c++': 'C++', csharp: 'C#', 'c#': 'C#',
  rust: 'Rust', ruby: 'Ruby', php: 'PHP', swift: 'Swift', scala: 'Scala',
  graphql: 'GraphQL', toml: 'TOML', ini: 'INI', markdown: 'Markdown', md: 'Markdown',
  diff: 'Diff', text: null, plaintext: null, // 라벨을 일부러 비운다 — "평문"은 정보가 없다
}

/** 같은 언어의 다른 이름. 우리 번들 키로 옮긴다. */
const ALIAS = {
  py: 'python', sh: 'bash', zsh: 'bash', console: 'shell', shellsession: 'shell',
  yml: 'yaml', golang: 'go', kt: 'kotlin', postgres: 'sql', postgresql: 'sql', mysql: 'sql',
}

/**
 * `<code>`의 클래스에서 글쓴이가 쓴 언어를 읽는다.
 * 반환: { lang: 번들에 있는 키 or null, label: 표시할 이름 or null } 또는 null.
 *
 * (`scripts/probe-code-detect.mjs`가 이 함수를 그대로 불러 검증한다 — 사본이 아니다.)
 */
export function authorLanguage(classNames) {
  const names = (classNames || '').split(/\s+/)
  for (let i = 0; i < names.length; i++) {
    const m = AUTHOR_CLASS.exec(names[i])
    if (!m) continue
    const raw = m[1].toLowerCase()
    const key = ALIAS[raw] || raw
    if (LABEL[key]) return { lang: key, label: LABEL[key] }
    if (Object.prototype.hasOwnProperty.call(KNOWN_ONLY_LABEL, key)) {
      return { lang: null, label: KNOWN_ONLY_LABEL[key] }
    }
    // 언어인지 모르는 이름 — 라벨도 달지 않는다. 자동 감지로 넘어간다.
    return null
  }
  return null
}

const MIN_CHARS = 12 // 이보다 짧으면 감지가 우연에 가깝다
const MAX_HANGUL = 0.25 // 한글 비중이 이 이상이면 코드가 아니라 메모로 본다
const LINES_FOR_NUMBERS = 8 // 줄번호를 켜는 최소 줄 수
const MAX_LINES_FOR_NUMBERS = 400 // 이보다 길면 거터를 만들지 않는다 (DOM 낭비)
// 이보다 긴 블록(로그 덤프 — 실측 최대 1,777자짜리 줄이 있다)은 **자동 감지**를 건너뛴다.
// highlightAuto는 후보 10개 문법을 전부 돌리므로 비용이 길이 × 10이다. 글쓴이가 언어를 쓴
// 블록은 문법 하나라 상한과 무관하게 칠한다(결정 43·51). 복사 버튼·줄번호 규칙은 그대로.
const MAX_CHARS = 20000

let registered = false
function register() {
  if (registered) return
  SUBSET.forEach(function (name) {
    hljs.registerLanguage(name, LANGS[name])
  })
  // 우리가 직접 textContent → innerHTML로 넣으므로 콘솔 경고가 필요 없다
  hljs.configure({ ignoreUnescapedHTML: true })
  registered = true
}

/** 한글 비중. 공백을 뺀 글자 기준. */
function hangulRatio(src) {
  const solid = src.replace(/\s/g, '')
  if (!solid.length) return 0
  const han = solid.match(/[가-힣ㄱ-ㆎ]/g)
  return han ? han.length / solid.length : 0
}

/**
 * 신뢰도 임계 — 실측으로 정한 값이다. (`scripts/probe-code-detect.mjs`로 재현)
 *
 * 코드가 아닌 짧은 블록의 relevance(측정): 명령 출력 0~1 · 자바 스택트레이스 1 ·
 * nginx 로그 2 · 영문 산문 2 · ls 출력 1 · key=value 출력 3 · URL 목록 3.
 * 진짜 코드(측정): bash 21 · kotlin 15 · json 10 · sql 10 · go 9 · python 8 ·
 * xml 8 · yaml 4~7 · java 6.
 * → 짧은 블록에서는 4가 둘을 가른다.
 *
 * ⚠️ 길이에 비례해 문턱을 올리는 방식은 버렸다. 측정해 보니 코드가 아닌 텍스트의
 *    relevance는 줄당 약 1씩 쌓이는데(30줄 로그 = 30, 30줄 산문 = 30),
 *    파이썬·Go의 밀도는 그보다 낮다(11줄 8, 10줄 9). 비례 문턱을 두면 로그를
 *    막기도 전에 이 블로그에서 가장 많은 파이썬(149개)을 통째로 놓친다.
 *    긴 영문 로그 덤프가 옅게 물드는 것은 감수한다 — 물드는 대상은 숫자와
 *    따옴표 문자열이라 눈에 거슬리지 않는다. 정말 위험한 한국어 메모는
 *    아래 한글 비중 가드가 먼저 잘라낸다.
 */
const MIN_RELEVANCE = 4

/**
 * SQL 오탐 방지.
 *
 * SQL 키워드는 대부분 평범한 영어 단어(select·from·where·in·with·order·by·not·null)라
 * 영문 로그·스택트레이스가 SQL로 잡힌다(실측: 파이썬 트레이스백 4줄이 sql relevance 7).
 * 진짜 SQL 블록은 거의 언제나 줄 첫머리에 문장 동사가 온다.
 */
const SQL_HEAD = /^\s*(select|insert|update|delete|create|alter|drop|truncate|with|merge|grant)\b/im

/** 감지 결과 또는 null. null이면 원문 그대로 둔다.
 *  (`scripts/probe-code-detect.mjs`가 이 함수를 그대로 불러 임계를 검증한다 — 사본이 아니다.) */
export function detect(src) {
  register()
  if (src.length < MIN_CHARS) return null
  if (hangulRatio(src) > MAX_HANGUL) return null

  const res = hljs.highlightAuto(src, SUBSET)
  if (!res || !res.language || !LABEL[res.language]) return null
  if (res.relevance < MIN_RELEVANCE) return null
  if (res.language === 'sql' && !SQL_HEAD.test(src)) return null
  return res
}

/* ── 복사 ── */

function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    // 권한이 없거나 사용자 제스처가 인정되지 않으면 거절된다 → 구식 경로로 되돌린다
    return navigator.clipboard.writeText(text).catch(function () {
      return legacyCopy(text)
    })
  }
  return legacyCopy(text)
}

/** http·file 환경 폴백. 화면 밖 textarea → execCommand. */
function legacyCopy(text) {
  return new Promise(function (resolve, reject) {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', '')
    ta.style.cssText = 'position:fixed;top:0;left:-9999px;opacity:0'
    document.body.appendChild(ta)
    ta.select()
    let ok = false
    try {
      ok = document.execCommand('copy')
    } catch (e) {
      ok = false
    }
    document.body.removeChild(ta)
    ok ? resolve() : reject(new Error('copy failed'))
  })
}

const COPY_ICON =
  '<svg class="icon" width="15" height="15" viewBox="0 0 20 20" aria-hidden="true" focusable="false">' +
  '<rect x="7" y="7" width="10" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"></rect>' +
  '<path d="M13 4.5A1.5 1.5 0 0 0 11.5 3h-7A1.5 1.5 0 0 0 3 4.5v7A1.5 1.5 0 0 0 4.5 13"' +
  ' fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"></path></svg>'

function makeCopyButton(getText) {
  const btn = document.createElement('button')
  btn.type = 'button'
  btn.className = 'code-copy'
  btn.setAttribute('aria-label', '코드 복사')
  btn.innerHTML = COPY_ICON

  let timer = null
  btn.addEventListener('click', function () {
    copyText(getText()).then(
      function () {
        btn.classList.add('is-copied')
        btn.setAttribute('aria-label', '복사됨')
        clearTimeout(timer)
        timer = setTimeout(function () {
          btn.classList.remove('is-copied')
          btn.setAttribute('aria-label', '코드 복사')
        }, 1500)
      },
      function () {
        /* 복사 실패 — 사용자가 직접 선택할 수 있으니 조용히 넘어간다 */
      }
    )
  })
  return btn
}

/* ── 줄번호 거터 ──
 * 숫자는 CSS가 counter로 그린다. JS는 빈 <span>만 줄 수만큼 놓는다.
 * → CSS가 아직 없어도 화면에 아무것도 나타나지 않는다(무해한 실패). */
function makeGutter(lines) {
  const g = document.createElement('span')
  g.className = 'code-lines'
  g.setAttribute('aria-hidden', 'true')
  for (let i = 0; i < lines; i++) g.appendChild(document.createElement('span'))
  return g
}

/* ── 블록 하나 처리 ── */

function enhance(pre) {
  const parent = pre.parentNode
  if (!parent) return
  if (parent.classList && parent.classList.contains('code-wrap')) return // 이미 처리됨

  const codeEl = pre.querySelector('code') || pre
  const src = (codeEl.textContent || '').replace(/\s+$/, '')
  if (!src) return

  // 1) 감싸기 — 라벨·복사 버튼을 절대 위치로 띄울 기준 상자.
  //    pre를 그대로 두고 부모만 끼우므로 레이아웃이 밀리지 않는다.
  const wrap = document.createElement('div')
  wrap.className = 'code-wrap'
  parent.insertBefore(wrap, pre)
  wrap.appendChild(pre)

  // 2) 언어를 정한다. 글쓴이가 쓴 것이 있으면 그것을 쓰고, 없으면 자동 감지.
  //    ⚠ `<pre>`의 클래스는 **보지 않는다** — 에디터 자동 감지 결과다 (결정 43).
  const author = authorLanguage(codeEl.className)
  let label = null

  if (author && author.lang) {
    // 글쓴이가 지정했고 번들에도 있다 — 신뢰도 임계·한글 가드를 건너뛴다.
    // 그 가드들은 "우리가 추측할 때" 틀리지 않으려는 장치이지,
    // 글쓴이가 직접 쓴 것을 되묻는 장치가 아니다.
    try {
      const out = hljs.highlight(src, { language: author.lang, ignoreIllegals: true })
      codeEl.innerHTML = out.value
      codeEl.classList.add('hljs')
      label = author.label
    } catch (e) {
      // 등록되지 않은 언어 등 — 칠하지 않고 라벨만 남긴다
      label = author.label
    }
  } else if (author) {
    // 언어인 줄은 알지만 번들에 없다. **자동 감지로 넘어가지 않는다** —
    // 글쓴이가 `typescript`라고 썼는데 우리가 `java`로 칠하는 쪽이 더 나쁘다.
    label = author.label
  } else if (src.length > MAX_CHARS) {
    // 로그 덤프에 10개 문법을 돌리지 않는다. 감지도 라벨도 없이 원문 그대로 — 복사 버튼·줄번호만.
  } else {
    const res = detect(src)
    if (res) {
      codeEl.innerHTML = res.value // highlightAuto 출력은 이스케이프되어 있다
      codeEl.classList.add('hljs')
      codeEl.classList.add('language-' + res.language)
      label = LABEL[res.language]
    }
  }

  if (label) {
    const lang = document.createElement('span')
    lang.className = 'code-lang'
    lang.textContent = label
    wrap.appendChild(lang)
  }

  // 3) 복사 버튼은 하이라이팅 여부와 무관하게 붙인다.
  wrap.appendChild(
    makeCopyButton(function () {
      return codeEl.textContent || ''
    })
  )

  // 4) 조건부 줄번호
  const lines = src.split('\n').length
  if (lines >= LINES_FOR_NUMBERS && lines <= MAX_LINES_FOR_NUMBERS) {
    wrap.classList.add('has-lines')
    wrap.appendChild(makeGutter(lines))
  }
}

/**
 * 유휴 시간에 조금씩 돌린다(결정 51). 블록 하나에 highlightAuto가 10개 문법을 전부 돌리므로
 * 블록 20개면 200회 파싱이 DOMContentLoaded에서 **동기로** 돌았고, 그 뒤에야 목차·진행바가
 * 초기화됐다. 이제 enhance는 한 프레임 예산 안에서 돌고, 부트는 곧바로 다음 모듈로 넘어간다.
 * requestIdleCallback이 없으면(Safari) setTimeout 0으로 같은 모양을 흉내 낸다.
 * timeout을 두는 이유: 바쁜 페이지에서 유휴가 안 오면 영영 안 칠해진다.
 */
function schedule(work) {
  const ric = typeof window.requestIdleCallback === 'function' ? window.requestIdleCallback : null
  function step(deadline) {
    const t0 = Date.now()
    function budgetLeft() {
      return deadline && typeof deadline.timeRemaining === 'function'
        ? deadline.timeRemaining() > 4
        : Date.now() - t0 < 12
    }
    // 한 번 깨어나면 **최소 한 블록**은 처리한다. timeout으로 깨어난 콜백은 timeRemaining()이
    // 0이라, 예산부터 보면 아무것도 못 하고 영영 재예약된다 — 바쁜 페이지에서 정확히 그렇다.
    let more
    do {
      more = work()
    } while (more && budgetLeft())
    if (more) next()
  }
  function next() {
    if (ric) ric(step, { timeout: 1000 })
    else setTimeout(function () { step(null) }, 0)
  }
  next()
}

export default function initCode() {
  const pres = []
  contentRoots().forEach(function (root) {
    Array.prototype.push.apply(pres, Array.prototype.slice.call(root.querySelectorAll('pre')))
  })
  if (!pres.length) return

  register()
  let i = 0
  schedule(function () {
    const pre = pres[i++]
    if (!pre) return false
    try {
      enhance(pre)
    } catch (e) {
      /* 블록 하나가 실패해도 나머지는 처리한다. 원문은 그대로 남는다. */
    }
    return i < pres.length
  })
}
