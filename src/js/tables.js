// 표 가로스크롤 래핑 — hooks.md §5.6
//
// 표는 7편 14%뿐이지만 최대 4열이라 모바일에서 반드시 넘친다.
// overflow-x 컨테이너로 감싸 표만 스크롤되게 한다(페이지가 통째로 가로 스크롤하지 않게).

import { contentRoots } from './util.js'

export default function initTables() {
  contentRoots().forEach(function (root) {
    Array.prototype.slice.call(root.querySelectorAll('table')).forEach(function (table) {
      const parent = table.parentNode
      if (!parent) return
      if (parent.classList && parent.classList.contains('table-scroll')) return

      const wrap = document.createElement('div')
      wrap.className = 'table-scroll'
      // 스크롤 되는 영역은 키보드로도 스크롤할 수 있어야 한다.
      // tabindex를 주면 role/이름이 필요하다(그러지 않으면 정체 불명의 탭 정거장이 된다).
      wrap.setAttribute('tabindex', '0')
      wrap.setAttribute('role', 'region')
      wrap.setAttribute('aria-label', '표')

      parent.insertBefore(wrap, table)
      wrap.appendChild(table)
    })
  })
}
