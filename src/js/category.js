// 사이드바 카테고리 접기/펼치기 — hooks.md §5.6
//
// 왜 클래스 이름을 쓰지 않는가
//   [##_category_##]는 티스토리가 통짜로 렌더한다. 우리는 안쪽 마크업을 만들지 않았고,
//   공식 레퍼런스(docs/tistory-skin-reference.txt:1715-1731)는 치환자 이름만 적었을 뿐
//   출력 마크업을 적지 않았다. DESIGN.md §5.3이 적어 둔 이름들(.category_list ·
//   .sub_category_list · .link_item)은 실블로그 관찰에서 온 것으로 보이지만 출처가 없다.
//   이름이 하나라도 다르면 조용히 아무 일도 일어나지 않는다 — 이 도메인이 실패하는 방식 그대로다.
//   그래서 **구조**로 고른다: "중첩 <ul>을 가진 <li>". 이름이 달라도 동작하고,
//   구조가 예상과 다르면 아무것도 하지 않고 물러난다.
//
// 왜 앵커에 핸들러를 걸지 않는가
//   상위 카테고리 링크도 실제로 이동하는 링크다(/category/IT). 클릭을 가로채면
//   "상위 카테고리 글 전체 보기"로 가는 길이 사라진다. 접기/펼치기는 별도의 버튼이다.

import { uniqueId } from './util.js'

const CHEVRON =
  '<svg class="icon cat-toggle-icon" width="12" height="12" viewBox="0 0 12 12"' +
  ' aria-hidden="true" focusable="false">' +
  '<path d="M4.5 2.5 8 6l-3.5 3.5" fill="none" stroke="currentColor" stroke-width="1.5"' +
  ' stroke-linecap="round" stroke-linejoin="round"></path></svg>'

/** el의 직속 자식 중 태그가 tag인 것만. querySelector로는 손자까지 딸려온다. */
function childrenByTag(el, tag) {
  const out = []
  let n = el.firstElementChild
  while (n) {
    if (n.tagName === tag) out.push(n)
    n = n.nextElementSibling
  }
  return out
}

/**
 * 접을 대상이 늘어서는 목록을 고른다.
 *
 * 티스토리 출력은 트리 전체를 "분류 전체보기" li 하나로 한 번 더 감싼다.
 *   ul > li(분류 전체보기) > [a, ul > li(상위) > [a, ul > li(하위)]]
 * 그 래퍼 li에 토글을 달면 사이드바 전체가 접혀 버린다. 루트 ul의 li가 하나뿐이고
 * 그 안에 ul이 있으면 래퍼로 보고 한 단계만 내려간다. (딱 한 번만 — 더 내려가면
 * 상위 카테고리가 하나뿐인 블로그에서 엉뚱한 층을 고른다)
 */
function pickList(rootUl) {
  const lis = childrenByTag(rootUl, 'LI')
  if (lis.length !== 1) return rootUl
  const nested = childrenByTag(lis[0], 'UL')
  return nested.length === 1 ? nested[0] : rootUl
}

/** li 자신의 링크. 하위 목록 안쪽 링크를 잘못 집지 않도록 sub를 제외한다. */
function ownAnchor(li, sub) {
  const direct = childrenByTag(li, 'A')
  if (direct.length) return direct[0]
  const all = li.getElementsByTagName('a')
  for (let i = 0; i < all.length; i++) {
    if (!sub.contains(all[i])) return all[i]
  }
  return null
}

/**
 * 버튼 이름에 쓸 카테고리 이름.
 * 앵커 안에는 글 수 배지가 요소로 섞여 있다(렌더 예: `<a> IT <span>(37)</span> </a>`).
 * 그 요소의 클래스 이름을 모르므로, 요소 자식은 통째로 무시하고 직속 텍스트 노드만 모은다.
 */
function labelOf(a) {
  let t = ''
  let n = a.firstChild
  while (n) {
    if (n.nodeType === 3) t += n.nodeValue
    n = n.nextSibling
  }
  t = t.replace(/\s+/g, ' ').trim()
  return t || a.textContent.replace(/\s+/g, ' ').trim()
}

