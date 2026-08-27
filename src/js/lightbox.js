// 이미지 라이트박스 — hooks.md §5.6
//
// 상태를 클래스가 아니라 "존재"로 표현한다: 열릴 때 .lightbox를 만들고 닫을 때 지운다.
// (계약에 열림 상태 클래스가 없다. body.is-lightbox-open만 배경 스크롤을 잠근다.)
// 그래서 CSS가 아직 없어도 평소 화면에는 아무것도 추가되지 않는다.

import { contentRoots } from './util.js'

const FOCUSABLE = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'

let open = null // { el, restore }

const CLOSE_ICON =
  '<svg class="icon" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false">' +
  '<path d="M5 5l10 10M15 5 5 15" fill="none" stroke="currentColor" stroke-width="1.8"' +
  ' stroke-linecap="round"></path></svg>'

function close() {
  if (!open) return
  const state = open
  open = null

  document.removeEventListener('keydown', onKeydown, true)
  document.body.classList.remove('is-lightbox-open')
  if (state.el.parentNode) state.el.parentNode.removeChild(state.el)

  // 포커스 복귀. 열기 전 요소가 사라졌으면 아무것도 하지 않는다.
  if (state.restore && document.contains(state.restore)) {
    try {
      state.restore.focus({ preventScroll: true })
    } catch (e) {
      /* 포커스 불가 요소 — 넘어간다 */
    }
  }
}

function onKeydown(e) {
  if (!open) return
  if (e.key === 'Escape' || e.key === 'Esc') {
    e.preventDefault()
    close()
    return
  }
  // Enter를 누르고 있으면(repeat) 닫기 버튼이 반복 keydown에 눌려 닫히고, 포커스가
  // 이미지로 돌아가 다음 반복에 다시 열린다 — 반복 입력은 대화상자 안에서 받지 않는다.
  if (e.key === 'Enter' && e.repeat) {
    e.preventDefault()
    return
  }
  if (e.key !== 'Tab') return

  // 포커스 트랩. 다이얼로그 안 포커스 가능 요소를 순환한다.
  const items = Array.prototype.slice.call(open.el.querySelectorAll(FOCUSABLE))
  if (!items.length) {
    e.preventDefault()
    return
  }
  const first = items[0]
  const last = items[items.length - 1]
  const active = document.activeElement

  if (e.shiftKey && (active === first || !open.el.contains(active))) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && (active === last || !open.el.contains(active))) {
    e.preventDefault()
    first.focus()
  }
}

function openFor(img) {
  if (open) return

  // 포커스 복귀 대상. 라이트박스 대상에는 initLightbox가 이미 tabindex="0"을 줬다(결정 48 —
  // 키보드 진입로, figure당 하나라 실측 최대 19개). 여기 -1은 init을 거치지 않은 이미지
  // (나중에 삽입된 것 등)를 위한 폴백으로, 포커스 복귀만 가능하게 하고 탭 순서는 안 늘린다.
  if (!img.hasAttribute('tabindex')) img.setAttribute('tabindex', '-1')

  const el = document.createElement('div')
  el.className = 'lightbox'
  el.setAttribute('role', 'dialog')
  el.setAttribute('aria-modal', 'true')
  el.setAttribute('aria-label', img.getAttribute('alt') || '이미지 확대')

  const backdrop = document.createElement('div')
  backdrop.className = 'lightbox-backdrop'

  const big = document.createElement('img')
  big.className = 'lightbox-img'
  // ⚠ **원본 URL을 따로 찾지 않는다.** 예전에는 `data-origin`을 먼저 봤는데,
  //   그 속성의 근거가 이 저장소 어디에도 없었다(2026-08-27 셀프 리뷰).
  //   실제로 관찰된 티스토리 이미지블록은 `data-origin-width`/`-height`와
  //   `<span data-url>`을 쓴다 — 이름이 다르다. 없는 속성을 먼저 보는 코드는
  //   폴백 덕에 조용히 통과하면서 "원본을 쓰고 있다"는 착각만 남긴다.
  //   무엇이 진짜 원본 주소인지는 TODO `lightbox-origin`에서 실측한다.
  big.src = img.currentSrc || img.src
  big.alt = img.getAttribute('alt') || ''

  const btn = document.createElement('button')
  btn.type = 'button'
  btn.className = 'lightbox-close'
  btn.setAttribute('aria-label', '닫기')
  btn.innerHTML = CLOSE_ICON

  el.appendChild(backdrop)
  el.appendChild(big)
  el.appendChild(btn)

  el.addEventListener('click', function (e) {
    // 이미지 자체를 누른 게 아니면 닫는다 (배경·여백·닫기 버튼)
    if (e.target === big) return
    close()
  })

  document.body.appendChild(el)
  document.body.classList.add('is-lightbox-open')
  document.addEventListener('keydown', onKeydown, true)

  open = { el: el, restore: img }
  try {
    btn.focus({ preventScroll: true })
  } catch (e) {
    btn.focus()
  }
}

