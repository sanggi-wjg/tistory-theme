#!/usr/bin/env python3
"""V019(Namecard 번들 ↔ 프리뷰 픽스처)·V020(보호글 Namecard 위치)이 갈림을 실제로 잡는가 — `npm run test:namecard-live`

둘 다 배포 뒤에만 돈다(네트워크). 대조기 자체가 아무것도 못 잡으면 「같다」는 info만 계속 나온다 — 검사가
통과 신호를 위조하는 부류(docs/HARNESS.md 「핵심 위험」). 그래서 오프라인으로
① 2026-10-10 라이브 번들(@e0a0fbc)에서 자른 **Namecard 컴포넌트 실물**이 지금 프리뷰 픽스처와 같다고 판정되는지,
② 번들 쪽을 하나씩 비튼 변이가 **각각** 갈림(또는 「컴포넌트를 못 찾았다」)으로 잡히는지,
③ 픽스처 쪽을 비튼 변이(상태 하나를 안 그림, 클래스 오타)가 잡히는지,
④ `verify_namecard_bundle`·`verify_namecard_protected`를 `fetch`만 바꿔 **끝까지** 돌려 판정(info·경고·미검증)이
   맞는지 본다.

① 이 실패하면 둘 중 하나다 — 프리뷰 픽스처를 바꿨거나(그러면 라이브 번들을 다시 받아 여기를 갱신한다),
대조기가 망가졌다. 실물은 svg path의 `d`만 줄였다(대조기는 className 없는 원소를 보지 않는다).
"""
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
# importlib 대신 소스를 직접 컴파일한다 — `__pycache__`의 낡은 바이트코드가 판정하지 않게(verify.load_renderer 참조)
V = types.ModuleType("verify")
V.__file__ = os.path.join(HERE, "verify.py")
with open(V.__file__, encoding="utf-8") as f:
    exec(compile(f.read(), V.__file__, "exec"), V.__dict__)

# 2026-10-10 라이브 번들 static/pc/dist/index.js(userblog-e0a0fbc…)의 Namecard 컴포넌트 — path d만 줄였다
COMPONENT = (
    "function _8(){var u,l,d,c,f;const{data:e,isLoading:t}=w8(),{mutate:n,isPending:r,error:i}=S8(),"
    "{mutate:s,isPending:o,error:a}=$8();return ne.useEffect(()=>{var p,h;i?window.showTooltip(ES(\"follow\","
    "(p=i.response)==null?void 0:p.status)):a&&window.showTooltip(ES(\"unfollow\",(h=a.response)==null?void 0:h.status))},"
    "[i,a]),E.jsxs(\"div\",{className:\"tt_box_namecard\",children:[E.jsxs(\"div\",{className:\"tt_cont\","
    "children:[E.jsx(\"a\",{className:\"tt_tit_cont\",href:(u=e==null?void 0:e.blogUrl)!=null?u:\"#none\","
    "children:(l=e==null?void 0:e.title)!=null?l:\"\"}),(e==null?void 0:e.storyCreator)&&E.jsxs(\"a\","
    "{className:\"tt_link\",href:\"https://notice.tistory.com/2648\",children:[E.jsx(\"div\",{className:\"tt_wrap_svg\","
    "children:E.jsxs(\"svg\",{fill:\"none\",height:\"15\",viewBox:\"0 0 14 15\",width:\"14\",xmlns:\"http://www.w3.org/2000/svg\","
    "children:[E.jsx(\"path\",{clipRule:\"evenodd\",d:\"M0 0Z\",fill:\"#C5F220\",fillRule:\"evenodd\"}),E.jsx(\"path\","
    "{clipRule:\"evenodd\",d:\"M0 0Z\",fill:\"black\",fillRule:\"evenodd\"})]})}),E.jsxs(\"strong\",{className:\"tt_tit_g\","
    "children:[e.storyCreator.categoryLabel,\" 분야 크리에이터\"]}),E.jsx(\"span\",{className:\"tt_img_area_reply tt_ico_arrow2\"})]}),"
    "E.jsx(\"a\",{className:\"tt_desc\",href:(d=e==null?void 0:e.blogUrl)!=null?d:\"#none\",children:(c=e==null?void 0:e.description)!=null?c:\"\"}),"
    "(e==null?void 0:e.isMember)===!1&&(e.isFollower?E.jsxs(\"button\",{className:\"tt_btn_subscribe type2\","
    "\"data-tiara-action-name\":\"프로필영역 구독 버튼_클릭\",\"data-tiara-copy\":\"구독중\",disabled:o||t,type:\"button\","
    "onClick:()=>{s()},children:[E.jsx(\"span\",{className:\"tt_txt_g\",children:\"구독중\"}),E.jsx(\"span\","
    "{className:\"tt_img_area_reply tt_ico_check\"})]}):E.jsxs(\"button\",{className:\"tt_btn_subscribe\","
    "\"data-tiara-action-name\":\"프로필영역 구독 버튼_클릭\",\"data-tiara-copy\":\"구독하기\",disabled:r||t,type:\"button\","
    "onClick:()=>{if(!Bs()){ca();return}n()},children:[E.jsx(\"span\",{className:\"tt_txt_g\",children:\"구독하기\"}),"
    "E.jsx(\"span\",{className:\"tt_img_area_reply tt_ico_cross\"})]}))]}),E.jsx(\"a\",{className:\"tt_wrap_thumb\","
    "href:(f=e==null?void 0:e.blogUrl)!=null?f:\"#none\",children:E.jsx(\"span\",{className:\"tt_thumb_g\","
    "style:{backgroundImage:e!=null&&e.thumbnailUrl?\"url(\".concat(e.thumbnailUrl,\")\"):void 0}})})]})}"
)
# 앞의 미끼는 `Comment:`가 없는 다른 객체의 `Namecard:` 키다 — 앱 표만 믿는지 본다
BUNDLE = ('var Zq={Namecard:"프로필"};function ES(e,t){return""}' + COMPONENT
          + 'const E8={Comment:g8,Namecard:_8,Menubar:uN,Reaction:wN,NaverAd:dN};')

