// 목차 + 스크롤스파이 — hooks.md §5.1
//
// 마크업이 빈 <ol class="toc-list" id="toc-list">를 미리 놓아두었다. JS는 채우기만 한다.
// 소제목이 3개 미만이면 .is-ready를 붙이지 않는다 → CSS가 .toc를 display:none으로 둔 채로 남긴다.
// (실측: 소제목 3개 이상인 글 68%, 최대 25개)

import { onMediaChange, rafThrottle, reducedMotion, uniqueId } from './util.js'

const MIN_HEADINGS = 3 // 이 미만이면 목차를 만들지 않는다
const SPY_OFFSET = 120 // 화면 위쪽 이 높이를 지나면 "현재 위치"로 본다

// 접이식이 살아 있는 구간. components.css의 @media (max-width: 1024px)와 같은 값이어야 한다.
// 여기가 어긋나면 ARIA가 화면과 다른 말을 한다 — QA F2가 정확히 그 사고였다.
const COLLAPSIBLE_MQ = '(max-width: 1024px)'

/**
 * 목차를 만들지 못했다고 CSS에 알린다 — hooks.md §5.1
 *
 * 레이아웃은 기본이 2단이고 이 클래스가 붙을 때만 1단이 된다. 반대로(=목차가 생길 때만
 * 2단으로) 만들면 **첫 페인트에서 모든 글이 1단**이었다가 스크립트가 돌 때 68%가 2단으로
 * 바뀐다 — 1400px에서 본문이 144px 밀리는 것을 실측했다. 다수를 밀지 않는 쪽을 기본으로 둔다.
 */
function markNoToc() {
  if (document.body) document.body.classList.add('no-toc')
}

export default function initToc() {
  const toc = document.getElementById('toc')
  const list = document.getElementById('toc-list')
  if (!toc || !list) return // 글 페이지가 아니다 — 레이아웃도 건드리지 않는다

  // 부분일치. 실제 래퍼는 tt_article_useless_p_margin contents_style
  const root = document.querySelector('.entry-body .contents_style') || document.querySelector('.entry-body')
  if (!root) return markNoToc() // 본문을 못 찾았다 = 목차도 못 만든다

  const headings = Array.prototype.slice
    .call(root.querySelectorAll('h2, h3'))
    .filter(function (h) {
      return h.textContent.trim().length > 0
    })
  if (headings.length < MIN_HEADINGS) return markNoToc()

  const frag = document.createDocumentFragment()
  const links = []

  headings.forEach(function (h, i) {
    // 한글 슬러그는 URL 인코딩 문제가 있다. 번호를 쓴다 — hooks.md §5.1
    if (!h.id) h.id = uniqueId('toc-h-' + (i + 1))

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
     1025px 이상에서 CSS는 .toc-toggle을 "목차" 라벨로 바꾼다(pointer-events: none)
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

  /* ── 목차 링크 ── */
  list.addEventListener('click', function (e) {
    const a = e.target.closest ? e.target.closest('.toc-link') : null
    if (!a) return
    const id = a.getAttribute('href').slice(1)
    const target = document.getElementById(id)
    if (!target) return // 앵커가 사라졌으면 기본 동작에 맡긴다

    e.preventDefault()
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

    // 접이식이 살아 있는 구간에서만 접는다.
    // (offsetParent로 판단하면 안 된다 — 데스크톱에서도 토글은 라벨로 보인다)
    if (toggle && collapsible()) {
      toc.classList.remove('is-open')
      syncToggle()
    }
  })

  /* ── 스크롤스파이 ── */
  let tops = []
  let cur = -1

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
    if (links[cur]) links[cur].classList.remove('is-current')
    if (links[idx]) links[idx].classList.add('is-current')
    cur = idx
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
