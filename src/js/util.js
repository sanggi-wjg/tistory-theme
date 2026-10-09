// 기능 모듈이 공유하는 최소한의 도우미.
// 여기에 기능을 넣지 않는다 — 순수 함수와 얇은 래퍼만.

/** 모션 최소화 설정. matchMedia가 없는 환경(구형·테스트)에서도 죽지 않는다. */
export function reducedMotion() {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  } catch (e) {
    return false
  }
}

/**
 * 본문 래퍼 목록.
 *
 * 실제 클래스는 `tt_article_useless_p_margin contents_style`이다.
 * class 속성 전체를 통짜로 비교하는 정확일치 선택자로는 잡히지 않는다 — 반드시 클래스 부분일치.
 * 글 본문뿐 아니라 공지 본문도 잡는다 — `.notice-body` 자신이거나(skin.html이 단다),
 * 티스토리가 안쪽에 래퍼를 달아 왔으면 그 래퍼다(notice.js가 바깥 것을 떼 한 겹만 남긴다).
 */
export function contentRoots() {
  return Array.prototype.slice.call(document.querySelectorAll('.contents_style'))
}

/** rAF로 묶어 스크롤 핸들러가 프레임당 한 번만 돌게 한다. */
export function rafThrottle(fn) {
  let ticking = false
  return function throttled() {
    if (ticking) return
    ticking = true
    window.requestAnimationFrame(function () {
      ticking = false
      try {
        fn()
      } catch (e) {
        /* 스크롤 핸들러가 죽어도 페이지는 살아 있어야 한다 */
      }
    })
  }
}

/** matchMedia 변경 구독. Safari 13 이하는 addEventListener가 없다. */
export function onMediaChange(mq, fn) {
  if (!mq) return
  if (typeof mq.addEventListener === 'function') mq.addEventListener('change', fn)
  else if (typeof mq.addListener === 'function') mq.addListener(fn)
}

/**
 * 스크롤 상자 안에서 item이 위아래 여유(margin, 상자 높이의 1/4까지)를 두고 보이게
 * **상자의 scrollTop만** 옮긴다. scrollIntoView는 페이지까지 움직인다(결정 59가 겪은 부류).
 * 상자가 스크롤되지 않으면(내용이 상자에 다 들어가거나 display:none) 아무것도 하지 않는다.
 * 목차 상자 따라가기(toc.js, 결정 63)와 떠 있는 목차 시트(toc-sheet.js, 결정 65)가 쓴다.
 * instant면 굴리지 않고 바로 놓는다 — 막 열린 상자처럼 움직임을 보여 줄 이유가 없을 때.
 */
export function revealInBox(box, item, margin, instant) {
  const view = box.clientHeight
  if (box.scrollHeight <= view + 1) return
  const gap = Math.min(margin, view / 4)
  const top = item.getBoundingClientRect().top - box.getBoundingClientRect().top - box.clientTop + box.scrollTop
  const bottom = top + item.offsetHeight
  let next = box.scrollTop
  if (top < box.scrollTop + gap) next = top - gap
  else if (bottom > box.scrollTop + view - gap) next = bottom - view + gap
  else return
  next = Math.max(0, Math.min(next, box.scrollHeight - view))
  if (Math.abs(next - box.scrollTop) < 1) return // 이미 끝에 붙어 있다
  // 여기서 던지면 부른 쪽이 끊긴다(toc.js의 첫 spy()라면 스크롤 구독이 안 걸린다) — 옵션 객체를
  // 모르는 구형 scrollTo는 scrollTop 대입으로 물러난다.
  try {
    box.scrollTo({ top: next, behavior: instant || reducedMotion() ? 'auto' : 'smooth' })
  } catch (e) {
    box.scrollTop = next
  }
}

/** 0…1로 자른다. */
export function clamp01(n) {
  return n < 0 ? 0 : n > 1 ? 1 : n
}

/** 문서 안에서 유일한 id를 만든다. 기존 id와 부딪히면 뒤에 번호를 더한다. */
export function uniqueId(base) {
  let id = base
  let n = 2
  while (document.getElementById(id)) id = base + '-' + n++
  return id
}

/**
 * 글 본문 루트. 부분일치다 — 실제 래퍼는 tt_article_useless_p_margin contents_style.
 *
 * 목차와 소제목 앵커가 **같은 곳**을 봐야 한다. 한쪽만 .entry-body로 물러나면
 * 두 기능이 다른 소제목 목록을 세게 되는데, 그건 화면에 아무 신호도 내지 않는다.
 */
export function entryRoot() {
  return document.querySelector('.entry-body .contents_style') || document.querySelector('.entry-body')
}

/**
 * 본문 소제목을 순서대로 돌려주고, id가 없으면 만들어 붙인다.
 *
 * 목차(toc.js)와 소제목 앵커(heading-anchor.js)가 **같은 목록·같은 번호**를 봐야 한다.
 * 둘이 따로 세면 목차 링크와 앵커 주소가 어긋나는데 — 예를 들어 한쪽만 빈 소제목을
 * 세면 그 뒤가 전부 한 칸씩 밀린다 — 클릭해 보기 전에는 드러나지 않는다.
 *
 * 번호를 쓰는 이유는 한글 슬러그의 URL 인코딩 문제다 (hooks.md §5.1).
 * 이미 id가 있으면 건드리지 않으므로 두 번 불러도 결과가 같다.
 */
export function headingsWithIds(root) {
  const headings = Array.prototype.slice
    .call(root.querySelectorAll('h2, h3'))
    .filter(function (h) {
      return h.textContent.trim().length > 0
    })

  headings.forEach(function (h, i) {
    if (!h.id) h.id = uniqueId('toc-h-' + (i + 1))
  })

  return headings
}
