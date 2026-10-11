// 관련 글에서 이전/다음 글과 겹치는 줄을 뺀다 — hooks.md §4·§8, 이슈 #162
//
// 티스토리의 이전/다음 글은 **같은 카테고리 안에서만** 움직이고, 바로 위 「'카테고리'의 다른 글」
// 4줄에는 그 이웃이 늘 들어 있었다(2026-10-11 라이브 5편 전부). 그래서 글 끝에서 같은 제목이 두 번 보인다.
// 이전/다음 카드는 「이전 글」·「다음 글」이라는 방향을 말하므로 그쪽을 남기고 관련 글 쪽을 뺀다.
// 다 빠지면 섹션째 감춘다 — 제목과 「카테고리 전체 보기」만 남은 빈 목록이 된다.
//
// 비교는 경로로만 한다. 관련 글 링크에만 `?category=<번호>`가 붙고 이전/다음 링크에는 없다(라이브 실측).
// 쿼리·해시를 버리고, 퍼센트 인코딩을 벗기고(대소문자·원문 한글 차이를 없앤다), 끝 '/'를 뗀다 —
// category.js의 decodePath·bare를 그대로 쓴다. 레일·칩이 「같은 경로」를 재는 규칙과 한 벌이다.
//
// JS가 안 돌면 중복이 남을 뿐 아무것도 깨지지 않는다. 줄은 감추지 않고 DOM에서 뗀다 —
// 남은 줄의 :first-child·:last-child가 실제 모양과 어긋나지 않게.

import { decodePath, bare } from './category.js'

/**
 * 같은 글인지 대조할 열쇠. 쿼리·해시 무시, 디코딩, 끝 '/' 제거.
 * 빈 href·'#…'·루트('/')·해석할 수 없는 href는 ''을 낸다 — ''은 무엇과도 겹치지 않는다.
 * 빈 href를 그대로 해석하면 지금 페이지 경로가 되어 엉뚱한 줄과 맞을 수 있다.
 */
export function entryPath(href, base) {
  if (!href || href.charAt(0) === '#') return ''
  let p
  try {
    p = new URL(href, base).pathname
  } catch (e) {
    return ''
  }
  p = bare(decodePath(p))
  return p === '/' ? '' : p
}

/** relatedHrefs 가운데 navHrefs와 같은 글을 가리키는 것의 번호. */
export function duplicateIndexes(relatedHrefs, navHrefs, base) {
  const nav = new Set()
  navHrefs.forEach(function (h) {
    const k = entryPath(h, base)
    if (k) nav.add(k)
  })
  const out = []
  relatedHrefs.forEach(function (h, i) {
    const k = entryPath(h, base)
    if (k && nav.has(k)) out.push(i)
  })
  return out
}

function hrefOf(a) {
  return a ? a.getAttribute('href') || '' : ''
}

export default function initRelated() {
  // 셋 다 skin.html이 내보내는 훅이다(hooks.md §4). 없으면 글 페이지가 아니거나 이웃이 없다.
  const section = document.querySelector('.related')
  if (!section) return
  const nav = Array.prototype.slice.call(document.querySelectorAll('.postnav-item'))
  if (!nav.length) return

  const items = Array.prototype.slice.call(section.querySelectorAll('.related-item'))
  const drop = duplicateIndexes(
    items.map(function (li) {
      return hrefOf(li.querySelector('.related-link'))
    }),
    nav.map(hrefOf),
    window.location.href
  )
  if (!drop.length) return

  drop.forEach(function (i) {
    items[i].parentNode.removeChild(items[i])
  })
  // 링크를 못 읽은 줄은 drop에 들지 않으므로, 같아지는 것은 전부 뺐을 때뿐이다
  if (drop.length === items.length) section.hidden = true
}
