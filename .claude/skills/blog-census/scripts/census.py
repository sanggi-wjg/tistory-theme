#!/usr/bin/env python3
"""티스토리 블로그 콘텐츠 전수 실측.

목록 페이지에서 전체 글을 수집하고(--posts), 필요하면 본문까지 받아
인라인 스타일 오염과 코드블록 실태를 집계한다(--bodies).

이 프로젝트의 설계 결정 대부분이 이 수치에서 나왔다. 잘못 집계하면
잘못된 CSS가 만들어진다 — DECISIONS.md §5의 정정 기록 참조.

사용:
  python3 .claude/skills/blog-census/scripts/census.py --posts
  python3 .claude/skills/blog-census/scripts/census.py --posts --bodies
"""
import argparse
import collections
import html
import json
import os
import re
import sys
import time
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
GENERIC_OG = "openGraph%2Fopengraph"   # 대표이미지가 없을 때 티스토리가 쓰는 기본 이미지
ROOT = os.getcwd()


def fetch(url, retries=2):
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if i == retries:
                sys.stderr.write("  [실패] %s — %s\n" % (url, e))
                return None
            time.sleep(1.5 * (i + 1))


# 목록 항목 마크업 — 두 스킨을 안다.
#   our  : 2026-08-26 배포한 우리 스킨. `article.post` + `.post-title`·`.post-date`·`.post-cat`·`.post-link`
#          (계약은 docs/hooks.md §3). 썸네일은 **`img.thumb-img`가 있을 때만** 실물이다 — `.thumb` 상자는
#          기본 이미지일 때도 있으므로 `class="thumb`로 세면 100%가 나온다.
#   old  : 2026-08-25까지의 구 스킨. `div.post` + `.tit`·`.date`·`.category`·`a.link`
# 둘 다 0건이면 마크업이 또 바뀐 것이다 — 임의로 고치지 말고 새 구조를 보고한다.
LIST_SHAPES = {
    "our": dict(split=r'<article class="post[" ]', title=r'<strong class="post-title">(.*?)</strong>',
                date=r'<time class="post-date">(.*?)</time>', cat=r'<span class="post-cat">(.*?)</span>',
                link=r'<a class="post-link" href="([^"]+)"', thumb='class="thumb-img"'),
    "old": dict(split=r'<div class="post">', title=r'<div class="tit">(.*?)</div>',
                date=r'<time class="date">(.*?)</time>', cat=r'<div class="category">(.*?)</div>',
                link=r'<a class="link" href="([^"]+)"', thumb='class="thumb'),
}


def crawl_list(base):
    """목록 페이지를 끝까지 훑는다. RSS는 최신 50편만 주므로 쓰지 않는다."""
    posts, page, shape = [], 1, None
    while True:
        h = fetch("%s/?page=%d" % (base, page))
        if h is None:
            break
        if shape is None:
            for name, sh in LIST_SHAPES.items():
                if re.search(sh["split"], h):
                    shape = sh
                    sys.stderr.write("  목록 마크업: %s 스킨\n" % name)
                    break
            if shape is None:
                break
        blocks = re.split(shape["split"], h)[1:]
        if not blocks:
            break
        for b in blocks:
            b = b[:12000]
            def pick(pat):
                m = re.search(pat, b, re.S)
                return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""
            link = re.search(shape["link"], b)
            posts.append({
                "title": pick(shape["title"]),
                "date": pick(shape["date"]),
                "category": pick(shape["cat"]) or "(없음)",
                "hasThumbnail": shape["thumb"] in b,
                "url": html.unescape(link.group(1)) if link else "",
            })
        sys.stderr.write("  page %d — 누적 %d편\n" % (page, len(posts)))
        page += 1
        if page > 200:
            break
    return posts


