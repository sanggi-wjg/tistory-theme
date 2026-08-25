// 읽기 진행바 + 맨 위로 — hooks.md §5.2 · §5.3
//
// 진행바는 width가 아니라 transform: scaleX()만 건드린다.
// 스크롤마다 레이아웃을 재계산하지 않기 위해서다(§5.2에 명시된 계약).

import { clamp01, rafThrottle, reducedMotion } from './util.js'

const TO_TOP_RATIO = 0.8 // 뷰포트 높이의 이 비율만큼 내려가면 버튼을 보인다
const TO_TOP_MIN = 400

function scrollY() {
  return window.pageYOffset || document.documentElement.scrollTop || 0
}

/* ── 읽기 진행바 ── */

function initBar() {
  const box = document.getElementById('reading-progress')
  if (!box) return // 글 페이지가 아니다
  const bar = box.querySelector('.reading-progress-bar')
  if (!bar) return

  // 읽는 구간은 본문이다. 댓글·관련글까지 포함하면 100%가 너무 늦게 온다.
  const target = document.querySelector('.entry-body') || document.querySelector('.entry-main')
  if (!target) return

  let start = 0
  let span = 0

  function measure() {
    const rect = target.getBoundingClientRect()
    start = rect.top + scrollY()
    // 본문 끝이 화면 아래에 닿는 순간을 100%로 본다
    span = rect.height - window.innerHeight
  }

  function paint() {
    const y = scrollY()
    // span <= 0 = 본문이 화면보다 짧다. 그때는 본문 상단을 지나는 순간 100%로 튄다.
    // 고치지 않는 것이 **결정이다**(코드리뷰 ③) — 잴 구간이 없으면 "다 읽었다"가 맞고,
    // 본문 중앙값이 2,813자라 해당하는 글이 거의 없다. 다시 꺼내지 말 것.
    const p = span > 0 ? clamp01((y - start) / span) : y >= start ? 1 : 0
    bar.style.transform = 'scaleX(' + p.toFixed(4) + ')'
  }

  const onScroll = rafThrottle(paint)
  const onResize = rafThrottle(function () {
    measure()
    paint()
  })

  measure()
  paint()
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', onResize)
  window.addEventListener('load', onResize)

  if (typeof ResizeObserver === 'function') {
    try {
      new ResizeObserver(onResize).observe(target)
    } catch (e) {
      /* 관찰 실패 — resize/load로 충분하다 */
    }
  }

  // 댓글은 티스토리 React가 나중에 렌더링한다. 서버는 빈 컨테이너만 내보내므로
  // 초기 측정 뒤에 문서 높이가 크게 바뀐다 → MutationObserver로 다시 잰다.
  const comments = document.getElementById('comments')
  if (comments && typeof MutationObserver === 'function') {
    try {
      const mo = new MutationObserver(onResize)
      mo.observe(comments, { childList: true, subtree: true })
      // 무한히 관찰할 이유가 없다. 렌더가 끝날 만큼 기다렸다가 끊는다.
      setTimeout(function () {
        mo.disconnect()
      }, 20000)
    } catch (e) {
      /* 관찰 실패 — 진행바가 살짝 어긋날 뿐이다 */
    }
  }
}

/* ── 맨 위로 ── */

function initToTop() {
  const btn = document.getElementById('to-top')
  if (!btn) return

  let shown = false
  function update() {
    const threshold = Math.max(TO_TOP_MIN, window.innerHeight * TO_TOP_RATIO)
    const next = scrollY() > threshold
    if (next === shown) return
    btn.classList.toggle('is-visible', next)
    shown = next
  }

  const onScroll = rafThrottle(update)
  update()
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', onScroll)

  btn.addEventListener('click', function (e) {
    try {
      window.scrollTo({ top: 0, behavior: reducedMotion() ? 'auto' : 'smooth' })
    } catch (err) {
      window.scrollTo(0, 0) // 옵션 객체 미지원
    }
    // 키보드로 눌렀으면(detail === 0) 포커스도 문서 맨 앞으로 돌려준다.
    // 그러지 않으면 탭이 페이지 끝에서 이어져 처음부터 읽을 수가 없다.
    if (e.detail === 0) {
      const skip = document.querySelector('.skip-link')
      if (skip) {
        try {
          skip.focus({ preventScroll: true })
        } catch (err) {
          skip.focus()
        }
      }
    }
  })
}

export default function initProgress() {
  initBar()
  initToTop()
}
