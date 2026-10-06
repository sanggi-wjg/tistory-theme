// 카드 링크의 이름 — hooks.md §2
//
// 카드는 전체가 <a class="post-link"> 하나다(중첩 앵커 금지). 그래서 링크 이름이 카테고리·제목·
// 발췌 전체·날짜를 다 읽은 약 500자가 됐다(라이브 접근성 트리, 결정 63).
// 링크 이름을 그 안의 제목으로 좁힌다. 대가: 이름이 정해진 링크는 스크린리더가 안쪽 글자 대신
// 이름을 읽는 경우가 많아, 카테고리·발췌·날짜를 그 자리에서 더는 못 들을 수 있다(낭독은 재지 않았다).

import { uniqueId } from './util.js'

export default function initCards() {
  const links = document.querySelectorAll('.post-link')
  for (let i = 0; i < links.length; i++) {
    try {
      const a = links[i]
      const title = a.querySelector('.post-title')
      // 제목이 없거나 비었으면 건드리지 않는다 — 빈 이름을 가리키면 이름이 아예 사라진다.
      if (!title || !title.textContent.trim()) continue
      if (!title.id) title.id = uniqueId('post-title-' + (i + 1))
      a.setAttribute('aria-labelledby', title.id)
    } catch (e) {
      /* 카드 하나가 실패해도 나머지는 처리한다 */
    }
  }
}
