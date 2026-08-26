#!/usr/bin/env python3
"""티스토리 치환자 로컬 렌더러.

src/skin.html의 치환자를 data/posts.json 픽스처로 치환해
페이지 타입별 HTML을 _preview/에 출력한다.

티스토리 서버가 하는 일을 흉내내되, 완벽히 같지는 않다.
알려진 차이는 SKILL.md의 "렌더러가 재현하지 못하는 것"에 정리되어 있다.

사용:
  python3 .claude/skills/skin-preview/scripts/render.py
  python3 .claude/skills/skin-preview/scripts/render.py --page index,page
"""
import argparse
import html
import json
import os
import re
import sys
from urllib.parse import quote

ROOT = os.getcwd()
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(ROOT, "_preview")

# 그룹 래퍼 밖에 놓인 *_group 치환자에 그리는 경고 상자.
# 티스토리는 이 경우 조용히 빈 문자열을 내놓는다 — 프리뷰까지 침묵하면 못 찾는다.
#   대괄호를 &#91;/&#93;로 쓴다 — 리터럴로 두면 VALUE_RE가 이 경고문 안의
#   치환자를 다시 치환해 자기 자신을 무한히 감싼다 (2026-08-26에 실제로 났다).
WRAP_WARN = ('<div style="border:2px dashed #d60000;color:#d60000;padding:12px;'
             'font:600 13px/1.5 monospace">&#91;##_%s_##&#93;이 &lt;%s&gt; 밖에 있다. '
             '티스토리는 여기서 <b>빈 문자열</b>을 내놓는다 — 이 영역이 통째로 '
             '사라진다 (린트 SUB009).</div>')

# 래퍼 안에서 실제로 그려질 것. 서버가 내놓는 것은 빈 div 하나이고
# 알맹이는 티스토리 React가 나중에 채운다 (레퍼런스 1240행).
REACT_BOX = ('<div data-tistory-react-app="Comment">'
             '<div class="tt-comment-cont">[%s: 티스토리 React가 렌더링]</div></div>')

PAGE_TYPES = {
    "index":     "tt-body-index",
    "page":      "tt-body-page",
    "category":  "tt-body-category",
    "search":    "tt-body-search",
    "tag":       "tt-body-tag",
    "archive":   "tt-body-archive",
    "guestbook": "tt-body-guestbook",
    "empty":     "tt-body-search",   # 결과 0건 시나리오
    # 소제목이 3개 이상이라 목차가 생기는 글. page는 2개뿐이라 목차가 안 생긴다.
    # 둘 다 내지 않으면 **실측 68%인 다수 경로가 프리뷰에 한 번도 안 나온다.**
    # 레이아웃도 갈린다 — body.no-toc 유무로 폭이 1,136 ↔ 848로 바뀐다(layout.css).
    "page_toc":  "tt-body-page",
    # /tag(클라우드)와 /tag/이름(목록)은 body_id가 둘 다 tt-body-tag지만
    # 렌더되는 영역이 다르다. 한 페이지에 둘 다 그리면 h1이 두 개가 되어
    # 실블로그에 없는 화면을 보게 된다. 그래서 나눈다 —
    #   tag       → /tag/이름 : 목록 (LIST_PAGES에 있다)
    #   tag_cloud → /tag      : 클라우드 (LIST_PAGES에 없다)
    "tag_cloud": "tt-body-tag",
}

LIST_PAGES = {"category", "search", "tag", "archive", "empty"}

# <s_list>는 **홈에서도 렌더된다.** 2026-08-25 실측 — 홈에 list_conform "전체 글",
# list_count(전체 글 수), 글 카드, 페이징이 모두 나왔다. 렌더러가 이걸 몰라서
# 프리뷰의 홈은 s_index_article_rep로만 그려졌고, 그 영역이 실제로는 죽어 있다는
# 것을 배포 전까지 아무도 볼 수 없었다.
LIST_AREA_PAGES = LIST_PAGES | {"index"}

# s_article_rep의 하위 영역. 바깥에 두면 티스토리가 통째로 버린다 (DECISIONS.md 결정 29).
ARTICLE_REP_CHILDREN = ("s_index_article_rep", "s_permalink_article_rep")

# 위 영역 중 s_article_rep 바깥에 있어 이번 렌더에서 버려진 것들.
ORPHAN_AREAS = set()


def scan_orphan_areas(skin):
    """티스토리와 같은 판단을 미리 내린다 — 버릴 영역을 정하고 경고한다.

    렌더러가 이 규칙을 몰랐던 것이 이번 사고의 절반이다. 린트(SUB008)가 잡더라도,
    프리뷰가 "잘 나온다"고 보여 주면 사람은 프리뷰를 믿는다."""
    ORPHAN_AREAS.clear()
    for child in ARTICLE_REP_CHILDREN:
        for m in re.finditer(r"<%s(?:\s[^>]*)?>" % child, skin, re.I):
            before = skin[:m.start()]
            if len(re.findall(r"<s_article_rep(?:\s[^>]*)?>", before, re.I)) <= \
               len(re.findall(r"</s_article_rep>", before, re.I)):
                ORPHAN_AREAS.add(child)
                sys.stderr.write(
                    "  [경고] <%s>가 <s_article_rep> 바깥에 있다 — 티스토리가 이 영역을 "
                    "통째로 버린다. 프리뷰도 똑같이 버린다 (린트 SUB008).\n" % child)
                break

