// 공지 본문 정규화 — hooks.md §5.7
//
// [##_notice_rep_desc_##]가 .contents_style 래퍼를 달고 오는지 **확인할 방법이 없다.**
// 공식 레퍼런스가 출력 마크업을 적지 않았고, 라이브에는 공지가 없어 본 적이 없다.
//
// 안 달고 온다면 조용히 이렇게 된다:
//   · content.css가 전부 .contents_style 스코프라 **본문 타이포가 하나도 안 걸린다**
//   · 빌드가 만든 인라인색 보정도 .contents_style 스코프라 다크에서 옛 글 색이 묻힌다
//   · tables.js · code.js · lightbox.js · inline-fix.js가 contentRoots()로 찾으므로 전부 건너뛴다
// 에러는 나지 않는다. 이 도메인이 실패하는 방식 그대로다.
//
// 그래서 skin.html이 .notice-body에 contents_style을 **처음부터** 단다(린트 BND012).
// 예전에는 여기서 없을 때 붙였는데, 첫 페인트 뒤에 본문 시트가 걸려 공지마다 문단 여백만큼
// 아래가 밀렸다(이슈 #97 — 프리뷰 공지 2건에 48px).
//
// 여기서 하는 일은 그 반대 경우다 — 티스토리가 안쪽에 래퍼를 달아 오면 바깥 것을 뗀다.
// 두 겹이면 contentRoots()가 같은 본문을 두 번 낸다. lightbox.js는 루트마다 click 리스너를
// 걸므로 이미지 하나에 라이트박스가 두 번 열린다. 안쪽 래퍼가 같은 시트를 받으므로 떼어도
// 기하는 그대로다. 반드시 다른 본문 모듈보다 **먼저** 돌아야 한다.

export default function initNotice() {
  const bodies = document.querySelectorAll('.notice-body')
  Array.prototype.slice.call(bodies).forEach(function (el) {
    if (el.querySelector('.contents_style')) el.classList.remove('contents_style')
  })
}