RENDER = V.load_renderer()
if RENDER is None:
    sys.exit("render.py를 불러오지 못했다")


def fixtures(box=None):
    """기본은 V019가 쓰는 것과 같은 render.namecard_states() — 상태 목록을 두 곳에 베끼지 않는다."""
    if box is None:
        return RENDER.namecard_states()
    return [box(follower=f, creator=c) for f in (False, True) for c in (False, True)]


# (이름, 번들을 비트는 함수, 기대: "drift" 갈림 · "missing" 컴포넌트를 못 찾음)
BUNDLE_MUTANTS = [
    ("배지 글자 클래스가 바뀌었다(tt_tit_g → tt_tit_badge)", lambda s: s.replace('"tt_tit_g"', '"tt_tit_badge"'), "drift"),
    ("배지 글자 태그가 바뀌었다(strong → span)",
     lambda s: s.replace('E.jsxs("strong",{className:"tt_tit_g"', 'E.jsxs("span",{className:"tt_tit_g"'), "drift"),
    ("구독 중 상태 클래스가 바뀌었다(type2 → is-following)",
     lambda s: s.replace('"tt_btn_subscribe type2"', '"tt_btn_subscribe is-following"'), "drift"),
    ("원소가 하나 늘었다(구독자 수)",
     lambda s: s.replace('E.jsx("a",{className:"tt_desc"',
                         'E.jsx("span",{className:"tt_count",children:"1"}),E.jsx("a",{className:"tt_desc"'), "drift"),
    ("원소가 하나 사라졌다(설명 tt_desc)",
     lambda s: s.replace('E.jsx("a",{className:"tt_desc",', 'E.jsx("a",{'), "drift"),
    ("className이 조건식이 됐다",
     lambda s: s.replace('className:"tt_btn_subscribe type2"', 'className:"tt_btn_subscribe ".concat(x?"type2":"")'),
     "drift"),
    ("버튼이 하위 컴포넌트로 쪼개졌다",
     lambda s: s.replace('E.jsxs("button",{className:"tt_btn_subscribe",', 'E.jsx(Xb,{a:1}),E.jsxs("i",{'), "drift"),
    ("앱 표에서 Namecard 키가 바뀌었다(ProfileCard)",
     lambda s: s.replace("Namecard:_8,Menubar", "ProfileCard:_8,Menubar"), "missing"),
    ("컴포넌트가 화살표 함수가 됐다(대조기가 따라가야 한다)",
     lambda s: s.replace("function _8(){", "const _8=()=>{"), "same"),
    ("esbuild식 호출 (0,E.jsx)(…)로 바뀌었다(대조기가 따라가야 한다)",
     lambda s: s.replace("E.jsxs(", "(0,E.jsxs)(").replace("E.jsx(", "(0,E.jsx)("), "same"),
    ("props가 변수로 넘어간다(클래스를 알 수 없다)",
     lambda s: s.replace('E.jsx("a",{className:"tt_desc",', 'E.jsx("a",pp),E.jsx("i",{'), "drift"),
    ("같은 이름의 함수가 다른 스코프에 또 있다(고를 수 없다)",
     lambda s: 'function q(){function _8(){return E.jsx("b",{className:"x"})}}' + s, "missing"),
    # ↓ 클래스·태그는 그대로이고 자리(부모)만 옮겨진 경우 — 집합 대조만으로는 「같다」였다(#134)
    ("설명(tt_desc)이 tt_cont 밖, 카드 바로 아래로 옮겨졌다", lambda s: move_desc(s), "drift"),
    ("구독 버튼이 배지 줄(tt_link) 안으로 들어갔다",
     lambda s: s.replace('E.jsx("span",{className:"tt_img_area_reply tt_ico_arrow2"})]})',
                         'E.jsx("span",{className:"tt_img_area_reply tt_ico_arrow2"}),'
                         'E.jsxs("button",{className:"tt_btn_subscribe",children:[]})]})'), "drift"),
]


