// 진입점. esbuild가 여기서부터 dist/images/script.js 한 파일로 묶는다.
//
// 원칙: 기능 하나가 실패해도 본문은 읽을 수 있어야 한다.
// 그래서 모든 모듈을 개별 try/catch로 감싼다. 한 모듈의 예외가 다음 모듈을 막지 않는다.

import initTheme from './theme.js'
import initNotice from './notice.js'
import initCode from './code.js'
import initTables from './tables.js'
import initLinks from './links.js'
import initLightbox from './lightbox.js'
import initToc from './toc.js'
import initHeadingAnchor from './heading-anchor.js'
import initCategory from './category.js'
import initCatChips from './cat-chips.js'
import initProgress from './progress.js'
import initInlineFix from './inline-fix.js'

function safe(name, fn) {
  try {
    fn()
  } catch (e) {
    // 티스토리에는 빌드 타임 검사가 없다. 조용히 죽는 대신 콘솔에 남긴다.
    if (window.console && console.warn) console.warn('[skin] ' + name + ' 실패:', e)
  }
}

function boot() {
  safe('theme', initTheme)
  // 공지 본문에 .contents_style이 없으면 붙인다. 아래 본문 모듈들이 그 클래스로 찾으므로
  // 반드시 먼저 돈다 — hooks.md §5.7
  safe('notice', initNotice)
  safe('code', initCode)
  safe('tables', initTables)
  safe('links', initLinks)
  safe('lightbox', initLightbox)
  safe('toc', initToc)
  // 목차 뒤에 둔다. 둘은 서로를 필요로 하지 않지만(소제목 3개 미만이면 목차만 없다),
  // 목차가 실패해도 앵커는 남아야 하므로 순서가 아니라 safe()가 그것을 보장한다.
  safe('heading-anchor', initHeadingAnchor)
  // 사이드바 높이를 바꾸므로 문서 높이를 재는 진행바보다 먼저 돈다
  safe('category', initCategory)
  // 같은 트리를 읽어 헤더 안 칩을 채운다(결정 50). 헤더 높이를 바꾸므로 진행바보다 먼저
  safe('cat-chips', initCatChips)
  // 진행바는 본문 DOM이 다 만들어진 뒤에 높이를 재야 한다
  safe('progress', initProgress)
  // 인라인색 안전망은 CSS 보정이 이미 적용된 계산값을 보므로 마지막이다
  safe('inline-fix', initInlineFix)
}

// script는 </body> 직전에 있지만, 티스토리가 위치를 바꿀 가능성에 대비해 두 경우를 모두 본다.
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot, { once: true })
} else {
  boot()
}