# 실제 글에서 관찰된 오염 패턴을 그대로 담은 본문 픽스처.
# 인라인 color/background-color/font-family 보정 규칙이 동작하는지 여기서 확인한다.
# ── 티스토리가 실제 페이지에 끼워 넣는 스타일시트 ──────────────────────
#
# 이걸 빼면 프리뷰는 **우리 CSS만** 그린다. 그러면 다크에서 인용문이 사라지는 종류의
# 결함이 프리뷰에서 멀쩡해 보인다 — 원인이 우리 CSS가 아니라 티스토리 CSS와의
# 특이도 싸움이기 때문이다. 프리뷰가 통과 신호를 위조한 사고를 이미 두 번 겪었다
# (CLAUDE.md 2026-08-25 두 항목). 세 번째를 만들지 않으려면 상대를 불러와야 한다.
#
# **순서가 곧 검사다.** 실제 <head>에서 content.css는 우리보다 앞, atom-one-light는
# 우리보다 뒤에 온다. 뒤에 오는 쪽은 특이도가 같으면 이긴다 — 그 조건을 재현해야
# `.hljs` 접두가 정말 필요한지 눈으로 확인된다. 여기 순서를 바꾸지 말 것.
TISTORY_CONTENT_CSS = ("https://tistory1.daumcdn.net/tistory_admin/userblog/"
                       "userblog-d748cfd5e0a0f73a4f05afc297a1e4fc6364eea5/static/style/content.css")
TISTORY_HLJS_CSS = ("https://cdnjs.cloudflare.com/ajax/libs/highlight.js/10.7.3/"
                    "styles/atom-one-light.min.css")

# 네트워크가 없으면 위 두 시트가 조용히 빠지고 프리뷰는 다시 거짓말을 한다.
# 눈에 띄는 띠를 띄워 "지금 보고 있는 것은 반쪽"이라고 알린다.
# ⚠ `%` 포맷을 쓰지 않는다. 이 문자열은 CSS를 담고 있어 `width:100%` 같은 값이
#    언제든 들어올 수 있고, 그러면 "%" 포맷이 ValueError로 터진다. 자리표시자로 바꾼다.
TISTORY_CSS_GUARD = """
<script>
(function () {
  var need = __NEED__, ok = 0;
  function warn() {
    if (ok >= need) return;
    var b = document.createElement('div');
    b.textContent = '⚠ 티스토리 스타일시트를 불러오지 못했다 (' + ok + '/' + need + '). ' +
      '지금 화면은 우리 CSS만 그린 결과라, 티스토리와의 특이도 충돌은 재현되지 않는다.';
    b.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:99999;padding:10px 14px;' +
      'background:#f5a623;color:#171717;font:13px/1.5 system-ui;text-align:center';
    document.body.appendChild(b);
  }
  window.__tistoryCssLoaded = function () { ok++; };
  window.addEventListener('load', function () { setTimeout(warn, 300); });
}());
</script>"""


# 본문 픽스처는 "열기 + 알맹이 + 닫기"로 나눠 조립한다.
# 예전에는 ARTICLE_BODY.replace("</div>", …, 1)로 목차용 변형을 만들었는데,
# 알맹이에 <div>가 하나라도 생기는 순간 **첫 </div>가 안쪽 것**이 되어 조용히
# 엉뚱한 자리에 붙는다. 오픈그래프 카드가 div를 쓰면서 실제로 그렇게 됐다.
ARTICLE_BODY_INNER = """
<p data-ke-size="size16"><span style="font-family: AppleSDGothicNeo-Regular, 'Malgun Gothic', sans-serif;">힙 덤프는 깨끗한데 컨테이너 RSS만 계속 올라갔다. 논힙 영역을 하나씩 벗겨내다 커넥션 풀 설정에 도달했다.</span></p>
<blockquote data-ke-style="style3">HikariCP의 <code>maxLifetime</code>은 반드시 DB의 <code>wait_timeout</code>보다 짧아야 한다.</blockquote>
<h2 data-ke-size="size26"><span style="color: #000000;">Socket 버퍼는 어디에 쌓이는가</span></h2>
<p data-ke-size="size16"><span style="color: #333333;">네이티브 메모리를 봐야 했다. </span><code>jcmd</code><span style="color: #333333;">의 </span><code>VM.native_memory</code><span style="color: #333333;">로 커밋된 영역을 뜯어보면 Internal이 비정상적으로 크다.</span></p>
<pre id="code_1" class="javascript" data-ke-language="javascript" data-ke-type="codeblock"><code>$ jcmd 1 VM.native_memory summary
Total: reserved=2841MB, committed=1974MB
-  Internal (reserved=612MB, committed=612MB)
-      Thread (reserved=318MB, committed=318MB)</code></pre>
<p><figure class="imageblock alignCenter" data-ke-mobileStyle="widthOrigin" data-origin-width="800" data-origin-height="533"><span data-url="https://placehold.co/800x450/eeeeee/999999?text=screenshot"><img src="https://placehold.co/800x450/eeeeee/999999?text=screenshot" alt=""></span><figcaption>논힙 메모리 추이</figcaption></figure></p>
<h2 data-ke-size="size26"><span style="color: #252525;">maxLifetime 조정과 검증</span></h2>
<p data-ke-size="size16" style="background-color: #f8f8f8;">설정을 바꾼 뒤 24시간 동안 RSS 추이를 관찰했다. 증가 곡선이 사라졌다.</p>
<table><thead><tr><th>항목</th><th>변경 전</th><th>변경 후</th><th>비고</th></tr></thead>
<tbody><tr><td>maxLifetime</td><td>1800s</td><td>240s</td><td>wait_timeout 300s</td></tr>
<tr><td>RSS 증가</td><td>+40MB/h</td><td>0</td><td>-</td></tr></tbody></table>
<pre data-ke-type="codeblock"><code>spring:
  datasource:
    hikari:
      max-lifetime: 240000
      keepalive-time: 120000</code></pre>
<p data-ke-size="size16"><a href="https://github.com/brettwooldridge/HikariCP">HikariCP 공식 문서</a>와 <a href="https://sanggi-jayg.tistory.com/entry/prev">1편</a>을 함께 보면 좋다.</p>
<p data-ke-size="size16"><span style="color: #eeffff;">라이트 모드에서 안 보이는 색으로 쓴 문장이다.</span></p>
"""