def move_desc(s):
    """설명 a.tt_desc를 tt_cont의 children에서 빼 tt_wrap_thumb 앞(tt_box_namecard 바로 아래)에 둔다."""
    desc = ('E.jsx("a",{className:"tt_desc",href:(d=e==null?void 0:e.blogUrl)!=null?d:"#none",'
            'children:(c=e==null?void 0:e.description)!=null?c:""}),')
    assert s.count(desc) == 1, "COMPONENT에서 tt_desc 호출을 못 찾았다 — 실물을 갱신했으면 여기도 맞춘다"
    s = s.replace(desc, "")
    return s.replace('E.jsx("a",{className:"tt_wrap_thumb"', desc + 'E.jsx("a",{className:"tt_wrap_thumb"')

# (이름, 픽스처 함수) — 프리뷰 쪽이 실물과 갈리는 경우
def _no_creator(follower=False, creator=False):
    return RENDER.namecard_box(follower=follower, creator=False)


def _typo(follower=False, creator=False):
    return RENDER.namecard_box(follower=follower, creator=creator).replace("tt_desc", "tt_dsc")


def _thumb_inside(follower=False, creator=False):
    """썸네일 a.tt_wrap_thumb를 tt_cont 안으로 — 클래스는 그대로, 자리만 다르다."""
    h = RENDER.namecard_box(follower=follower, creator=creator)
    i = h.index('<a class="tt_wrap_thumb"')
    j = h.index("</a>", i) + len("</a>")
    thumb, h = h[i:j], h[:i] + h[j:]
    return h.replace('<div class="tt_cont">', '<div class="tt_cont">' + thumb, 1)


FIXTURE_MUTANTS = [
    ("픽스처가 크리에이터 배지 줄을 한 번도 안 그린다", _no_creator),
    ("픽스처 클래스 오타(tt_desc → tt_dsc)", _typo),
    ("픽스처의 썸네일이 tt_cont 안에 있다(자리만 다르다)", _thumb_inside),
]


