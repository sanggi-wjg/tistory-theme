// 떠 있는 목차 — 버튼(.toc-fab)과 시트(#toc-sheet) — hooks.md §5.1b, 결정 65
//
// 1399px 이하에서 목차는 글 머리 접이식뿐이라, 긴 글을 읽는 도중에는 목차로 돌아갈 길이 없었다
// (390px 「타이밍 어택」 문서 16,412px — 1,500px만 내려가도 목차가 화면 밖이다). 글 머리 #toc가
// 화면 위로 지나가면 「목차」 버튼을 띄우고, 누르면 같은 목록을 대화상자로 연다. 아래 시트인지
// 버튼 위 팝오버인지는 CSS가 폭으로 정한다.
//
// toc.js가 목차를 실제로 만든 뒤에만 부른다(#toc.is-ready). 그래서 소제목 3개 미만인 글과 글
// 페이지가 아닌 곳에는 버튼도 시트도 없다.
//
// 대화상자는 <dialog>의 showModal()에 맡긴다 — 포커스 가두기·Esc·뒤 페이지 inert를 브라우저가
// 한다. lightbox.js처럼 트랩을 손으로 짜지 않는다. showModal이 없는 브라우저에서는 아무것도
// 만들지 않는다 — 글 머리 목차는 그대로 있다.
//
// 배경 스크롤은 잠그지 않는다. 시트 안 스크롤이 배경으로 새는 것은 CSS의 overscroll-behavior가 막는다.

import { onMediaChange, rafThrottle, revealInBox } from './util.js'

const SHEET_ID = 'toc-sheet'
const TITLE_ID = 'toc-sheet-title'
const FOLLOW_MARGIN = 48 // 열 때 현재 항목 위아래에 남길 여유(px)

const LIST_ICON =
  '<svg class="icon" width="16" height="16" viewBox="0 0 20 20" aria-hidden="true" focusable="false">' +
  '<path d="M7.5 5.5h9M7.5 10h9M7.5 14.5h9" fill="none" stroke="currentColor" stroke-width="1.6"' +
  ' stroke-linecap="round"></path>' +
  '<path d="M3.5 5.5h.01M3.5 10h.01M3.5 14.5h.01" fill="none" stroke="currentColor" stroke-width="2.4"' +
  ' stroke-linecap="round"></path></svg>'

const CLOSE_ICON =
  '<svg class="icon" width="16" height="16" viewBox="0 0 20 20" aria-hidden="true" focusable="false">' +
  '<path d="M5 5l10 10M15 5 5 15" fill="none" stroke="currentColor" stroke-width="1.6"' +
  ' stroke-linecap="round"></path></svg>'

function focusEl(el) {
  if (!el) return
  try {
    el.focus({ preventScroll: true })
  } catch (e) {
    /* 포커스 불가 요소 — 넘어간다 */
  }
}

/**
 * 버튼과 시트를 만들고 시트 링크 배열을 돌려준다. 시트 링크는 글 머리 링크와 번호가 같아
 * toc.js의 스크롤스파이가 같은 자리에서 현재 표시를 옮긴다. 못 만들면 null.
 *
 * toc는 #toc.is-ready(버튼을 띄울지는 이것이 화면 위로 지나갔는가로 정한다), list는 채워진
 * #toc-list(시트 항목은 이것의 복제), mq는 toc.js의 COLLAPSIBLE_MQ다 — 경계를 여기 다시 적지
 * 않는다. 린트 BND010은 toc.js의 그 상수만 CSS와 대조한다.
 */