def crawl_bodies(base, posts, limit=None):
    """본문을 받아 인라인 스타일과 코드블록을 집계한다."""
    colors, bgs, fonts = collections.Counter(), collections.Counter(), collections.Counter()
    # 코드블록 라벨은 **세 신호를 따로** 센다 — 만든 주체가 다르고 신뢰도가 다르다(결정 43).
    #   data-ke-language  : 에디터가 붙인다. 믿지 않는다(결정 18)
    #   <pre class>       : 에디터 자동 감지. 믿지 않는다(이 블로그에 없는 언어가 46개 섞여 있다)
    #   <code class="language-*"> : 글쓴이가 펜스로 쓴 것. 이것만 믿는다
    # 2026-08-26까지 첫째만 세어 「라벨 39%」가 나왔는데 셋째·둘째가 통째로 빠져 있었다
    # (TODO census-pre-class). 합치지 않는다 — 합치면 다시 «라벨 있음» 한 숫자가 된다.
    ke_langs, pre_classes, author_langs = collections.Counter(), collections.Counter(), collections.Counter()
    pre_total = ke_total = pre_class_total = author_total = kor_blocks = 0
    blocks = []   # 블록별 원문 — 감지 커버리지(scripts/probe-code-coverage.mjs)가 읽는다
    parsed = 0
    targets = posts if limit is None else posts[:limit]
    for i, p in enumerate(targets):
        if not p["url"]:
            continue
        h = fetch(base + p["url"] if p["url"].startswith("/") else p["url"])
        if h is None:
            continue
        # 래퍼는 'tt_article_useless_p_margin contents_style' — 정확일치로 찾으면 오래된 글이 누락된다
        m = re.search(r'<div class="[^"]*contents_style[^"]*">', h)
        if not m:
            sys.stderr.write("  [본문 미발견] %s\n" % p["title"][:40])
            continue
        parsed += 1
        rest = h[m.end():]
        j = rest.find("container_postbtn")
        bd = rest[:j if j > 0 else 200000]
        code_stripped = re.sub(r"<code>.*?</code>", "", bd, flags=re.S)   # 코드 내용 오탐 제거
        colors.update(x.strip().lower() for x in
                      re.findall(r'style="[^"]*?(?<!-)color:\s*([^;"]+)', code_stripped))
        bgs.update(x.strip().lower() for x in
                   re.findall(r'background-color:\s*([^;"]+)', code_stripped))
        fonts.update(x.strip().lower()[:40] for x in
                     re.findall(r'font-family:\s*([^;"]+)', code_stripped))
        pres = re.findall(r"<pre.*?</pre>", bd, re.S)
        pre_total += len(pres)
        for pre in pres:
            open_tag = re.match(r"<pre[^>]*>", pre).group(0)
            ke = re.search(r'data-ke-language="([^"]*)"', open_tag)
            pc = re.search(r'\sclass="([^"]*)"', open_tag)
            code_open = re.search(r"<code[^>]*>", pre)
            cc = re.search(r'\sclass="([^"]*)"', code_open.group(0)) if code_open else None
            author = re.search(r"\blanguage-([A-Za-z0-9#+._-]+)", cc.group(1)) if cc else None
            if ke:
                ke_total += 1
                ke_langs[ke.group(1)] += 1
            if pc and pc.group(1).strip():
                pre_class_total += 1
                pre_classes[pc.group(1).strip()] += 1
            if author:
                author_total += 1
                author_langs[author.group(1).lower()] += 1
            # textContent 근사 — <br>은 줄바꿈, 나머지 태그는 제거, 엔티티 복원
            text = html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"<br\s*/?>", "\n", pre)))
            text = text.rstrip()
            if re.search(r"[가-힣]", text):
                kor_blocks += 1
            blocks.append({"post": p["url"], "keLanguage": ke.group(1) if ke else None,
                           "preClass": pc.group(1).strip() if pc else None,
                           "codeClass": cc.group(1) if cc else None, "text": text})
        if (i + 1) % 25 == 0:
            sys.stderr.write("  본문 %d/%d\n" % (i + 1, len(targets)))
        time.sleep(0.15)
    return dict(parsed=parsed, colors=colors, bgs=bgs, fonts=fonts,
                pre_total=pre_total, kor_blocks=kor_blocks, blocks=blocks,
                ke_total=ke_total, ke_langs=ke_langs,
                pre_class_total=pre_class_total, pre_classes=pre_classes,
                author_total=author_total, author_langs=author_langs)