# ── 티스토리 에디터 컴포넌트 ─────────────────────────────────────────
# 티스토리 content.css가 **라이트 전용 색을 박아 둔** 요소들이다. 하나라도 빼면
# 그 컴포넌트의 다크 결함이 프리뷰에서 보이지 않는다. 실측 개수와 원본 색은
# data/tistory-hardcoded-colors.json에 있고, 린트 TIS001이 그 목록을 지킨다.
#
# .another_category의 규칙은 CDN 시트가 아니라 **페이지 안 <style>**로 오고 전부
# !important다. 그것까지 재현해야 우리 덮어쓰기가 정말 이기는지 보인다.
EDITOR_COMPONENTS = """
<figure data-ke-type="opengraph"><a href="https://example.com"><div class="og-image" style="background-image:url(https://placehold.co/240x160/eeeeee/999999?text=og)"></div><div class="og-text"><p class="og-title">오픈그래프 링크 카드 제목 — 실측 62곳 / 39편</p><p class="og-desc">이 카드의 제목과 링크가 #000이라 다크에서 1.00:1이 된다.</p><p class="og-host">example.com</p></div></a></figure>
<blockquote data-ke-style="style1">스타일1 인용 — ID 스코프라 클래스만으로는 못 이긴다.<cite>출처: 실측 7곳</cite></blockquote>
<blockquote data-ke-style="box">박스 인용 — 배경 #fcfcfc가 박혀 다크에서 흰 카드가 된다.</blockquote>
<blockquote data-ke-style="style2"><p>인용 안의 문단이다. 티스토리 `blockquote p { color:#666 }`가 <strong>직접 지정</strong>이라 상속을 이긴다 — blockquote만 칠하면 이 줄은 안 바뀐다. 실측 57곳 / 25편으로 인용 중 가장 흔한 형태다.</p></blockquote>
<figure class="fileblock"><a href="#"><span class="filename">첨부파일.zip</span><span class="size">1.2MB</span></a></figure>
<table data-ke-style="style12"><tbody><tr><td>머리 행</td><td>값</td></tr><tr><td>첫 열</td><td>홀수 행</td></tr><tr><td>첫 열</td><td>짝수 행</td></tr></tbody></table>
<style>
.another_category_color_gray * { color:#909090 !important; }
.another_category_color_gray h4,
.another_category_color_gray h4 a { color:#737373 !important; }
.another_category_color_gray,
.another_category_color_gray h4 { border-color:#E5E5E5 !important; }
</style>
<div class="another_category another_category_color_gray"><h4><a href="#">'네트워크' 카테고리의 다른 글</a></h4><table><tbody><tr><th><a href="#">티스토리가 본문 끝에 붙이는 상자다</a></th><td>2026.04.30</td></tr></tbody></table></div>
"""

# 소제목 3개 이상(h2 3 + h3 1). 목차·스크롤스파이·데스크톱 2단 경로를 여기서 본다.
TOC_EXTRA = """
<h2 data-ke-size="size26">커넥션 유효성 검사</h2>
<p data-ke-size="size16">세 번째 소제목이다. 이 글은 목차가 생긴다.</p>
<h3 data-ke-size="size23">test-query를 쓰지 않는 이유</h3>
<p data-ke-size="size16">JDBC4 드라이버는 <code>isValid()</code>를 쓴다.</p>
<table><thead><tr><th>항목</th><th>값</th><th>비고</th><th>기본</th></tr></thead>
<tbody><tr><td>maxLifetime</td><td>240000</td><td>DB wait_timeout보다 짧게</td><td>1800000</td></tr></tbody></table>
"""

_OPEN = '<div class="tt_article_useless_p_margin contents_style">'
ARTICLE_BODY = _OPEN + ARTICLE_BODY_INNER + EDITOR_COMPONENTS + "</div>"
ARTICLE_BODY_TOC = _OPEN + ARTICLE_BODY_INNER + TOC_EXTRA + EDITOR_COMPONENTS + "</div>"


def load_fixtures():
    with open(os.path.join(ROOT, "data", "posts.json"), encoding="utf-8") as f:
        posts = json.load(f)["posts"]
    for i, p in enumerate(posts):
        p["_i"] = i
        p["_link"] = "/entry/post-%d" % i
        p["_summary"] = (
            "이 글은 로컬 프리뷰용 요약이다. 실제 요약 길이를 흉내내기 위해 "
            "적당한 분량의 한국어 문장을 채워 넣었다. 카드 레이아웃에서 몇 줄까지 "
            "표시되는지 확인하는 용도다."
        )
    cats = json.load(open(os.path.join(ROOT, "data", "categories.json"), encoding="utf-8"))
    return posts, cats


def category_tree(cats):
    """상위 → 하위 트리로 접는다. 두 형식이 같은 데이터를 쓴다."""
    tree = {}
    for c, v in cats["categories"].items():
        if c.endswith("  (상위)"):
            continue
        top, _, sub = c.partition("/")
        tree.setdefault(top, {"n": 0, "subs": {}})
        if sub:
            tree[top]["subs"][sub] = v["total"]
        else:
            tree[top]["n"] += v["total"]
    for top in tree:
        tree[top]["n"] = sum(tree[top]["subs"].values()) + tree[top]["n"]
    return tree


