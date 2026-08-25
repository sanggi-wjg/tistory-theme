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
 * 글 본문뿐 아니라 공지 본문(.notice-body 안)도 같은 래퍼를 쓰므로 전부 잡는다.
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
