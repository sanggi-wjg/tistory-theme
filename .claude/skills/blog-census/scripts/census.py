#!/usr/bin/env python3
"""티스토리 블로그 콘텐츠 전수 실측.

목록 페이지에서 전체 글을 수집하고(--posts), 필요하면 본문까지 받아
인라인 스타일 오염과 코드블록 실태를 집계한다(--bodies).

이 프로젝트의 설계 결정 대부분이 이 수치에서 나왔다. 잘못 집계하면
잘못된 CSS가 만들어진다 — DECISIONS.md §7의 정정 기록 참조.

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


def crawl_list(base):
    """목록 페이지를 끝까지 훑는다. RSS는 최신 50편만 주므로 쓰지 않는다."""
    posts, page = [], 1
    while True:
        h = fetch("%s/?page=%d" % (base, page))
        if h is None:
            break
        blocks = re.split(r'<div class="post">', h)[1:]
        if not blocks:
            break
        for b in blocks:
            b = b[:12000]
            def pick(pat):
                m = re.search(pat, b, re.S)
                return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""
            link = re.search(r'<a class="link" href="([^"]+)"', b)
            posts.append({
                "title": pick(r'<div class="tit">(.*?)</div>'),
                "date": pick(r'<time class="date">(.*?)</time>'),
                "category": pick(r'<div class="category">(.*?)</div>') or "(없음)",
                "hasThumbnail": 'class="thumb' in b,
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
    langs = collections.Counter()
    pre_total = lang_total = kor_blocks = 0
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
        ls = re.findall(r'data-ke-language="([^"]*)"', bd)
        lang_total += len(ls)
        langs.update(ls)
        for pre in pres:
            if re.search(r"[가-힣]", re.sub(r"<[^>]+>", "", pre)):
                kor_blocks += 1
        if (i + 1) % 25 == 0:
            sys.stderr.write("  본문 %d/%d\n" % (i + 1, len(targets)))
        time.sleep(0.15)
    return dict(parsed=parsed, colors=colors, bgs=bgs, fonts=fonts,
                langs=langs, pre_total=pre_total, lang_total=lang_total, kor_blocks=kor_blocks)


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
    print("\n  코드블록 %d개 · 언어 지정 %d개(%.0f%%) · 한국어 혼재 %d개(%.0f%%)"
          % (b["pre_total"], b["lang_total"],
             b["lang_total"] / b["pre_total"] * 100 if b["pre_total"] else 0,
             b["kor_blocks"], b["kor_blocks"] / b["pre_total"] * 100 if b["pre_total"] else 0))
    print("  언어 분포: %s" % dict(b["langs"].most_common(10)))

    json.dump({"crawledAt": time.strftime("%Y-%m-%d"), "parsedPosts": b["parsed"],
               "needsFix": [c for c, _ in sorted(dark, key=lambda x: -x[1])]
                           + [c for c, _ in sorted(light, key=lambda x: -x[1])]
                           + list(b["bgs"].keys()),
               "color": dict(b["colors"]), "backgroundColor": dict(b["bgs"]),
               "fontFamily": dict(b["fonts"]),
               "codeBlocks": {"total": b["pre_total"], "labeled": b["lang_total"],
                              "korean": b["kor_blocks"], "languages": dict(b["langs"])}},
              open(os.path.join(ROOT, "data", "inline-styles.json"), "w"),
              ensure_ascii=False, indent=1)
    print("\n→ data/inline-styles.json 갱신 (린트 INL001이 이 파일을 쓴다)")


if __name__ == "__main__":
    main()
