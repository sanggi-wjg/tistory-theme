// 목차 + 스크롤스파이 — hooks.md §5.1
//
// 마크업이 빈 <ol class="toc-list" id="toc-list">를 미리 놓아두었다. JS는 채우기만 한다.
// 소제목이 3개 미만이면 .is-ready를 붙이지 않는다 → CSS가 .toc를 display:none으로 둔 채로 남긴다.
// (실측: 소제목 3개 이상인 글 68%, 최대 25개)

import initTocSheet from './toc-sheet.js'
import { entryRoot, headingsWithIds, onMediaChange, rafThrottle, reducedMotion, revealInBox } from './util.js'

const MIN_HEADINGS = 3 // 이 미만이면 목차를 만들지 않는다
const SPY_OFFSET = 120 // 화면 위쪽 이 높이를 지나면 "현재 위치"로 본다
const FOLLOW_MARGIN = 48 // 목차 상자가 현재 항목을 따라갈 때 위·아래에 남길 여유(px)

// 접이식이 살아 있는 구간. components.css의 @media (max-width: 1399px)와 같은 값이어야 한다.
// 여기가 어긋나면 ARIA가 화면과 다른 말을 한다 — QA F2가 정확히 그 사고였다.
// 경계가 1400인 이유: 목차가 옆 칸에 서는 3단이 거기서 시작한다(layout.css). 그 아래에서
// 펼쳐 두면 목차가 본문 위에 1칸으로 선다 — 1280px 라이브 실측, 결정 48.
const COLLAPSIBLE_MQ = '(max-width: 1399px)'

/**
 * 목차를 만들지 못했다고 CSS에 알린다 — hooks.md §5.1
 *
 * 레이아웃은 기본이 2단이고 이 클래스가 붙을 때만 1단이 된다. 반대로(=목차가 생길 때만
 * 2단으로) 만들면 **첫 페인트에서 모든 글이 1단**이었다가 스크립트가 돌 때 68%가 2단으로
 * 바뀐다 — 1400px에서 본문이 144px 밀리는 것을 실측했다. 다수를 밀지 않는 쪽을 기본으로 둔다.
 *
 * 첫 판정은 skin.html의 인라인 스크립트가 .entry-body 직후, 첫 페인트 전에 한다(결정 48).
 * 여기는 폴백이다 — 본문을 못 찾았거나 인라인이 실패한 경로, 그리고 인라인은 목차가 생긴다고
 * 봤는데 여기서 예외로 죽은 경로. **조건은 인라인과 같아야 한다**
 * (h2·h3, 빈 소제목 제외, MIN_HEADINGS 미만). classList.add라 두 번 붙여도 같다.
 */
function markNoToc() {
  if (document.body) document.body.classList.add('no-toc')
}

export default function initToc() {
  const toc = document.getElementById('toc')
  const list = document.getElementById('toc-list')
  if (!toc || !list) return // 글 페이지가 아니다 — 레이아웃도 건드리지 않는다

  // 왜 finally인가 — 결정 62의 목차 바 예약을 푼다. html.js이고 body.no-toc가 아니면
  // 1399px 이하에서 CSS가 .entry-aside에 목차 바 자리를 미리 잡는다. .is-ready를 못 붙이고
  // 끝나면 — 조기 반환이든 실행 중 예외든 — 빈 띠가 남으므로 no-toc로 푼다. 예외는
  // html.js가 못 보는 경로라(hooks.md §5.4) 여기서 풀어야 한다. .is-ready를 붙인 뒤의 예외
  // (접이식·스크롤스파이)는 목차가 이미 자리를 채웠으니 건드리지 않는다 — 거기서 no-toc를
  // 붙이면 목차는 보이는데 1단이 된다. 예외는 삼키지 않는다. index.js의 safe()가 남긴다.
  try {
    build(toc, list)
  } finally {
    if (!toc.classList.contains('is-ready')) markNoToc()
  }
}

