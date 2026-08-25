// 다크모드 토글 — hooks.md §5.4 · §5.5
//
// 세 가지 상태를 다룬다: data-theme="dark" / data-theme="light" / stamp 없음(시스템 따름).
// 최초 stamp는 <head> 인라인 스니펫이 찍는다(FOUC 방지). 여기서는 토글만 한다.

import { onMediaChange } from './util.js'

const KEY = 'theme' // hooks.md §5.4 — head 인라인과 같은 키. 바꾸면 조용히 어긋난다.

/** localStorage는 시크릿 모드·사이트데이터 차단에서 예외를 던진다. 값이 없는 것과 같게 취급한다. */
function read() {
  try {
    const v = localStorage.getItem(KEY)
    return v === 'dark' || v === 'light' ? v : null
  } catch (e) {
    return null
  }
}

function write(v) {
  try {
    localStorage.setItem(KEY, v)
  } catch (e) {
    /* 저장에 실패해도 이번 세션의 토글은 동작한다 */
  }
}

export default function initTheme() {
  const root = document.documentElement
  const btn = document.getElementById('theme-toggle')
  let mq = null
  try {
    mq = window.matchMedia('(prefers-color-scheme: dark)')
  } catch (e) {
    mq = null
  }

  // 지금 실제로 보이는 테마. stamp가 없으면 시스템 값이 곧 현재 테마다.
  function current() {
    const stamped = root.getAttribute('data-theme')
    if (stamped === 'dark' || stamped === 'light') return stamped
    return mq && mq.matches ? 'dark' : 'light'
  }

  function sync() {
    if (btn) btn.setAttribute('aria-pressed', current() === 'dark' ? 'true' : 'false')
  }

  // 다른 모듈(인라인색 안전망)이 다시 계산할 수 있게 알린다.
  function announce() {
    try {
      document.dispatchEvent(new CustomEvent('skin:theme', { detail: { theme: current() } }))
    } catch (e) {
      /* CustomEvent 생성자가 없는 환경 — 알림만 생략한다 */
    }
  }

  sync()

  if (btn) {
    btn.addEventListener('click', function () {
      const next = current() === 'dark' ? 'light' : 'dark'
      root.setAttribute('data-theme', next)
      write(next)
      sync()
      announce()
    })
  }

  // 저장된 선택이 없을 때만 시스템 설정 변화를 따라간다.
  // (사용자가 명시적으로 고른 값을 OS가 덮지 않는다.)
  onMediaChange(mq, function () {
    if (read()) return
    sync()
    announce()
  })
}