def luminance(v):
    m = re.match(r"#([0-9a-f]{3,8})$", v.strip())
    if not m:
        return None
    s = m.group(1)
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) < 6:
        return None
    r, g, b = (int(s[i:i + 2], 16) for i in (0, 2, 4))
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://sanggi-jayg.tistory.com")
    ap.add_argument("--posts", action="store_true", help="목록 전수 수집")
    ap.add_argument("--bodies", action="store_true", help="본문까지 수집 (느리다)")
    ap.add_argument("--limit", type=int, default=None, help="본문 수집 상한")
    args = ap.parse_args()
    if not (args.posts or args.bodies):
        args.posts = True

    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    prev = {}
    pp = os.path.join(ROOT, "data", "posts.json")
    if os.path.exists(pp):
        prev = json.load(open(pp, encoding="utf-8"))

    sys.stderr.write("목록 수집 중…\n")
    posts = crawl_list(args.base)
    if not posts:
        sys.exit("목록을 수집하지 못했다. 스킨이 바뀌어 마크업이 달라졌을 수 있다 — "
                 "임의로 고치지 말고 새 구조를 보고할 것.")

    n = len(posts)
    th = sum(1 for p in posts if p["hasThumbnail"])
    print("\n■ 전수 %d편 (이전 %s편)" % (n, prev.get("total", "—")))
    print("  대표이미지 보유 %d/%d (%.1f%%)" % (th, n, th / n * 100))
    for k in (20, 40):
        s = posts[:k]
        print("  최신 %2d편 %d/%d (%.0f%%)" % (k, sum(1 for p in s if p["hasThumbnail"]), len(s),
                                            sum(1 for p in s if p["hasThumbnail"]) / len(s) * 100))

    year = collections.defaultdict(lambda: [0, 0])
    for p in posts:
        y = (p["date"] or "?")[:4]
        year[y][0] += 1
        year[y][1] += 1 if p["hasThumbnail"] else 0
    print("\n  연도별 보유율")
    for y in sorted(year, reverse=True):
        t, w = year[y]
        print("    %s  %3d/%-3d %5.1f%%" % (y, w, t, w / t * 100))

    cat = collections.defaultdict(lambda: {"total": 0, "withThumbnail": 0})
    for p in posts:
        for key in (p["category"], p["category"].split("/")[0] + "  (상위)"):
            cat[key]["total"] += 1
            cat[key]["withThumbnail"] += 1 if p["hasThumbnail"] else 0

    tl = sorted(len(p["title"]) for p in posts)
    print("\n  제목 길이  전체 중앙값 %d자 / 최신 20편 중앙값 %d자"
          % (tl[n // 2], sorted(len(p["title"]) for p in posts[:20])[10]))

    json.dump({"blog": args.base.split("//")[-1], "crawledAt": time.strftime("%Y-%m-%d"),
               "total": n, "posts": posts},
              open(pp, "w"), ensure_ascii=False, indent=1)
    json.dump({"note": "'(상위)' 접미사는 하위 카테고리를 합산한 값",
               "categories": dict(sorted(cat.items(), key=lambda kv: -kv[1]["total"]))},
              open(os.path.join(ROOT, "data", "categories.json"), "w"), ensure_ascii=False, indent=1)
    print("\n→ data/posts.json · data/categories.json 갱신")

    if not args.bodies:
        return

    sys.stderr.write("\n본문 수집 중… (시간이 걸린다)\n")
    b = crawl_bodies(args.base, posts, args.limit)
    print("\n■ 본문 %d/%d편 파싱" % (b["parsed"], len(posts) if args.limit is None else args.limit))
    if b["parsed"] < (args.limit or len(posts)):
        print("  ⚠️ 파싱 실패분이 있다. 래퍼 선택자를 확인할 것 — 0으로 착각하면 안 된다")

    dark, light = [], []
    for c, cnt in b["colors"].items():
        L = luminance(c)
        if L is None:
            continue
        (dark if L < 0.5 else light).append((c, cnt))
    print("\n  인라인 color %d종 %d곳" % (len(b["colors"]), sum(b["colors"].values())))
    print("    다크에서 죽는 색 %d종: %s" % (len(dark), ", ".join(c for c, _ in sorted(dark, key=lambda x: -x[1]))))
    print("    라이트에서 죽는 색 %d종: %s" % (len(light), ", ".join(c for c, _ in sorted(light, key=lambda x: -x[1]))))
    print("  background-color %d종 %d곳: %s" % (len(b["bgs"]), sum(b["bgs"].values()),
                                              ", ".join(c for c, _ in b["bgs"].most_common(12))))
    print("  font-family %d종" % len(b["fonts"]))
    def pct(n):
        return n / b["pre_total"] * 100 if b["pre_total"] else 0
    print("\n  코드블록 %d개 · 한국어 혼재 %d개(%.0f%%)" % (b["pre_total"], b["kor_blocks"], pct(b["kor_blocks"])))
    print("  라벨 — 세 신호를 따로 센다(합치지 않는다):")
    print("    data-ke-language (에디터)      %d개(%.0f%%)  %s" % (b["ke_total"], pct(b["ke_total"]), dict(b["ke_langs"].most_common(8))))
    print("    <pre class>      (에디터 감지) %d개(%.0f%%)  %s" % (b["pre_class_total"], pct(b["pre_class_total"]), dict(b["pre_classes"].most_common(8))))
    print("    <code class=language-*> (글쓴이) %d개(%.0f%%)  %s" % (b["author_total"], pct(b["author_total"]), dict(b["author_langs"].most_common(8))))
    os.makedirs(os.path.join(ROOT, "_workspace"), exist_ok=True)
    json.dump({"crawledAt": time.strftime("%Y-%m-%d"), "blocks": b["blocks"]},
              open(os.path.join(ROOT, "_workspace", "code-blocks.json"), "w"), ensure_ascii=False, indent=1)
    print("  → _workspace/code-blocks.json (블록 %d개 원문 — node scripts/probe-code-coverage.mjs 가 읽는다)" % len(b["blocks"]))

    json.dump({"crawledAt": time.strftime("%Y-%m-%d"), "parsedPosts": b["parsed"],
               "needsFix": [c for c, _ in sorted(dark, key=lambda x: -x[1])]
                           + [c for c, _ in sorted(light, key=lambda x: -x[1])]
                           + list(b["bgs"].keys()),
               "color": dict(b["colors"]), "backgroundColor": dict(b["bgs"]),
               "fontFamily": dict(b["fonts"]),
               "codeBlocks": {"total": b["pre_total"], "korean": b["kor_blocks"],
                              "keLanguage": {"count": b["ke_total"], "values": dict(b["ke_langs"])},
                              "preClass": {"count": b["pre_class_total"], "values": dict(b["pre_classes"])},
                              "authorLanguage": {"count": b["author_total"], "values": dict(b["author_langs"])}}},
              open(os.path.join(ROOT, "data", "inline-styles.json"), "w"),
              ensure_ascii=False, indent=1)
    print("\n→ data/inline-styles.json 갱신 (린트 INL001이 이 파일을 쓴다)")


if __name__ == "__main__":
    main()
