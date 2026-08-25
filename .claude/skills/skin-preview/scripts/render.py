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

ROOT = os.getcwd()
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(ROOT, "_preview")

PAGE_TYPES = {
    "index":     "tt-body-index",
    "page":      "tt-body-page",
    "category":  "tt-body-category",
    "search":    "tt-body-search",
    "tag":       "tt-body-tag",
    "archive":   "tt-body-archive",
    "guestbook": "tt-body-guestbook",
    "empty":     "tt-body-search",   # 결과 0건 시나리오
}

LIST_PAGES = {"category", "search", "tag", "archive", "empty"}

# 실제 글에서 관찰된 오염 패턴을 그대로 담은 본문 픽스처.
# 인라인 color/background-color/font-family 보정 규칙이 동작하는지 여기서 확인한다.
ARTICLE_BODY = """<div class="tt_article_useless_p_margin contents_style">
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
</div>"""


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


def build_category_html(cats, posts):
    """[##_category_##]가 출력하는 고정 마크업을 그대로 재현한다."""
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
    out = ['<ul class="tt_category"><li class=""><a href="/category" class="link_tit"> 분류 전체보기 '
           '<span class="c_cnt">(%d)</span> </a>' % len(posts), '<ul class="category_list">']
    for top, v in sorted(tree.items(), key=lambda kv: -kv[1]["n"]):
        out.append('<li class=""><a href="/category/%s" class="link_item"> %s '
                   '<span class="c_cnt">(%d)</span> </a>' % (html.escape(top), html.escape(top), v["n"]))
        if v["subs"]:
            out.append('<ul class="sub_category_list">')
            for s, n in sorted(v["subs"].items(), key=lambda kv: -kv[1]):
                out.append('<li class=""><a href="/category/%s/%s" class="link_sub_item"> %s '
                           '<span class="c_cnt">(%d)</span> </a></li>' % (
                               html.escape(top), html.escape(s), html.escape(s), n))
            out.append("</ul>")
        out.append("</li>")
    out.append("</ul></li></ul>")
    return "\n".join(out)


def globals_for(page, posts, cats, category_html, skin_vars):
    conform = {"category": "Kotlin & Java/Spring", "search": "OOMKilled",
               "tag": "hikaricp", "archive": "2026", "empty": "존재하지않는검색어"}.get(page, "")
    g = {
        "title": "상쾌한기분", "desc": "오늘도 상쾌한기분", "blogger": "상쾌한기분",
        "image": "https://placehold.co/200x200/eeeeee/999999?text=logo",
        "blog_image": '<img src="https://placehold.co/200x200/eeeeee/999999?text=logo" alt="">',
        "blog_link": "/", "rss_url": "/rss", "taglog_link": "/tag", "guestbook_link": "/guestbook",
        "page_title": "상쾌한기분", "body_id": PAGE_TYPES[page],
        "blog_menu": '<ul class="blog-menu"><li><a href="/">홈</a></li>'
                     '<li><a href="/tag">태그</a></li><li><a href="/guestbook">방명록</a></li></ul>',
        "category": category_html, "category_list": category_html,
        "count_total": "482,193", "count_today": "312", "count_yesterday": "487",
        "search_name": "search", "search_text": "", "search_onclick_submit": "return false;",
        "list_conform": conform, "list_count": "0" if page == "empty" else str(len(posts)),
        "list_description": "카테고리 설명이 들어가는 자리다.",
        "list_style": "list", "list_image": "https://placehold.co/1200x300/eeeeee/999999?text=category",
        "prev_page": 'href="?page=1"', "next_page": 'href="?page=3"',
        "no_more_prev": "", "no_more_next": "",
        "revenue_list_upper": '<div class="_ad">[광고 자리: 홈·목록 상단]</div>',
        "revenue_list_lower": '<div class="_ad">[광고 자리: 홈·목록 하단]</div>',
        "comment_group": '<div data-tistory-react-app="Comment">'
                         '<div class="tt-comment-cont">[댓글: 티스토리 React가 렌더링]</div></div>',
        "guestbook_group": '<div data-tistory-react-app="Comment">'
                           '<div class="tt-comment-cont">[방명록: 티스토리 React가 렌더링]</div></div>',
        "tag_label_rep": " ".join('<a href="/tag/%s">%s</a>' % (t, t)
                                  for t in ["k8s", "spring", "jvm", "hikaricp", "oom"]),
    }
    for k, v in skin_vars.items():
        g["var_" + k] = v
    return g


def item_scope(p, prefix):
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
        prefix + "_summary": p["_summary"], prefix + "_desc": ARTICLE_BODY,
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
        sub.update(item_scope(p, prefix))
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
    if name == "s_index_article_rep":
        return repeat(inner, posts[:12], "article_rep", ctx, page, posts) if page == "index" else ""
    if name == "s_permalink_article_rep":
        return R(inner, {**ctx, **item_scope(posts[0], "article_rep")}) if page == "page" else ""
    if name == "s_article_rep":
        if page == "page":
            return R(inner, {**ctx, **item_scope(posts[0], "article_rep")})
        if page == "index":
            return repeat(inner, posts[:12], "article_rep", ctx, page, posts)
        return ""
    if name == "s_list":
        return R(inner) if is_list else ""
    if name == "s_list_rep":
        return repeat(inner, posts[:20], "list_rep", ctx, page, posts) if (is_list and page != "empty") else ""
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
        if page != "page":
            return ""
        if name == "s_article_prev":
            return R(inner, {**ctx, **item_scope(posts[1], "article_prev")})
        if name == "s_article_next":
            return R(inner, {**ctx, **item_scope(posts[2], "article_next")})
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
        # 8개 페이지 전부에 태그 목록이 나와 스킨 결함처럼 보인다.
        return R(inner) if page == "tag" else ""

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

    # 표시하지 않는 것들
    if name in ("s_ad_div", "s_article_protected", "s_notice_rep", "s_rct_notice",
                "s_rct_notice_rep", "s_cover_group", "s_cover_rep", "s_cover",
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
    cat_html = build_category_html(cats, posts)
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
    os.makedirs(OUT, exist_ok=True)
    made = []
    for page in [p.strip() for p in args.page.split(",") if p.strip()]:
        if page not in PAGE_TYPES:
            sys.stderr.write("알 수 없는 페이지 타입: %s\n" % page)
            continue
        sys.stderr.write("── %s (%s)\n" % (page, PAGE_TYPES[page]))
        ctx = globals_for(page, posts, cats, cat_html, skin_vars)
        out = render(skin, ctx, page, posts)
        # 로컬 경로로 치환 — 스킨은 ./images/, style.css를 상대 경로로 참조한다
        # 렌더 결과는 _preview/pages/ 아래에 둔다.
        # _preview/index.html은 목차 페이지이므로, page 타입 'index'와 파일명이 충돌한다.
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