export default function initTocSheet(toc, list, mq) {
  const sheet = document.createElement('dialog')
  if (typeof sheet.showModal !== 'function') return null

  const headLinks = Array.prototype.slice.call(list.querySelectorAll('.toc-link'))
  if (!headLinks.length) return null
  const toggle = toc.querySelector('.toc-toggle')

  /* ── DOM ── body 끝에 버튼, 그 뒤에 시트(붙이는 것은 맨 끝에서) */
  const fab = document.createElement('button')
  fab.type = 'button'
  fab.className = 'toc-fab'
  fab.setAttribute('aria-haspopup', 'dialog')
  fab.setAttribute('aria-controls', SHEET_ID)
  fab.setAttribute('aria-expanded', 'false')
  fab.innerHTML = LIST_ICON + '<span class="toc-fab-label">목차</span>'

  sheet.id = SHEET_ID
  sheet.className = 'toc-sheet'
  sheet.setAttribute('aria-labelledby', TITLE_ID)

  const head = document.createElement('div')
  head.className = 'toc-sheet-head'
  head.innerHTML = '<h2 class="toc-sheet-title" id="' + TITLE_ID + '">목차</h2>'
  const closeBtn = document.createElement('button')
  closeBtn.type = 'button'
  closeBtn.className = 'toc-sheet-close'
  closeBtn.setAttribute('aria-label', '목차 닫기')
  closeBtn.innerHTML = CLOSE_ICON
  head.appendChild(closeBtn)

  // 항목은 글 머리 목록의 복제다 — 같은 소제목 목록을 다시 세지 않는다(결정 38의 「같은 목록」).
  // 클래스(.toc-item · .toc-h2|.toc-h3 · .toc-link)도 같고, CSS가 .toc-sheet 아래에서 따로 칠한다.
  // 스크롤스파이가 돌기 전에 불리므로 현재 표시는 아직 없다.
  const sheetList = document.createElement('ol')
  sheetList.className = 'toc-sheet-list'
  Array.prototype.forEach.call(list.children, function (li) {
    sheetList.appendChild(li.cloneNode(true))
  })
  const sheetLinks = Array.prototype.slice.call(sheetList.querySelectorAll('.toc-link'))

  sheet.appendChild(head)
  sheet.appendChild(sheetList)

  /* ── 보이기 ── 접이식 구간이고 글 머리 목차가 화면 위로 완전히 지나갔을 때만 .is-visible */
  let shown = false

  function collapsible() {
    return mq ? mq.matches : true // matchMedia 미지원 — toc.js와 같이 접이식으로 본다
  }

  // 판정은 부를 때마다 위치를 재서 한다 — 목차의 아래 끝이 화면 위쪽(0) 위에 있으면 「지나갔다」. 안
  // 보이는 것만으로는 모자란다(아직 아래에 있어 안 보이는 것과 갈라야 한다).
  // IntersectionObserver의 교차 변화에 기대지 않는다. 목차가 첫 화면 아래에 있는 글(폰은 거의 늘 그렇다)에서
  // 아래 → 위로 한 번에 넘어가면(「댓글」 링크·페이지 안 찾기·모션 축소의 맨 위로) 「교차 안 함 → 교차 안 함」
  // 이라 알림이 오지 않아, 버튼이 안 뜨거나 맨 위에 남았다(1차 체크포인트 F1).
  function sync() {
    const next = collapsible() && toc.getBoundingClientRect().bottom <= 0
    if (next === shown) return
    fab.classList.toggle('is-visible', next)
    shown = next
  }

  // 스크롤마다 프레임당 한 번(toc.js 스크롤스파이와 같은 rafThrottle). 창 크기나 늦게 온 이미지(load)로
  // 목차 위치가 바뀔 때도 다시 잰다. 만든 직후에도 한 번 — 해시로 들어왔거나 새로고침이 스크롤을 되살린 자리다.
  const onScroll = rafThrottle(sync)
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', onScroll)
  window.addEventListener('load', onScroll)
  sync()

  /* ── 열기 ── */
  fab.addEventListener('click', function () {
    if (sheet.open) return
    // 열기 전에 버튼에 포커스를 둔다. showModal()은 그때 포커스가 있던 요소를 기억했다가 닫을 때
    // 돌려주는데, Safari·iOS는 버튼을 눌러도 포커스를 주지 않아 그 전에 포커스가 있던 요소(예: 앞서
    // 목차로 착지한 소제목)가 기억된다. 버튼이면 어느 브라우저든 돌아올 곳이 같다.
    focusEl(fab)
    sheet.showModal()
    fab.setAttribute('aria-expanded', 'true')
    // showModal()이 정한 첫 포커스 대신, 읽던 자리부터 고르게 현재 항목으로 옮긴다.
    const cur = sheetList.querySelector('.toc-link.is-current') || sheetLinks[0]
    // 굴러가는 상자는 목록이다 — 머리(.toc-sheet-head)는 서 있고 목록만 굴러간다(components.css,
    // skin-style과 합의). 막 열린 상자라 굴리지 않고 바로 놓는다.
    revealInBox(sheetList, cur, FOLLOW_MARGIN, true)
    focusEl(cur)
  })

  /* ── 닫기 ── 닫기 버튼 · Esc(브라우저) · 배경 클릭 · 시트 링크 · 3단으로 넘어감 */
  let picking = false // 시트 링크로 닫는 중 — 포커스는 착지한 소제목이 받는다

  closeBtn.addEventListener('click', function () {
    sheet.close()
  })

  // ::backdrop의 click은 dialog 자신이 받는다. dialog 안쪽 여백을 눌러도 target이 dialog라 좌표로
  // 가린다 — 사각형 밖이어야 배경이다.
  sheet.addEventListener('click', function (e) {
    if (e.target !== sheet) return
    const r = sheet.getBoundingClientRect()
    if (e.clientX >= r.left && e.clientX < r.right && e.clientY >= r.top && e.clientY < r.bottom) return
    sheet.close()
  })

  // 착지는 글 머리 목차 링크와 한 벌이다(결정 59 — 접기 → 스크롤 → 소제목 포커스). 같은 자리의 글
  // 머리 링크를 click()해 toc.js의 목록 핸들러가 정하게 한다 — lightbox.js의 img.click()과 같은 수다.
  // 먼저 닫는다: 열린 동안 뒤 페이지는 inert라 소제목이 포커스를 못 받는다. close()가 포커스를
  // 어디로 돌려놓든 이어지는 click()이 소제목으로 옮긴다. close 이벤트는 그 뒤 태스크에 오므로
  // picking으로 거기서 포커스를 도로 뺏지 않게 한다. 소제목을 못 찾으면 목록 핸들러가
  // preventDefault를 안 해 #id 기본 이동이 일어난다 — 글 머리 링크와 같다.
  sheetList.addEventListener('click', function (e) {
    const a = e.target.closest ? e.target.closest('.toc-link') : null
    const i = sheetLinks.indexOf(a)
    if (i < 0 || !headLinks[i]) return
    e.preventDefault()
    if (sheet.open) {
      picking = true
      sheet.close()
    }
    headLinks[i].click()
  })

  // 닫힌 뒤 포커스는 버튼으로 돌아온다. 버튼이 안 보이면(visibility: hidden은 포커스를 못 받는다)
  // 그 자리에 보이는 목차로 보낸다 — 3단으로 넘어가 닫혔으면 옆 칸 목차의 현재 항목, 열린 채 배경을
  // 굴려 글 머리 목차가 다시 화면에 들어왔으면 그 토글.
  function returnTarget() {
    if (shown) return fab
    if (collapsible()) return toggle || fab
    return list.querySelector('.toc-link.is-current') || headLinks[0]
  }

  sheet.addEventListener('close', function () {
    fab.setAttribute('aria-expanded', 'false')
    if (picking) {
      picking = false
      return
    }
    focusEl(returnTarget())
  })

  onMediaChange(mq, function () {
    sync()
    // 3단에서는 목차가 옆 칸에 선다 — 열린 시트를 닫는다. 포커스는 close 이벤트가 그 목차로 보낸다.
    if (!collapsible() && sheet.open) sheet.close()
  })

  // 붙이는 것은 마지막이다 — 위에서 던지면 반쯤 묶인 버튼이 화면에 남지 않는다.
  document.body.appendChild(fab)
  document.body.appendChild(sheet)
  return sheetLinks
}