def build_category_list_html(cats, posts, current=""):
    """[##_category_list_##](리스트형)의 출력을 그대로 재현한다.

    2026-08-25 sanggi-jayg.tistory.com 실측을 옮겼다 — 앵커 안쪽의 앞뒤 공백,
    글 수 span, li class="" 까지 포함해서다. 현재 카테고리의 li에는 class="selected"가
    붙는다(같은 날 /category/Python 실측). 이 이름들이 tistory.css와 category.js의
    유일한 접점이므로, 여기서 한 글자라도 다르면 프리뷰가 통과 신호를 위조한다.
    """
    tree = category_tree(cats)

    def li(cls):
        return '<li class="selected">' if cls else '<li class="">'

    out = ['<ul class="tt_category">%s<a href="/category" class="link_tit"> 분류 전체보기 '
           '<span class="c_cnt">(%d)</span> </a>' % (li(False), len(posts)),
           '<ul class="category_list">']
    for top, v in sorted(tree.items(), key=lambda kv: -kv[1]["n"]):
        out.append('%s<a href="/category/%s" class="link_item"> %s '
                   '<span class="c_cnt">(%d)</span> </a>' % (
                       li(current == top), html.escape(top), html.escape(top), v["n"]))
        if v["subs"]:
            out.append('<ul class="sub_category_list">')
            for s, n in sorted(v["subs"].items(), key=lambda kv: -kv[1]):
                out.append('%s<a href="/category/%s/%s" class="link_sub_item"> %s '
                           '<span class="c_cnt">(%d)</span> </a></li>' % (
                               li(current == top + "/" + s),
                               html.escape(top), html.escape(s), html.escape(s), n))
            out.append("</ul>")
        out.append("</li>")
    out.append("</ul></li></ul>")
    return "\n".join(out)


def build_category_folder_html(cats, posts):
    """[##_category_##](폴더형)의 출력을 재현한다.

    **이 스킨은 이것을 쓰지 않는다** (린트 CAT001). 그래도 재현해 두는 이유는,
    누군가 치환자를 되돌렸을 때 프리뷰가 리스트형을 그려서 "잘 나온다"고
    거짓말하는 일을 막기 위해서다. 2026-08-25 첫 배포가 정확히 그 사고였다 —
    렌더러가 두 치환자를 같은 마크업에 매핑해 두어, 폴더형이 나간 것을
    배포 후 실물을 보고서야 알았다.

    2026-08-25 git-rich-quick.tistory.com 실측: 중첩 table, 트리선 GIF,
    a href 0개(onclick), div마다 인라인 color·background-color.
    """
    tree = category_tree(cats)
    gif = "https://tistory1.daumcdn.net/tistory_admin/blogs/image/tree/base/"
    color, bg = "#4d4d4d", "#ffffff"
    out = ['<table id="treeComponent" cellpadding="0" cellspacing="0" style="width: 100%;"><tr><td>']
    out.append(
        '<table id="category_0" cellpadding="0" cellspacing="0"><tr>'
        '<td class="ib" style="font-size: 1px"><img src="%stab_top.gif" width="16" '
        'onclick="expandTree()" alt="" style="display:block"></td>'
        '<td valign="top" style="font-size:9pt; padding-left:3px">'
        '<table id="imp0" cellpadding="0" cellspacing="0" style="background-color: %s;"><tr>'
        '<td class="branch3" onclick="window.location.href=\'/category\'">'
        '<div id="text_0" style="color: %s;">분류 전체보기<span class="c_cnt"> (%d)</span></div>'
        '</td></tr></table></td></tr></table>' % (gif, bg, color, len(posts)))
    for i, (top, v) in enumerate(sorted(tree.items(), key=lambda kv: -kv[1]["n"])):
        cid = 1000000 + i
        tab = "tab_closed.gif" if v["subs"] else "tab_isleaf.gif"
        out.append(
            '<table id="category_%d" cellpadding="0" cellspacing="0"><tr>'
            '<td class="ib" style="width:39px; font-size: 1px;  background-image: url(\'%snavi_back_noactive.gif\')">'
            '<a class="click" onclick="toggleFolder(\'%d\')"><img src="%s%s" width="39" alt=""></a></td><td>'
            '<table cellpadding="0" cellspacing="0" style="background-color: %s;"><tr>'
            '<td class="branch3" onclick="window.location.href=\'/category/%s\'">'
            '<div id="text_%d" style="color: %s;">%s<span class="c_cnt"> (%d)</span></div>'
            '</td></tr></table></td></tr></table>' % (
                cid, gif, cid, gif, tab, bg, quote(top), cid, color, html.escape(top), v["n"]))
        if v["subs"]:
            out.append('<div id="category_%d_children" style="display:none;">' % cid)
            for j, (s, n) in enumerate(sorted(v["subs"].items(), key=lambda kv: -kv[1])):
                sid = cid * 10 + j
                out.append(
                    '<table class="category_%d" cellpadding="0" cellspacing="0"><tr>'
                    '<td style="width:39px;font-size: 1px;"><img src="%snavi_back_active.gif" width="17" '
                    'height="18" alt=""/><img src="%stab_treed.gif" width="22" alt=""/></td><td>'
                    '<table onclick="window.location.href=\'/category/%s/%s\'" cellpadding="0" '
                    'cellspacing="0" style="background-color: %s;"><tr>'
                    '<td class="branch3"><div id="text_%d" style="color: %s;">%s'
                    '<span class="c_cnt"> (%d)</span></div></td></tr></table></td></tr></table>' % (
                        sid, gif, gif, quote(top), quote(s), bg, sid, color, html.escape(s), n))
            out.append("</div>")
    out.append("</td></tr></table>")
    return "\n".join(out)