/** 라이트박스 대상인가 — 본문 figure 안 이미지. 링크가 걸려 있으면 링크가 우선이다. */
function isTarget(root, img) {
  if (!img || !root.contains(img)) return false
  if (!img.closest('figure')) return false
  if (img.closest('a')) return false
  return true
}

export default function initLightbox() {
  contentRoots().forEach(function (root) {
    // 키보드 진입로. <img>는 원래 포커스 대상이 아니라 클릭만 받으면 키보드·스크린리더
    // 사용자에게는 cursor:zoom-in이 광고하는 기능이 존재하지 않는다(결정 48).
    // figure당 하나뿐이라 탭 정거장은 실측 최대 19개다.
    Array.prototype.slice.call(root.querySelectorAll('figure img')).forEach(function (img) {
      if (!isTarget(root, img)) return
      // 셋을 한 조건으로 같이 준다. role만 붙고 포커스를 못 받으면 "버튼"이라 읽히는데
      // 닿을 수 없는 상태가 된다 — 에디터가 tabindex를 박는 일은 없지만 있어도 덮는다.
      img.setAttribute('tabindex', '0')
      img.setAttribute('role', 'button')
      const alt = img.getAttribute('alt')
      img.setAttribute('aria-label', alt ? alt + ' — 확대' : '이미지 확대')
    })

    root.addEventListener('click', function (e) {
      const img = e.target && e.target.closest ? e.target.closest('img') : null
      if (!isTarget(root, img)) return
      e.preventDefault()
      try {
        openFor(img)
      } catch (err) {
        /* 라이트박스가 실패해도 본문은 그대로다 */
      }
    })

    function keyTarget(e) {
      const img = e.target && e.target.tagName === 'IMG' ? e.target : null
      return isTarget(root, img) ? img : null
    }
    function tryOpen(img) {
      try {
        openFor(img)
      } catch (err) {
        /* 위와 같다 */
      }
    }

    // Enter는 keydown에서 연다. 반복 입력(repeat)은 받지 않는다 — 열리면 포커스가 닫기
    // 버튼으로 가고 버튼은 Enter keydown에 눌리므로, 누르고 있으면 열림→닫힘을 반복한다.
    // Space는 **keyup**에서 연다. keydown에서 열면 포커스가 옮겨간 닫기 버튼이 같은 키의
    // keyup에 눌려(버튼은 Space keyup에 활성화된다) 한 번 누름에 열렸다 곧바로 닫힌다.
    // keydown에서는 페이지 스크롤만 막는다.
    root.addEventListener('keydown', function (e) {
      const img = keyTarget(e)
      if (!img) return
      if (e.key === ' ' || e.key === 'Spacebar') {
        e.preventDefault()
        return
      }
      if (e.key !== 'Enter' || e.repeat) return
      e.preventDefault()
      tryOpen(img)
    })
    root.addEventListener('keyup', function (e) {
      if (e.key !== ' ' && e.key !== 'Spacebar') return
      const img = keyTarget(e)
      if (!img) return
      e.preventDefault()
      tryOpen(img)
    })
  })
}
