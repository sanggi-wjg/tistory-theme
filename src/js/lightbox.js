// 이미지 라이트박스 — hooks.md §5.6
//
// **티스토리 phocus 뷰어가 먼저고, 이 모듈의 .lightbox는 폴백이다** (결정 60).
// 티스토리 `static/pc/dist/index.js`가 DOMContentLoaded에 `span[data-phocus] > img`마다 click을
// **img에 직접** 건다(2019~2026 표본 16장 전부 data-phocus). 둘 다 뜨면 phocus(z 940109)가 위,
// 우리 것이 아래에 겹치고, phocus의 ✕로 닫으면 우리 것이 남아 body.is-lightbox-open으로 스크롤이
// 잠긴 채가 된다 — 키보드 포커스는 가려진 우리 닫기 버튼에 가 있다(2026-10-05~06 라이브 실측).
// 그래서 click 한 경로에서 phocus가 열렸는지 보고 물러난다. 우리 것이 뜨는 것은 phocus가 이
// 이미지를 받지 않았을 때뿐이다 — data-phocus 없는 이미지(에디터 밖에서 붙인 것), phocus가 아직
// 안 걸린 시점, 티스토리가 phocus를 꺼 둔 환경.
//
// 상태를 클래스가 아니라 "존재"로 표현한다: 열릴 때 .lightbox를 만들고 닫을 때 지운다.
// (계약에 열림 상태 클래스가 없다. body.is-lightbox-open만 배경 스크롤을 잠근다.)
// 그래서 CSS가 아직 없어도 평소 화면에는 아무것도 추가되지 않는다.

import { contentRoots } from './util.js'

const FOCUSABLE = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'

let open = null // { el, restore }

// phocus가 열려 있는 동안 티스토리가 <body>에 붙이는 클래스. **우리는 읽기만 한다** — 우리 JS가
// 만드는 이름이 아니라서 hooks.md §5.6·§8 표에 없다(서술로만 적었다).
const PHOCUS_OPEN = 'with-phocus'

let phocusReturn = null // phocus로 연 이미지 — 닫히면 포커스를 돌려줄 곳
let phocusObserver = null

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
  // 원본은 **`src` 속성**이다 (결정 56, 2026-09-14 라이브 실측). 티스토리 이미지블록은
  //   `src`에 원본(실측 4406px)을, `srcset`에 `img1.daumcdn.net/thumb/R1280x0/…` **축소본 하나를
  //   서술자 없이** 싣는다 — 서술자 없는 후보는 1x라 브라우저는 srcset을 고르고, `currentSrc`는
  //   1280px 축소본이 된다. 2019~2026년 글 전부 같은 모양이고 `<span data-url>`은 `src`와 같다.
  //   그래서 `currentSrc`를 먼저 보던 코드는 라이트박스에 축소본을 띄우고 있었다 — 화면은
  //   멀쩡해 보였다(뷰포트에 맞춰 커지니까), 선명도만 조용히 잃고 있었다.
  //   `getAttribute('src')`가 비면(에디터 밖에서 붙인 이미지) 지금까지처럼 currentSrc로 간다.
  //   `data-origin`은 예전에 근거 없이 보던 이름이다 — 어디에도 없다(2026-08-27 셀프 리뷰).
  big.src = img.getAttribute('src') || img.currentSrc || img.src
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

function phocusOpen() {
  return document.body.classList.contains(PHOCUS_OPEN)
}