function build(toc, list) {
  const root = entryRoot()
  if (!root) return // 본문을 못 찾았다 = 목차도 못 만든다 (finally가 markNoToc)

  // 목록과 id는 util이 만든다. heading-anchor.js가 같은 것을 쓴다 — hooks.md §5.8
  const headings = headingsWithIds(root)
  if (headings.length < MIN_HEADINGS) return // finally가 markNoToc

  const frag = document.createDocumentFragment()
  const links = []

  headings.forEach(function (h) {
    const li = document.createElement('li')
    li.className = 'toc-item toc-' + h.tagName.toLowerCase() // toc-h2 / toc-h3

    const a = document.createElement('a')
    a.className = 'toc-link'
    a.href = '#' + h.id
    a.textContent = h.textContent.trim()

    li.appendChild(a)
    frag.appendChild(li)
    links.push(a)
  })

  list.appendChild(frag)
  toc.classList.add('is-ready')

  /* ── 모바일 접이식 ──
     1400px 이상에서 CSS는 .toc-toggle을 "목차" 라벨로 바꾼다(pointer-events: none)
     — 눌러도 목록 높이가 변하지 않는다. 그런 상태에서 aria-expanded="false"를 남기면
     스크린리더는 "축소됨"이라고 읽는데 링크들은 이미 탭 순서 안에 있다.
     그래서 접이식이 실제로 동작하는 구간에서만 속성을 두고, 데스크톱에서는
     속성을 지우고 탭 순서에서도 뺀다. 미디어 변경도 구독해 창 크기를 바꿔도 따라온다. */
  const toggle = toc.querySelector('.toc-toggle')
  let collapsibleMq = null
  try {
    collapsibleMq = window.matchMedia ? window.matchMedia(COLLAPSIBLE_MQ) : null
  } catch (err) {
    collapsibleMq = null // matchMedia 미지원 — 접이식으로 간주한다(속성이 있는 쪽이 안전하다)
  }

  function collapsible() {
    return collapsibleMq ? collapsibleMq.matches : true
  }

  function syncToggle() {
    if (!toggle) return
    if (collapsible()) {
      toggle.removeAttribute('tabindex')
      toggle.setAttribute('aria-expanded', toc.classList.contains('is-open') ? 'true' : 'false')
    } else {
      // 데스크톱: 라벨이다. 상태를 주장하지 않고, 아무 일도 못 하는 탭 정거장도 만들지 않는다.
      toc.classList.remove('is-open')
      toggle.removeAttribute('aria-expanded')
      toggle.setAttribute('tabindex', '-1')
    }
  }

  if (toggle) {
    syncToggle()
    toggle.addEventListener('click', function () {
      // pointer-events:none은 마우스만 막는다. 스크린리더의 가상 클릭은 그대로 들어온다.
      // 데스크톱에서는 화면이 변하지 않으므로 클래스도 건드리지 않는다.
      if (!collapsible()) return
      toc.classList.toggle('is-open')
      syncToggle()
    })
    onMediaChange(collapsibleMq, syncToggle)
  }

  /* ── 목차 링크 ──
     떠 있는 목차 시트(toc-sheet.js, 결정 65)도 이 핸들러로 착지한다 — 시트가 닫히고 같은 자리의
     이 목록 링크를 click()한다. 착지 규칙(접기 → 스크롤 → 소제목 포커스)이 한 벌이다. */
  list.addEventListener('click', function (e) {
    const a = e.target.closest ? e.target.closest('.toc-link') : null
    if (!a) return
    const id = a.getAttribute('href').slice(1)
    const target = document.getElementById(id)
    if (!target) return // 앵커가 사라졌으면 기본 동작에 맡긴다

    e.preventDefault()

    // 접이식이 살아 있는 구간에서만 접는다.
    // (offsetParent로 판단하면 안 된다 — 데스크톱에서도 토글은 라벨로 보인다)
    // 반드시 스크롤 **전에** 접는다. 부드러운 스크롤은 시작 시점의 좌표로 가고 레이아웃이
    // 바뀌어도 다시 겨누지 않는다(Safari는 스크롤 앵커링도 없다). 뒤에서 접으면 펼친
    // 목록 높이(약 350px)만큼 본문이 올라가 소제목을 그만큼 지나쳐 착지한다.
    // scrollIntoView가 레이아웃을 강제로 다시 계산하므로 같은 프레임에서 접어도 된다.
    if (toggle && collapsible()) {
      toc.classList.remove('is-open')
      syncToggle()
    }

    target.scrollIntoView({ behavior: reducedMotion() ? 'auto' : 'smooth', block: 'start' })

    // 키보드 사용자가 이어서 읽을 수 있게 소제목으로 포커스를 옮긴다.
    // tabindex="-1"은 탭 순서를 늘리지 않는다.
    if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1')
    try {
      target.focus({ preventScroll: true })
    } catch (err) {
      /* preventScroll 미지원 — 포커스만 포기한다 */
    }
    try {
      history.replaceState(null, '', '#' + id)
    } catch (err) {
      /* file:// 등에서 SecurityError — 주소만 안 바뀐다 */
    }
  })

  /* ── 떠 있는 목차 (결정 65) ──
     1399px 이하에서 글 머리 목차가 화면 위로 지나가면 뜨는 버튼과 시트. 항목은 위 목록의 복제라
     순서가 같고, 시트 링크를 누르면 같은 자리의 글 머리 링크를 click()해 위 핸들러 하나로 착지한다.
     실패해도 글 머리 목차와 스크롤스파이는 살아야 한다 — 여기서 던지면 아래 구독이 안 걸린다. */
  let sheetLinks = null
  try {
    sheetLinks = initTocSheet(toc, list, collapsibleMq)
  } catch (err) {
    if (window.console && console.warn) console.warn('[skin] toc-sheet 실패:', err)
  }

  /* ── 스크롤스파이 ── */
  let tops = []
  let cur = -1
  // 현재 표시를 같은 자리에서 옮길 목록들. 시트는 글 머리 목록의 복제라 번호가 같다.
  const linkSets = sheetLinks ? [links, sheetLinks] : [links]

  function measure() {
    const y = window.pageYOffset || document.documentElement.scrollTop || 0
    tops = headings.map(function (h) {
      return h.getBoundingClientRect().top + y
    })
  }

  function spy() {
    if (!tops.length) return
    const y = (window.pageYOffset || document.documentElement.scrollTop || 0) + SPY_OFFSET
    let idx = 0
    for (let i = 0; i < tops.length; i++) {
      if (tops[i] <= y) idx = i
      else break
    }
    // 문서 끝에 닿았으면 마지막 항목을 켠다 (짧은 마지막 절이 영영 안 켜지는 것을 막는다)
    const doc = document.documentElement
    if (window.innerHeight + y - SPY_OFFSET >= doc.scrollHeight - 4) idx = tops.length - 1

    if (idx === cur) return
    // 색(.is-current)과 aria-current를 같은 자리에서 옮긴다 — 색만으로는 스크린리더에 안 보인다.
    // 글 머리 목차와 시트가 같이 옮겨 간다. 둘이 따로 세면 서로 다른 항목을 「지금」이라 한다.
    linkSets.forEach(function (set) {
      if (set[cur]) {
        set[cur].classList.remove('is-current')
        set[cur].removeAttribute('aria-current')
      }
      if (set[idx]) {
        set[idx].classList.add('is-current')
        set[idx].setAttribute('aria-current', 'location')
      }
    })
    if (links[idx]) follow(links[idx])
    cur = idx
  }

  /* 1400px~에서 목차는 max-height + overflow-y: auto 상자다(components.css). 항목이 많으면
     현재 항목이 상자 밖으로 나가는데 상자는 따라오지 않았다(결정 63).
     **상자의 scrollTop만** 옮긴다(util.revealInBox — 떠 있는 목차 시트와 같은 함수).
     현재 항목이 바뀔 때만 부르므로, 사용자가 상자를 직접 굴리는 동안에는 싸우지 않는다.
     접이식 구간(~1399px)에서는 상자가 스크롤되지 않아 첫 조건에서 물러난다. */
  function follow(link) {
    revealInBox(toc, link, FOLLOW_MARGIN)
  }

  const onScroll = rafThrottle(spy)
  const onResize = rafThrottle(function () {
    measure()
    spy()
  })

  measure()
  spy()
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', onResize)
  window.addEventListener('load', onResize) // 이미지가 늦게 로드되면 위치가 밀린다

  // 본문 높이가 변하면(이미지·임베드·코드블록 래핑) 좌표를 다시 잰다
  if (typeof ResizeObserver === 'function') {
    try {
      new ResizeObserver(onResize).observe(root)
    } catch (e) {
      /* 관찰 실패 — resize/load 이벤트로 충분하다 */
    }
  }
}