def globals_for(page, posts, cats, skin_vars):
    # 홈의 list_conform은 "전체 글"이다 (2026-08-25 실측). 빈 문자열로 두면
    # 홈의 h1이 비어 보이고, V003이 실물과 어긋난다.
    # 카테고리 페이지의 list_conform은 **상위/하위 전체 경로**다 — 2026-08-25 실측
    # (git-rich-quick /category/경제/주식 → h1 "경제/주식"). 이 값이 사이드바 트리의
    # li.selected를 고르는 기준이기도 하므로 data/categories.json에 실재하는 이름이어야 한다.
    # 가장 긴 하위 이름을 고른 것은 의도적이다 — 240px 레일에서 줄바꿈이 나는지를
    # 선택 상태와 함께 매 렌더마다 눈에 띄게 하려는 것이다.
    conform = {"index": "전체 글",
               "category": "Python/성능과 동시성", "search": "OOMKilled",
               "tag": "hikaricp", "archive": "2026", "empty": "존재하지않는검색어"}.get(page, "")
    g = {
        "title": "상쾌한기분", "desc": "오늘도 상쾌한기분", "blogger": "상쾌한기분",
        "image": "https://placehold.co/200x200/eeeeee/999999?text=logo",
        "blog_image": '<img src="https://placehold.co/200x200/eeeeee/999999?text=logo" alt="">',
        "blog_link": "/", "rss_url": "/rss", "taglog_link": "/tag", "guestbook_link": "/guestbook",
        "page_title": "상쾌한기분", "body_id": PAGE_TYPES[page],
        "blog_menu": '<ul class="blog-menu"><li><a href="/">홈</a></li>'
                     '<li><a href="/tag">태그</a></li><li><a href="/guestbook">방명록</a></li></ul>',
        # 두 치환자를 **다른 마크업**에 매핑한다. 같은 것에 매핑해 두었다가
        # 2026-08-25 첫 배포에서 폴더형이 나간 것을 못 잡았다 (DECISIONS.md 결정 31).
        # 카테고리 페이지에서는 보고 있는 가지에 li.selected가 붙는다.
        "category": build_category_folder_html(cats, posts),
        "category_list": build_category_list_html(
            cats, posts, conform if page == "category" else ""),
        "count_total": "482,193", "count_today": "312", "count_yesterday": "487",
        "search_name": "search", "search_text": "", "search_onclick_submit": "return false;",
        "list_conform": conform, "list_count": "0" if page == "empty" else str(len(posts)),
        # 홈에서는 블로그 설명이 들어간다 (실측: "git-rich-quick 님의 블로그 입니다.").
        "list_description": ("오늘도 상쾌한기분" if page == "index"
                             else "카테고리 설명이 들어가는 자리다."),
        "list_style": "list", "list_image": "https://placehold.co/1200x300/eeeeee/999999?text=category",
        "prev_page": 'href="?page=1"', "next_page": 'href="?page=3"',
        "no_more_prev": "", "no_more_next": "",
        "revenue_list_upper": '<div class="_ad">[광고 자리: 홈·목록 상단]</div>',
        "revenue_list_lower": '<div class="_ad">[광고 자리: 홈·목록 하단]</div>',
        # ⚠ 래퍼 밖에서는 **경고를 그린다.** 티스토리는 조용히 빈 문자열로 치환하지만,
        #   프리뷰가 그 침묵을 그대로 흉내 내면 눈으로도 못 찾는다. 2026-08-26에
        #   [##_comment_group_##]이 <s_rp> 없이 나가 댓글이 통째로 사라졌는데,
        #   그때 이 렌더러는 래퍼와 무관하게 상자를 그려 **통과 신호를 위조했다**.
        #   진짜 상자는 s_rp / s_guest 핸들러가 ctx에 덮어써서 넣는다.
        "comment_group": WRAP_WARN % ("comment_group", "s_rp"),
        "guestbook_group": WRAP_WARN % ("guestbook_group", "s_guest"),
        # ⚠ 구분자는 공백이 아니라 **", "** 다. 티스토리는 <a> 사이에 쉼표
        #   텍스트 노드를 끼워 넣는다 (2026-08-26 라이브 실측):
        #     <a …>Memory</a>, <a …>performance</a>, …
        #   여기를 공백으로 두는 동안 프리뷰는 **통과 신호를 위조하고 있었다** —
        #   flex 컨테이너에서 그 텍스트 노드가 익명 아이템이 되어 칸을 차지하는
        #   현상이 재현되지 않았고, 본 블로그에서 태그마다 쉼표가 떠서야 드러났다.
        #   태그 개수도 실제 글(8개)에 맞춰 두 줄 넘침이 보이게 한다.
        "tag_label_rep": ", ".join('<a href="/tag/%s" rel="tag">%s</a>' % (t, t)
                                   for t in ["k8s", "spring", "jvm", "hikaricp",
                                             "oom", "profiler", "메모리", "__slots__"]),
    }
    for k, v in skin_vars.items():
        g["var_" + k] = v
    return g