// phocus는 닫힐 때 포커스를 돌려주지 않는다 — Esc로 닫은 뒤 activeElement가 body·스킵 링크였다
// (라이브 실측). 키보드로 연 사람은 글 맨 앞부터 Tab을 다시 밟아야 한다. 그래서 phocus로 열린
// 이미지를 기억해 두고 <body>의 class를 지켜보다가 with-phocus가 빠지는 순간 그 이미지로 돌려준다.
// preventScroll을 빼지 않는다 — phocus가 막 스크롤을 열기 전 자리로 되돌린 참이라, 포커스가
// 스크롤을 움직이면 그 복귀를 덮는다.
//
// phocus에 남는 한계는 우리가 못 고친다: 뷰어에 role="dialog"·aria-modal이 없어 스크린리더에
// 대화상자로 읽히지 않고, 모바일 레이아웃에서는 4번째 Tab에 포커스가 뒤 페이지로 샌다(트랩 없음).
// 우리 .lightbox는 둘 다 갖췄지만 phocus가 이미지를 받는 한 뜨지 않는다.
function returnFocusAfterPhocus(img) {
  phocusReturn = img
  // 이미 지켜보는 중이면 돌려줄 곳만 바꾼다. 관찰은 phocus가 클래스를 붙인 **뒤에** 걸리므로
  // 다음 class 변화부터 보인다 — 열려 있는 동안 다른 클래스가 바뀌는 것은 걸러 낸다.
  if (phocusObserver || typeof MutationObserver === 'undefined') return
  phocusObserver = new MutationObserver(function () {
    if (phocusOpen()) return
    const target = phocusReturn
    phocusReturn = null
    phocusObserver.disconnect()
    phocusObserver = null
    if (!target || !document.contains(target)) return
    try {
      target.focus({ preventScroll: true })
    } catch (e) {
      /* 포커스 불가 요소 — 넘어간다 */
    }
  })
  phocusObserver.observe(document.body, { attributes: true, attributeFilter: ['class'] })
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
      // phocus가 이 클릭을 받았는지는 **매크로태스크로 미뤄** 본다. phocus는 body.with-phocus를
      // 자기 click 핸들러 안이 아니라 **그 직후 마이크로태스크**에서 붙인다(2026-10-06 라이브,
      // 이벤트 추적). 그래서 여기서 바로 읽으면 답이 클릭의 출처에 따라 갈린다:
      //   신뢰된 클릭(마우스) — 브라우저가 리스너 사이마다 마이크로태스크를 돌려, phocus(img의
      //     타깃 단계) 뒤에 도는 이 버블 리스너는 이미 참을 본다.
      //   합성 클릭(키보드 경로의 img.click()) — 바깥 JS 스택(우리 keydown 리스너)이 끝날 때까지
      //     마이크로태스크가 미뤄져 여기서는 거짓이다. 그대로 열면 phocus와 .lightbox가 둘 다
      //     뜬다 — 라이브에서 실제로 났다.
      // setTimeout(0)은 그 전에 쌓인 마이크로태스크(phocus의 것 포함)가 다 돈 뒤라 두 경우가 같은
      // 답을 낸다. 신뢰 클릭도 가르지 않고 항상 미룬다 — 타이밍 가정을 하나 덜 진다. 판정이 다음
      // 태스크에 있으니 이 리스너가 capture든 bubble이든 상관없다. ⚠ 판정을 다시 동기로 당기면
      // 키보드에서 두 겹이 돌아온다.
      window.setTimeout(function () {
        try {
          if (phocusOpen()) {
            returnFocusAfterPhocus(img)
            return
          }
          openFor(img)
        } catch (err) {
          /* 라이트박스가 실패해도 본문은 그대로다 */
        }
      }, 0)
    })

    function keyTarget(e) {
      const img = e.target && e.target.tagName === 'IMG' ? e.target : null
      return isTarget(root, img) ? img : null
    }
    // 키보드도 **`img.click()`**으로 연다 — 무엇을 띄울지는 위 click 경로 하나가 정한다.
    // phocus는 click만 받으므로 openFor를 직접 부르면 키보드로는 phocus를 건너뛰고 우리 것만
    // 뜬다(마우스와 다른 뷰어). img.click()은 합성 click을 img에 디스패치해 phocus의 타깃 단계
    // 핸들러 → 루트 버블 순서를 그대로 밟는다(라이브에서 `img.focus(); img.click()`로 phocus가
    // 열리는 것을 확인했다). 다만 합성 click 안에서는 phocus의 마이크로태스크가 이 keydown이
    // 끝날 때까지 미뤄진다 — click 핸들러가 판정을 매크로태스크로 미루는 이유다(위).
    // phocus가 이미 열려 있으면 아무것도 하지 않는다 — phocus가 포커스를 옮긴다는 보장이 없어
    // 포커스가 뒤의 이미지에 남아 있을 수 있고, 거기서 다시 부르면 안 된다. 다음 키 입력은 새
    // 태스크라 그때는 phocus의 마이크로태스크가 이미 돌아 with-phocus가 보인다.
    function activate(img) {
      if (phocusOpen()) return
      img.click()
    }

    // Enter는 keydown에서 연다. 반복 입력(repeat)은 받지 않는다 — 폴백이 열리면 포커스가 닫기
    // 버튼으로 가고 버튼은 Enter keydown에 눌리므로, 누르고 있으면 열림→닫힘을 반복한다.
    // Space는 **keyup**에서 연다. keydown에서 열면 포커스가 옮겨간 닫기 버튼이 같은 키의
    // keyup에 눌려(버튼은 Space keyup에 활성화된다) 한 번 누름에 열렸다 곧바로 닫힌다.
    // keydown에서는 페이지 스크롤만 막는다. (결정 48)
    //
    // 폴백은 click 핸들러가 setTimeout(0)으로 미뤄 연다 — 포커스가 닫기 버튼으로 가는 것은 이
    // 키 이벤트의 태스크가 끝난 **뒤**다. 위 논리는 그대로 선다:
    //   Enter — 키를 떼기 전에 열리면 이어지는 keyup이 닫기 버튼에 가지만, 버튼은 Enter keyup에
    //     눌리지 않아 무해하다. 열리기 전에 들어온 반복 keydown은 아래 repeat 검사가 img에서
    //     거르고, 열린 뒤의 것은 onKeydown이 대화상자 안에서 거른다.
    //   Space — 연 시점이 keyup 태스크 뒤라 같은 키의 keyup이 닫기 버튼에 닿을 일이 없다.
    //     keydown에서 열면 안 되는 이유도 그대로다 — 미뤄도 몇 ms라 키를 떼기 전에 열린다.
    root.addEventListener('keydown', function (e) {
      const img = keyTarget(e)
      if (!img) return
      if (e.key === ' ' || e.key === 'Spacebar') {
        e.preventDefault()
        return
      }
      if (e.key !== 'Enter' || e.repeat) return
      e.preventDefault()
      activate(img)
    })
    root.addEventListener('keyup', function (e) {
      if (e.key !== ' ' && e.key !== 'Spacebar') return
      const img = keyTarget(e)
      if (!img) return
      e.preventDefault()
      activate(img)
    })
  })
}
