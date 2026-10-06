// 소제목 앵커 — hooks.md §5.8
//
// 소제목 하나를 가리켜 공유할 수단이 없었다. 목차 링크가 유일한 통로인데
// 목차는 소제목 3개 이상일 때만 생긴다 — 실측 32%의 글에는 아예 없다.
// 그래서 **목차와 독립적으로** 돈다. 대신 루트와 id는 util이 한 곳에서 만든다.
//
// 보이는 `#` 글자는 CSS ::before가 그린다(content.css). 텍스트 노드로 넣지 않는
// 이유는 소제목의 textContent가 **목차 라벨이자 검색결과에 실리는 제목**이기
// 때문이다 — 넣으면 목차에 "개요#"가 뜨고 색인에도 그대로 들어간다.
// aria-label은 textContent에 들지 않으므로 소제목에 이름을 줘도 둘 다 오염되지 않는다.

import { entryRoot, headingsWithIds } from './util.js'

export default function initHeadingAnchor() {
  const root = entryRoot()
  if (!root) return // 글 페이지가 아니다

  headingsWithIds(root).forEach(function (h) {
    // 라벨은 앵커를 붙이기 **전에** 읽는다.
    const label = h.textContent.replace(/\s+/g, ' ').trim()

    const a = document.createElement('a')
    a.className = 'heading-anchor'
    a.href = '#' + h.id
    // 링크 목록으로 훑는 사용자에게 `#`은 전부 같은 이름이다. 소제목을 라벨로 준다.
    a.setAttribute('aria-label', label + ' 링크')

    // 앵커가 소제목 **안**에 있으면 그 aria-label이 소제목의 이름에 합쳐진다 —
    // 헤딩 목록에서 「개요 개요 링크」로 두 번 읽혔다(라이브 접근성 트리, 결정 63).
    // 소제목에 제 이름을 직접 준다. 앵커를 밖으로 빼면 content.css의 `h2:hover .heading-anchor`
    // 노출 규칙과 본문의 인접 선택자가 깨지고, aria-hidden으로 숨기면 키보드 사용자가 링크를 잃는다.
    // 글쓴이가 이미 이름을 줬으면 건드리지 않는다.
    if (!h.hasAttribute('aria-label') && !h.hasAttribute('aria-labelledby')) {
      h.setAttribute('aria-label', label)
    }

    h.appendChild(a)
  })
}