def item_scope(p, prefix, page=""):
    d = p["date"] or "2026.01.01"
    parts = (d.split(".") + ["01", "01"])[:3]
    y, m, dd = parts[0].strip(), parts[1].strip(), parts[2].strip()
    return {
        prefix + "_link": p["_link"], prefix + "_title": html.escape(p["title"]),
        prefix + "_title_text": html.escape(p["title"]),
        prefix + "_category": html.escape(p["category"]),
        prefix + "_category_link": "/category/" + p["category"],
        prefix + "_date": "%s. %s. %s. 14:22" % (y, m, dd),
        prefix + "_simple_date": d, prefix + "_regdate": d,
        prefix + "_date_year": y, prefix + "_date_month": m, prefix + "_date_day": dd,
        prefix + "_date_hour": "14", prefix + "_date_minute": "22", prefix + "_date_second": "05",
        prefix + "_summary": p["_summary"],
        prefix + "_desc": ARTICLE_BODY_TOC if page == "page_toc" else ARTICLE_BODY,
        prefix + "_rp_cnt": str((p["_i"] * 7) % 13),
        prefix + "_author": "상쾌한기분",
        prefix + "_thumbnail": "https://placehold.co/400x250/eeeeee/999999?text=thumb",
        prefix + "_thumbnail_url": "https://placehold.co/400x250/eeeeee/999999?text=thumb",
        prefix + "_thumbnail_raw_url": "https://placehold.co/1200x750/eeeeee/999999?text=thumb",
        prefix + "_thumbnail_link": "https://placehold.co/200x125/eeeeee/999999?text=thumb",
        prefix + "_type": "thumb_type" if p["hasThumbnail"] else "text_type",
        "_has_thumb": p["hasThumbnail"],
    }


GROUP_RE = re.compile(r"<(s_[a-zA-Z0-9_]+)((?:\s[^>]*)?)>", re.I)


def find_block(text, start, name):
    """name 그룹의 여닫이 짝을 찾아 (inner, end_index) 반환. 중첩 동명 태그를 처리한다."""
    open_re = re.compile(r"<%s(?:\s[^>]*)?>" % re.escape(name), re.I)
    close_re = re.compile(r"</%s>" % re.escape(name), re.I)
    depth, pos = 1, start
    while depth:
        o, c = open_re.search(text, pos), close_re.search(text, pos)
        if not c:
            return None, None
        if o and o.start() < c.start():
            depth += 1
            pos = o.end()
        else:
            depth -= 1
            pos = c.end()
            if depth == 0:
                return text[start:c.start()], pos
    return None, None


def render(text, ctx, page, posts):
    """그룹 치환자를 재귀 처리한다."""
    out, pos = [], 0
    while True:
        m = GROUP_RE.search(text, pos)
        if not m:
            out.append(text[pos:])
            break
        name, attrs = m.group(1).lower(), m.group(2)
        inner, end = find_block(text, m.end(), name)
        if inner is None:                      # 닫는 태그 없음 → 그대로 둔다 (린트가 잡는다)
            out.append(text[pos:m.end()])
            pos = m.end()
            continue
        out.append(text[pos:m.start()])
        out.append(handle_group(name, attrs, inner, ctx, page, posts))
        pos = end
    return values(("".join(out)), ctx)


def repeat(inner, items, prefix, ctx, page, posts):
    buf = []
    for p in items:
        sub = dict(ctx)
        sub.update(item_scope(p, prefix, page))
        buf.append(render(inner, sub, page, posts))
    return "".join(buf)


