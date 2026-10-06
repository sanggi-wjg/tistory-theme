// 목록 페이징의 현재 페이지 — hooks.md §8, DECISIONS.md 결정 53
//
// 티스토리는 [##_paging_rep_link_num_##]를 숫자가 아니라 <span class="selected">N</span>으로
// 치환한다. 현재 위치 신호는 그 span뿐이라 CSS가 `.paging a:has(> .selected)`로 색을 입히는데,
// 색은 스크린리더에 안 보인다(결정 63). 그 span을 품은 앵커에
// aria-current="page"를 붙인다. 이전/다음에는 span.selected가 붙지 않는다(라이브 실측).

export default function initPaging() {
  const marks = document.querySelectorAll('.paging a > .selected')
  for (let i = 0; i < marks.length; i++) {
    marks[i].parentNode.setAttribute('aria-current', 'page')
  }
}