/** 퍼센트 인코딩을 벗긴 경로. 카테고리 이름에 공백·&·한글이 들어간다. */
function decodePath(p) {
  if (!p) return ''
  if (p.charAt(0) !== '/') p = '/' + p
  try {
    return decodeURIComponent(p)
  } catch (e) {
    return p // 잘못된 인코딩 — 원문끼리 비교한다
  }
}

/**
 * 지금 보고 있는 페이지가 이 링크 아래인가.
 *
 * 티스토리가 "선택된 항목"에 붙이는 클래스를 우리는 모른다(레퍼런스에 없다).
 * 그래서 클래스 대신 URL 경로를 대조한다 — /category/IT/Web 을 보고 있으면
 * /category/IT 가지를 펼친다. 경계를 '/'로 끊어 /category/IT 가 /category/ITSM 에
 * 걸리지 않게 한다.
 */
function onPath(here, path) {
  if (!path || path === '/') return false
  return here === path || here.indexOf(path + '/') === 0
}

export default function initCategory() {
  // .side-category · .side-body는 skin.html이 보장하는 우리 훅이다(hooks.md §6).
  const box = document.querySelector('.side-category .side-body')
  if (!box) return

  const rootUl = box.querySelector('ul')
  if (!rootUl) return // 목록 형식([##_category_list_##])이거나 구조가 다르다 — 물러난다

  const list = pickList(rootUl)
  const items = childrenByTag(list, 'LI')
  if (!items.length) return

  const here = decodePath(window.location.pathname)
  const made = []

  items.forEach(function (li) {
    try {
      const sub = childrenByTag(li, 'UL')[0]
      if (!sub) return // 하위가 없는 상위 카테고리 — 토글이 필요 없다
      const link = ownAnchor(li, sub)
      if (!link) return // 이름을 지을 근거가 없다. 건드리지 않는다

      if (!sub.id) sub.id = uniqueId('side-cat-sub')

      // 현재 보고 있는 가지는 펼친 채로 시작한다.
      // 상위 링크가 안 맞더라도 하위 링크 중 하나가 맞으면 펼친다
      // (티스토리가 하위 카테고리에 계층 없는 URL을 줄 가능성 대비).
      let open = onPath(here, decodePath(link.pathname))
      if (!open) {
        const subLinks = sub.getElementsByTagName('a')
        for (let i = 0; i < subLinks.length; i++) {
          if (onPath(here, decodePath(subLinks[i].pathname))) {
            open = true
            break
          }
        }
      }

      const btn = document.createElement('button')
      btn.type = 'button'
      btn.className = 'cat-toggle'
      btn.setAttribute('aria-controls', sub.id)
      // 이름은 상태를 말하지 않는다. 상태는 aria-expanded 하나만 말한다 —
      // 두 곳에서 말하면 언젠가 서로 어긋난다(QA F2가 그 사고였다).
      const name = document.createElement('span')
      name.className = 'a11y-hidden'
      name.textContent = labelOf(link) + ' 하위 카테고리'
      btn.appendChild(name)
      btn.insertAdjacentHTML('beforeend', CHEVRON)

      // 링크 다음, 하위 목록 앞. DOM 순서와 화면 순서가 같다.
      li.insertBefore(btn, sub)
      li.classList.add('has-toggle')

      function apply(state) {
        // 클래스와 aria-expanded를 한 함수에서만 바꾼다. 갈라지면 어긋난다.
        li.classList.toggle('is-expanded', state)
        li.classList.toggle('is-collapsed', !state)
        btn.setAttribute('aria-expanded', state ? 'true' : 'false')
      }

      btn.addEventListener('click', function () {
        apply(!li.classList.contains('is-expanded'))
      })

      apply(open)
      made.push(li)
    } catch (e) {
      /* 항목 하나가 실패해도 나머지는 처리한다 */
    }
  })

  // 접을 것이 하나도 없었다 = 구조가 예상과 다르거나 하위 카테고리가 없다.
  // 흔적(빈 컨테이너 클래스)을 남기지 않는다.
  if (!made.length) return
  list.classList.add('cat-tree')
}