def handle_group(name, attrs, inner, ctx, page, posts):
    R = lambda t, c=None: render(t, c or ctx, page, posts)
    is_list = page in LIST_PAGES

    if name == "s_t3":
        return '<script>/* [s_t3: 티스토리 공통 JS]*/</script>' + R(inner)
    if name.startswith("s_if_var_"):
        return R(inner) if truthy(ctx.get("var_" + name[9:])) else ""
    if name.startswith("s_not_var_"):
        return "" if truthy(ctx.get("var_" + name[10:])) else R(inner)

    # 페이지 영역
    if name in ORPHAN_AREAS:
        return ""
    if name == "s_index_article_rep":
        return repeat(inner, posts[:12], "article_rep", ctx, page, posts) if page == "index" else ""
    if name == "s_permalink_article_rep":
        return R(inner, {**ctx, **item_scope(posts[0], "article_rep", page)}) if page in ("page", "page_toc") else ""
    if name == "s_article_rep":
        if page in ("page", "page_toc"):
            return R(inner, {**ctx, **item_scope(posts[0], "article_rep", page)})
        if page == "index":
            return repeat(inner, posts[:12], "article_rep", ctx, page, posts)
        return ""
    if name == "s_list":
        return R(inner) if page in LIST_AREA_PAGES else ""
    if name == "s_list_rep":
        return (repeat(inner, posts[:20], "list_rep", ctx, page, posts)
                if (page in LIST_AREA_PAGES and page != "empty") else "")
    if name == "s_list_empty":
        return R(inner) if page == "empty" else ""
    if name == "s_list_image":
        return R(inner) if page == "category" else ""

    # 조건 — 대표이미지
    if name in ("s_article_rep_thumbnail", "s_list_rep_thumbnail", "s_rctps_rep_thumbnail",
                "s_notice_rep_thumbnail", "s_article_related_rep_thumbnail",
                "s_article_prev_thumbnail", "s_article_next_thumbnail", "s_cover_item_thumbnail"):
        return R(inner) if ctx.get("_has_thumb", True) else ""

    # 글 페이지 부속
    if name in ("s_article_related", "s_tag_label", "s_rp", "s_article_prev", "s_article_next"):
        if page not in ("page", "page_toc"):
            return ""
        if name == "s_article_prev":
            return R(inner, {**ctx, **item_scope(posts[1], "article_prev", page)})
        if name == "s_article_next":
            return R(inner, {**ctx, **item_scope(posts[2], "article_next", page)})
        if name == "s_rp":
            # 래퍼 안에서만 진짜 상자가 된다 — 밖에서는 base ctx의 경고가 그려진다.
            return R(inner, {**ctx, "comment_group": REACT_BOX % "댓글"})
        return R(inner)
    if name == "s_article_related_rep":
        return repeat(inner, posts[3:8], "article_related_rep", ctx, page, posts)

    # 사이드바
    if name in ("s_sidebar", "s_sidebar_element", "s_search", "s_rp_count"):
        return R(inner)
    if name == "s_rctps_rep":
        return repeat(inner, posts[:5], "rctps_rep", ctx, page, posts)
    if name == "s_rctps_popular_rep":
        return repeat(inner, posts[5:10], "rctps_rep", ctx, page, posts)
    if name == "s_rctrp_rep":
        buf = []
        for i, p in enumerate(posts[:5]):
            sub = dict(ctx)
            sub.update({"rctrp_rep_link": p["_link"] + "#comment",
                        "rctrp_rep_desc": "좋은 글 감사합니다. 저도 같은 문제를 겪었는데 도움이 됐습니다.",
                        "rctrp_rep_name": ["김개발", "박엔지니어", "이서버", "최데브", "정클라"][i],
                        "rctrp_rep_time": p["date"]})
            buf.append(render(inner, sub, page, posts))
        return "".join(buf)
    if name in ("s_random_tags", "s_tag_rep"):
        tags = ["k8s", "spring", "jvm", "python", "kafka", "mysql", "docker", "airflow",
                "langchain", "redis", "golang", "nginx"]
        buf = []
        for i, t in enumerate(tags):
            sub = dict(ctx)
            sub.update({"tag_link": "/tag/" + t, "tag_name": t, "tag_class": "cloud%d" % (i % 5 + 1)})
            buf.append(render(inner, sub, page, posts))
        return "".join(buf)
    if name == "s_tag":
        # 태그 클라우드는 /tag 에서만 렌더된다. 양쪽 분기를 같게 두면
        # 전 페이지에 태그 목록이 나와 스킨 결함처럼 보인다.
        # 목록이 나오는 /tag/이름(page="tag")과는 다른 페이지다 — PAGE_TYPES 주석 참조.
        return R(inner) if page == "tag_cloud" else ""

    # 페이징
    if name == "s_paging":
        return R(inner) if (is_list or page == "index") and page != "empty" else ""
    if name == "s_paging_rep":
        buf = []
        for n in range(1, 6):
            sub = dict(ctx)
            sub.update({"paging_rep_link": 'href="?page=%d"' % n, "paging_rep_link_num": str(n)})
            buf.append(render(inner, sub, page, posts))
        return "".join(buf)

    # 방명록
    if name.startswith("s_guest"):
        if page != "guestbook":
            return ""
        if name == "s_guest":
            return R(inner, {**ctx, "guestbook_group": REACT_BOX % "방명록"})
        if name == "s_guest_rep":
            buf = []
            for i, p in enumerate(posts[:4]):
                sub = dict(ctx)
                sub.update({"guest_rep_id": "g%d" % i, "guest_rep_class": "guest",
                            "guest_rep_name": ["방문객", "지나가던개발자", "구독자", "익명"][i],
                            "guest_rep_date": p["date"], "guest_rep_desc": "잘 보고 갑니다!",
                            "guest_rep_logo": "", "guest_rep_onclick_delete": "return false;",
                            "guest_rep_onclick_reply": "return false;"})
                buf.append(render(inner, sub, page, posts))
            return "".join(buf)
        return R(inner)

    # 공지 — 본문 공지와 사이드바 공지 모듈.
    # 예전에는 통째로 버렸다. 그 결과 <s_notice_rep> 블록이 **한 번도 렌더된 적이 없어**
    # 그 안의 결함(반복 영역인데 h1을 쓴 것, .notice-body에 CSS가 없는 것)을
    # 프리뷰로는 볼 수 없었다. 리뷰에서 눈으로 찾았다 — 그러라고 있는 도구가 아니다.
    #
    # ⚠ 재현하지 못하는 것: 티스토리가 [##_notice_rep_desc_##]를 어떤 래퍼로 감싸는지
    #    모른다. 여기서는 .contents_style을 **씌우지 않은** 형태로 낸다 — 최악의 경우를
    #    보여 주는 쪽이 안전하고, js/notice.js가 그 경우를 받는지도 같이 보인다.
    if name == "s_notice_rep":
        if page not in ("index", "page", "page_toc"):
            return ""
        buf = []
        for i, pst in enumerate(posts[:2]):
            sub = dict(ctx)
            sub.update({
                "notice_rep_link": "/notice/%d" % (i + 1),
                "notice_rep_title": ["블로그 카테고리를 개편했습니다",
                                     "댓글 정책 안내"][i],
                "notice_rep_date": pst["date"], "notice_rep_simple_date": pst["date"],
                "notice_rep_desc": ('<p>본문 문단이다. 인라인 색이 섞인 옛 글을 흉내낸다 — '
                                    '<span style="color: #000000;">검은 글자</span>와 '
                                    '<span style="background-color: #ffffff;">흰 배경</span>.</p>'
                                    '<p>두 번째 문단.</p>'),
            })
            buf.append(render(inner, sub, page, posts))
        return "".join(buf)

    if name in ("s_rct_notice", "s_rct_notice_rep"):
        if not (is_list or page == "index"):
            return ""
        if name == "s_rct_notice":
            return R(inner)
        buf = []
        for i in range(2):
            sub = dict(ctx)
            sub.update({"notice_rep_link": "/notice/%d" % (i + 1),
                        "notice_rep_title": ["블로그 카테고리를 개편했습니다",
                                             "댓글 정책 안내"][i]})
            buf.append(render(inner, sub, page, posts))
        return "".join(buf)

    # 표시하지 않는 것들
    if name in ("s_ad_div", "s_article_protected", "s_cover_group", "s_cover_rep", "s_cover",
                "s_cover_item", "s_cover_item_article_info", "s_cover_item_not_article_info",
                "s_cover_url", "s_page_rep"):
        return ""

    sys.stderr.write("  [경고] 처리 규칙이 없는 그룹 치환자: <%s> → 내용을 그대로 남긴다\n" % name)
    return R(inner)


