// 모바일 카테고리 칩 — hooks.md §5.9, DECISIONS.md 결정 50
//
// 1024px 이하에서는 레일이 본문 **아래**로 내려가 카테고리가 사실상 안 보인다
// (390px 라이브 실측: 홈에서 5,800px, 글에서 15,300px 아래). 사이드바 트리에서
// **상위 카테고리만** 읽어 헤더 안 한 줄 칩으로 낸다.
//
// 마크업의 빈 <nav class="cat-chips">를 **채우기만** 한다(hooks.md §5 원칙). 못 채우면
// 빈 채로 남고 CSS가 :empty로 감춘다 — 폴더형 트리, 구조가 다른 트리, JS 실패 전부
// 오늘과 같은 화면(칩 없음)으로 물러난다. 데스크톱(1025px~)에서는 CSS가 감춘다.
// DOM은 폭과 무관하게 항상 만든다 — 창 크기에 따라 만들었다 지웠다 하지 않는다.
//
// 트리를 읽는 규칙은 category.js와 **같은 함수**다(구조로 고르고 이름에 기능을 걸지 않는다).
// 둘이 각자 파싱하면 한쪽만 고쳤을 때 레일과 칩이 다른 목록을 내는데, 화면에는 신호가
// 없다 — 결정 38(목차·앵커가 같은 목록을 봐야 한다)과 같은 이유다.

import { childrenByTag, decodePath, labelOf, onPath, ownAnchor, pickList } from './category.js'

/**
 * 앵커 안 글 수 배지. 렌더 예 `<a> 인프라 <span>(42)</span> </a>` — 요소 자식의
 * 텍스트에서 숫자만 꺼낸다. 클래스 이름(c_cnt)에 걸지 않는 이유는 category.js와 같다.
 */
function countOf(a) {
  let n = a.firstElementChild
  while (n) {
    const m = n.textContent.match(/\d[\d,]*/)
    if (m) return m[0]
    n = n.nextElementSibling
  }
  return ''
}

function chip(href, label, count, extraClass) {
  const a = document.createElement('a')
  a.className = 'cat-chip' + (extraClass ? ' ' + extraClass : '')
  a.href = href
  a.appendChild(document.createTextNode(label))
  if (count) {
    const s = document.createElement('span')
    s.className = 'cat-chip-count'
    s.textContent = count
    a.appendChild(s)
  }
  return a
}

export default function initCatChips() {
  const nav = document.getElementById('cat-chips')
  if (!nav || nav.firstChild) return // 그릇이 없거나 이미 채웠다

  // .side-category · .side-body는 skin.html이 보장하는 우리 훅이다(hooks.md §6).
  const box = document.querySelector('.side-category .side-body')
  const rootUl = box && box.querySelector('ul')
  if (!rootUl) return // 폴더형이거나 트리가 없다 — 빈 채로 두면 CSS가 감춘다

  const list = pickList(rootUl)
  const items = childrenByTag(list, 'LI')
  if (!items.length) return

  const here = decodePath(window.location.pathname)
  const frag = document.createDocumentFragment()

  // 「전체」 — 래퍼 li("분류 전체보기")의 링크. 래퍼가 없는 트리면 만들지 않는다.
  if (list !== rootUl) {
    const wrapper = childrenByTag(rootUl, 'LI')[0]
    const all = wrapper && ownAnchor(wrapper, list)
    if (all && all.getAttribute('href')) frag.appendChild(chip(all.getAttribute('href'), '전체', '', 'is-all'))
  }

  let current = null
  items.forEach(function (li) {
    try {
      const sub = childrenByTag(li, 'UL')[0]
      const link = sub ? ownAnchor(li, sub) : childrenByTag(li, 'A')[0]
      const href = link && link.getAttribute('href')
      if (!href) return // href 없는 앵커로 칩을 만들면 href="null" 링크가 된다
      const c = chip(href, labelOf(link), countOf(link))

      // 현재 가지 — 티스토리가 붙인 selected(카테고리 페이지)를 먼저, URL 대조를 함께,
      // 그래도 아니면 하위 링크 중 하나가 현재 경로인가(하위 URL이 계층 없이 올 가능성).
      // 세 단계 **전부** category.js와 같아야 한다 — 하나라도 빠지면 레일은 펼치는데
      // 칩은 안 켜지는 상태가 되고 화면에는 신호가 없다.
      let on = li.classList.contains('selected') || !!(sub && sub.querySelector('.selected'))
      if (!on) on = onPath(here, decodePath(link.pathname))
      if (!on && sub) {
        const subLinks = sub.getElementsByTagName('a')
        for (let i = 0; i < subLinks.length; i++) {
          if (onPath(here, decodePath(subLinks[i].pathname))) {
            on = true
            break
          }
        }
      }
      if (on) {
        c.classList.add('is-current')
        c.setAttribute('aria-current', 'page')
        current = c
      }
      frag.appendChild(c)
    } catch (e) {
      /* 항목 하나가 실패해도 나머지는 만든다 */
    }
  })
  nav.appendChild(frag)

  // 현재 칩이 오른쪽 밖이면 **칩 줄만** 옮긴다. scrollIntoView는 페이지까지 세로로 움직일 수 있다.
  if (current && nav.scrollWidth > nav.clientWidth) {
    nav.scrollLeft = Math.max(0, current.offsetLeft - nav.clientWidth / 2 + current.offsetWidth / 2)
  }
}