def run_v019(home, responses):
    """verify_namecard_bundle을 그대로 돌린다(fetch만 바꿔치기). (경고, 미검증, info) 코드별 개수."""
    V.WARNINGS.clear(); V.UNVERIFIED.clear(); V.INFO.clear()
    V.fetch = lambda url, *a, **k: responses.get(url, (404, "", url))
    V.verify_namecard_bundle("https://blog.example", home)
    return ([w for w in V.WARNINGS if w["code"] == "V019"], [u for u in V.UNVERIFIED if u["code"] == "V019"],
            [i for i in V.INFO if i.startswith("V019")])


def run_v020(path, doc, status=200):
    V.WARNINGS.clear(); V.UNVERIFIED.clear(); V.INFO.clear()
    V.fetch = lambda url, *a, **k: (status, doc, url)
    V.verify_namecard_protected("https://blog.example", path)
    return ([w for w in V.WARNINGS if w["code"] == "V020"], [u for u in V.UNVERIFIED if u["code"] == "V020"],
            [i for i in V.INFO if i.startswith("V020")])


PINNED = V.preview_sheet_url("TISTORY_NAMECARD_BUNDLE")
OTHER = "https://edge.example/userblog-ffff/static/pc/dist/index.js"


def home_with(src):
    return ('<html><head><script type="module" src="%s" defer=""></script>'
            '<script nomodule src="%s"></script></head><body></body></html>'
            % (src, src.replace("index.js", "index-legacy.js")))


NC = '<div data-tistory-react-app="Namecard"></div>'
PROTECTED = ('<html><body><main class="site-main"><section class="protected"><h1>보호글</h1>%s</section>%s'
             '</main></body></html>')