def truthy(v):
    return str(v).lower() not in ("", "0", "false", "none")


VALUE_RE = re.compile(r"\[##_([a-zA-Z0-9_]+)_##\]")


def values(text, ctx):
    def sub(m):
        k = m.group(1)
        if k in ctx:
            return str(ctx[k])
        sys.stderr.write("  [경고] 값이 없는 치환자: [##_%s_##]\n" % k)
        return '<span style="outline:1px dashed red">[##_%s_##]</span>' % k
    return VALUE_RE.sub(sub, text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default=",".join(PAGE_TYPES), help="쉼표 구분 페이지 타입")
    ap.add_argument("--src", default=os.path.join(SRC, "skin.html"))
    args = ap.parse_args()

    if not os.path.exists(args.src):
        # 렌더할 대상이 없는 것은 실패가 아니다. 구현 전에도 npm run check가 통과해야
        # 문서·인프라 변경을 커밋할 수 있다.
        print("ℹ️  %s 가 없어 렌더할 대상이 없다. 아직 구현 전이면 정상이다." % args.src)
        sys.exit(0)

    posts, cats = load_fixtures()
    skin_vars = {}
    xml = os.path.join(SRC, "index.xml")
    if os.path.exists(xml):
        x = open(xml, encoding="utf-8").read()
        for mv in re.finditer(r"<variable>(.*?)</variable>", x, re.S):
            b = mv.group(1)
            n = re.search(r"<name>(.*?)</name>", b, re.S)
            d = re.search(r"<default>(.*?)</default>", b, re.S)
            if n:
                v = (d.group(1) if d else "").replace("<![CDATA[", "").replace("]]>", "").strip()
                skin_vars[n.group(1).strip()] = v

    skin = open(args.src, encoding="utf-8").read()
    scan_orphan_areas(skin)
    os.makedirs(OUT, exist_ok=True)
    made = []
    for page in [p.strip() for p in args.page.split(",") if p.strip()]:
        if page not in PAGE_TYPES:
            sys.stderr.write("알 수 없는 페이지 타입: %s\n" % page)
            continue
        sys.stderr.write("── %s (%s)\n" % (page, PAGE_TYPES[page]))
        ctx = globals_for(page, posts, cats, skin_vars)
        out = render(skin, ctx, page, posts)
        # 로컬 경로로 치환 — 스킨은 ./images/, style.css를 상대 경로로 참조한다
        # 렌더 결과는 _preview/pages/ 아래에 둔다.
        # _preview/index.html은 목차 페이지이므로, page 타입 'index'와 파일명이 충돌한다.
        # 티스토리 시트를 **실제 순서대로** 끼운다 — content.css는 우리 앞, hljs는 우리 뒤.
        # 감시 스크립트가 링크보다 먼저 와야 onload 콜백이 정의되어 있다.
        stack = "\n".join((
            TISTORY_CSS_GUARD.replace("__NEED__", "2"),
            '<link rel="stylesheet" href="%s" onload="__tistoryCssLoaded()">' % TISTORY_CONTENT_CSS,
            '<link rel="stylesheet" href="../../dist/style.css">',
            '<link rel="stylesheet" href="%s" onload="__tistoryCssLoaded()">' % TISTORY_HLJS_CSS,
        ))
        before = out
        out = out.replace('<link rel="stylesheet" href="./style.css">', stack, 1)
        if out == before:
            # 스킨의 링크 표기가 바뀌면 위 치환이 조용히 빗나간다. 그때는 프리뷰가
            # 다시 우리 CSS만 그리게 되므로, 조용히 넘어가지 않고 알린다.
            sys.stderr.write("  ⚠ style.css 링크를 찾지 못해 티스토리 시트를 끼우지 못했다 "
                             "— 프리뷰가 특이도 충돌을 재현하지 않는다\n")
            out = out.replace('href="./style.css"', 'href="../../dist/style.css"')
        out = out.replace('src="./images/', 'src="../../dist/images/')
        out = out.replace('url(./images/', 'url(../../dist/images/')
        os.makedirs(os.path.join(OUT, "pages"), exist_ok=True)
        path = os.path.join(OUT, "pages", page + ".html")
        open(path, "w", encoding="utf-8").write(out)
        made.append(path)

    idx = ["<title>프리뷰</title><style>body{font:15px/1.7 system-ui;padding:40px;max-width:640px;"
           "margin:0 auto}a{display:block;padding:10px 14px;border:1px solid #ebebeb;border-radius:6px;"
           "margin:6px 0;text-decoration:none;color:#171717}a:hover{border-color:#0070f3}"
           "code{background:#fafafa;padding:1px 5px;border-radius:4px}</style>",
           "<h1>로컬 프리뷰</h1><p>치환자를 <code>data/posts.json</code> 픽스처로 치환한 결과다. "
           "티스토리 서버 렌더링과 완전히 같지는 않다 — <code>SKILL.md</code>의 "
           "“렌더러가 재현하지 못하는 것” 참조.</p>"]
    for p in made:
        n = os.path.basename(p)[:-5]
        idx.append('<a href="pages/%s.html">%s <small>(%s)</small></a>' % (n, n, PAGE_TYPES[n]))
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write("\n".join(idx))

    print("\n%d개 페이지 생성 → _preview/" % len(made))
    print("열기: open _preview/index.html")


if __name__ == "__main__":
    main()
