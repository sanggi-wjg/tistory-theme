// 소제목 앵커 — hooks.md §5.8
//
// 소제목 하나를 가리켜 공유할 수단이 없었다. 목차 링크가 유일한 통로인데
// 목차는 소제목 3개 이상일 때만 생긴다 — 실측 32%의 글에는 아예 없다.
// 그래서 **목차와 독립적으로** 돈다. 대신 루트와 id는 util이 한 곳에서 만든다.
//
// 보이는 `#` 글자는 CSS ::before가 그린다(content.css). 텍스트 노드로 넣지 않는
// 이유는 소제목의 textContent가 **목차 라벨이자 검색결과에 실리는 제목**이기
// 때문이다 — 넣으면 목차에 "개요#"가 뜨고 색인에도 그대로 들어간다.

import { entryRoot, headingsWithIds } from './util.js'

export default function initHeadingAnchor() {
  const root = entryRoot()
  if (!root) return // 글 페이지가 아니다

  headingsWithIds(root).forEach(function (h) {
    // 라벨은 앵커를 붙이기 **전에** 읽는다.
    const label = h.textContent.trim()

    const a = document.createElement('a')
    a.className = 'heading-anchor'
    a.href = '#' + h.id
    // 링크 목록으로 훑는 사용자에게 `#`은 전부 같은 이름이다. 소제목을 라벨로 준다.
    a.setAttribute('aria-label', label + ' 링크')

    h.appendChild(a)
  })
}
