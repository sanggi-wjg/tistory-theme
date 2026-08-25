// 외부링크 표시 — hooks.md §5.6 · DESIGN.md §6.5
//
// 본문 외부링크(실측 65개)에 target="_blank" rel="noopener"와 작은 아이콘을 붙인다.
// 이미지 링크는 건드리지 않는다 — 아이콘이 그림 옆에 붙어 지저분해진다.

import { contentRoots } from './util.js'

const ICON =
  '<svg class="external-icon" width="11" height="11" viewBox="0 0 12 12" aria-hidden="true" focusable="false">' +
  '<path d="M4.5 1.5h6v6M10.5 1.5 5 7" fill="none" stroke="currentColor" stroke-width="1.4"' +
  ' stroke-linecap="round" stroke-linejoin="round"></path>' +
  '<path d="M9 8v2.5H1.5V3H4" fill="none" stroke="currentColor" stroke-width="1.4"' +
  ' stroke-linecap="round" stroke-linejoin="round"></path></svg>'

function isExternal(a) {
  const href = a.getAttribute('href')
  if (!href) return false
  // 앵커·mailto·tel·javascript는 대상이 아니다
  if (/^(#|mailto:|tel:|javascript:)/i.test(href)) return false
  if (a.protocol !== 'http:' && a.protocol !== 'https:') return false
  if (!a.host) return false
  return a.host !== window.location.host
}

export default function initLinks() {
  contentRoots().forEach(function (root) {
    Array.prototype.slice.call(root.querySelectorAll('a[href]')).forEach(function (a) {
      try {
        if (a.classList.contains('external-link')) return
        if (!isExternal(a)) return
        if (a.querySelector('img')) return // 이미지 링크는 그대로 둔다

        a.setAttribute('target', '_blank')
        // 기존 rel 토큰을 지우지 않고 더한다
        const rel = (a.getAttribute('rel') || '').split(/\s+/).filter(Boolean)
        if (rel.indexOf('noopener') === -1) rel.push('noopener')
        if (rel.indexOf('noreferrer') === -1) rel.push('noreferrer')
        a.setAttribute('rel', rel.join(' '))
        a.classList.add('external-link')

        // 새 창으로 열린다는 사실은 스크린리더에도 알려야 한다.
        // .a11y-hidden은 skin.html이 이미 쓰는 계약 클래스다(hooks.md §7).
        const sr = document.createElement('span')
        sr.className = 'a11y-hidden'
        sr.textContent = ' (새 창)'
        a.appendChild(sr)
        a.insertAdjacentHTML('beforeend', ICON)
      } catch (e) {
        /* 링크 하나가 실패해도 나머지는 처리한다 */
      }
    })
  })
}
