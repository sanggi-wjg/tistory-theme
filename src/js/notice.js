// 공지 본문 정규화 — hooks.md §5.7
//
// [##_notice_rep_desc_##]가 .contents_style 래퍼를 달고 오는지 **확인할 방법이 없다.**
// 렌더러가 <s_notice_rep>을 통째로 버려서 로컬에서 한 번도 렌더된 적이 없고,
// 공식 레퍼런스도 출력 마크업을 적지 않았다.
//
// 안 달고 온다면 조용히 이렇게 된다:
//   · content.css가 전부 .contents_style 스코프라 **본문 타이포가 하나도 안 걸린다**
//   · 빌드가 만든 인라인색 보정도 .contents_style 스코프라 다크에서 옛 글 색이 묻힌다
//   · tables.js · code.js · lightbox.js · inline-fix.js가 contentRoots()로 찾으므로 전부 건너뛴다
// 에러는 나지 않는다. 이 도메인이 실패하는 방식 그대로다.
//
// 그래서 없을 때만 붙인다. 티스토리가 이미 달아 왔으면 아무 일도 하지 않는다.
// 반드시 다른 본문 모듈보다 **먼저** 돌아야 한다 — 그들이 contentRoots()로 찾기 때문이다.

export default function initNotice() {
  const bodies = document.querySelectorAll('.notice-body')
  Array.prototype.slice.call(bodies).forEach(function (el) {
    if (el.classList.contains('contents_style')) return
    if (el.querySelector('.contents_style')) return // 티스토리가 안쪽에 달아 왔다
    el.classList.add('contents_style')
  })
}