def main():
    fails = []

    def check(ok, name):
        print(("  ✓ " if ok else "  ✗ ") + name)
        if not ok:
            fails.append(name)

    print("① 라이브 실물 ↔ 지금 픽스처")
    problems, n = V.namecard_drift(BUNDLE, fixtures())
    check(problems == [] and n >= 15, "같다고 판정한다 (서명 %d종, 갈림 %s)" % (n, problems))
    check(V.bundle_component(BUNDLE).startswith("function _8("), "미끼 `{Namecard:…}`가 아니라 앱 표를 따라간다")
    edges = V.bundle_edges(V.bundle_component(BUNDLE))
    fx_edges = set().union(*(V.fixture_edges(h) for h in fixtures()))
    # 짝이 비어 있으면 「자리」 대조는 늘 같다고 나온다 — 개수와 대표 짝을 못박는다
    check(len(edges) == 16 and edges == fx_edges and "div.tt_cont > a.tt_desc" in edges
          and "a.tt_link > strong.tt_tit_g" in edges, "부모-자식 짝 16개가 픽스처와 같다 (%d / %d)" % (len(edges), len(fx_edges)))
    p, _ = V.namecard_drift(BUNDLE.replace('"tt_tit_g"', '"tt_tit_badge"'), fixtures())
    check(p is not None and not any("자리" in x for x in p),
          "이름이 바뀐 원소는 「자리가 다르다」로 두 번 나오지 않는다")

    print("② 번들 변이")
    for name, mut, want in BUNDLE_MUTANTS:
        p, _ = V.namecard_drift(mut(BUNDLE), fixtures())
        got = "missing" if p is None else ("drift" if p else "same")
        check(got == want, "%s → %s (기대 %s)%s" % (name, got, want, " " + "; ".join(p) if p else ""))

    print("③ 픽스처 변이")
    for name, box in FIXTURE_MUTANTS:
        p, _ = V.namecard_drift(BUNDLE, fixtures(box))
        check(bool(p), "%s → %s" % (name, "; ".join(p) if p else "갈림 없음"))

    print("④ verify_namecard_bundle 끝까지")
    w, u, i = run_v019(home_with(PINNED), {PINNED: (200, BUNDLE, PINNED)})
    check(not w and not u and len(i) == 1 and "같은 번들" in i[0], "고정 번들과 같은 URL·같은 마크업 → info 하나")
    w, u, i = run_v019(home_with(OTHER), {OTHER: (200, BUNDLE, OTHER)})
    check(not w and not u and len(i) == 1 and "갱신" in i[0], "해시만 바뀌고 마크업이 같다 → 상수 갱신 info")
    bad = BUNDLE.replace('"tt_tit_g"', '"tt_tit_badge"')
    w, u, i = run_v019(home_with(OTHER), {OTHER: (200, bad, OTHER)})
    check(len(w) == 1 and not i, "마크업이 바뀌었다 → 경고, 「같다」 info 없음")
    w, u, i = run_v019(home_with(OTHER), {OTHER: (None, "", OTHER)})
    check(not w and len(u) == 1 and not i, "번들을 못 받았다 → 미검증")
    w, u, i = run_v019("<html><head></head></html>", {})
    check(not w and len(u) == 1 and not i, "홈에 번들 링크가 없다 → 미검증")
    w, u, i = run_v019(home_with(OTHER.replace("index.js", "index-legacy.js")), {})
    check(len(u) == 1 and not i, "index-legacy.js만 있으면 번들로 읽지 않는다 → 미검증")
    w, u, i = run_v019(home_with(OTHER), {OTHER: (200, BUNDLE.replace("Namecard:_8", "Card:_8"), OTHER)})
    check(not w and len(u) == 1 and not i, "컴포넌트를 못 찾았다 → 미검증(통과로 읽히지 않는다)")

    print("⑤ verify_namecard_protected 끝까지")
    w, u, i = run_v020(None, "")
    check(len(u) == 1 and not i, "경로가 없다 → 미검증")
    w, u, i = run_v020("/300", PROTECTED % ("", ""))
    check(not w and not u and len(i) == 1, "보호글에 카드가 없다 → info")
    w, u, i = run_v020("/300", PROTECTED % ("", NC))
    check(len(w) == 1 and ".site-main" in w[0]["message"], "카드가 .entry-main 밖(main 바로 아래) → 경고, 조상 경로를 적는다")
    w, u, i = run_v020("/300", PROTECTED % ('<div class="entry-main"><p>본문<br></p>%s</div>' % NC, ""))
    check(not w and not u and len(i) == 1, "카드가 .entry-main 안 → info")
    w, u, i = run_v020("/300", '<html><body><div class="entry-main">%s</div></body></html>' % NC)
    check(len(u) == 1 and not w and not i, "보호글 영역이 없다(보호가 풀렸다) → 미검증")
    w, u, i = run_v020("/300", "", status=404)
    check(len(u) == 1 and not i, "보호글을 못 받았다 → 미검증")
    w, u, i = run_v020("/300", PROTECTED % ('<div class="entry-main"></div>', NC))
    check(len(w) == 1, "앞에 닫힌 .entry-main이 있어도 카드가 그 밖이면 경고")
    w, u, i = run_v020("/300", PROTECTED.replace('class="protected"', 'class="post-protected-note"') % ("", NC))
    check(len(u) == 1 and not w and not i, "section class가 protected 토큰이 아니다(post-protected-note) → 미검증")

    def boom(url, *a, **k):
        raise ValueError("boom")
    V.fetch = boom
    V.UNVERIFIED.clear()
    V.verify_namecard_protected("https://blog.example", "/300")
    check(len([x for x in V.UNVERIFIED if x["code"] == "V020"]) == 1, "예외가 나도 리포트를 잃지 않는다 → 미검증")
    check(V.protected_url("https://blog.example", "/entry/보호 글")
          == "https://blog.example/entry/%EB%B3%B4%ED%98%B8%20%EA%B8%80", "한글 경로를 퍼센트 인코딩한다")
    check(V.protected_url("https://blog.example", "https://blog.example/300") == "https://blog.example/300",
          "절대 URL은 그대로 쓴다")
    check(V.protected_url("https://blog.example", "300") == "https://blog.example/300", "앞 / 없는 경로")

    if fails:
        print("\n✗ %d개 실패" % len(fails))
        sys.exit(1)
    print("\n✓ V019·V020 대조기가 갈림을 잡는다")


if __name__ == "__main__":
    main()
