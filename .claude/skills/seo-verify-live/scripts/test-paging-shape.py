"""V018(페이징 픽스처 ↔ 라이브) 대조기가 갈림을 실제로 잡는가 — `npm run test:paging`

V018은 배포 뒤에만 돈다(네트워크). 그런데 대조기 자체가 아무것도 못 잡으면 「같은 모양이다」라는
info만 계속 나온다 — 검사가 통과 신호를 위조하는 부류(docs/HARNESS.md 「핵심 위험」). 그래서 오프라인으로
① 2026-10-09에 받은 **라이브 실물**(1·9·22페이지)이 지금 프리뷰와 같다고 판정되는지,
② 결정 53의 세 조건과 번호 규칙을 하나씩 비튼 라이브가 **각각** 갈림으로 잡히는지,
③ `verify_paging_fixture`를 `fetch`만 바꿔 **끝까지** 돌려 짝짓기·총수·못 받은 페이지 처리가 맞는지 본다.
   ③은 코드 리뷰가 짚은 것들이다 — 못 받은 9페이지를 「1·9·22 같다」에 넣었고, `\bhref`가 `data-href`에
   맞았고, 홈 번호가 깨지면 총수 0으로 미검증에 숨었다.

① 이 실패하면 둘 중 하나다 — 프리뷰 픽스처를 바꿨거나(그러면 라이브를 다시 받아 여기를 갱신한다),
대조기가 망가졌다. 라이브 실물은 svg만 뺐다(대조기는 svg를 보지 않는다).
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


def nav(prev, nums, nxt):
    return '<nav class="paging" aria-label="페이지 이동">%s<span class="paging-nums">%s</span>%s</nav>' % (prev, nums, nxt)


def num(n, cur):
    return '<a class="paging-num" href="/?page=%d"><span class="%s">%d</span></a>' % (n, "selected" if n == cur else "", n)


ELL = '<a class="paging-num" ><span class="">···</span></a>'
PREV_OFF = '<a class="paging-prev no-more-prev" > <span class="paging-label">이전</span> </a>'
NEXT_OFF = '<a class="paging-next no-more-next" > <span class="paging-label">다음</span> </a>'


def prev_on(n):
    return '<a class="paging-prev " href="/?page=%d"> <span class="paging-label">이전</span> </a>' % n


def next_on(n):
    return '<a class="paging-next " href="/?page=%d"> <span class="paging-label">다음</span> </a>' % n


# 2026-10-09 라이브(sanggi-jayg.tistory.com /, /?page=9, /?page=22) — 공백만 줄였다
LIVE = {
    1: nav(PREV_OFF, "".join(num(n, 1) for n in (1, 2, 3, 4)) + ELL + num(22, 1), next_on(2)),
    9: nav(prev_on(8), num(1, 9) + ELL + "".join(num(n, 9) for n in range(6, 13)) + ELL + num(22, 9), next_on(10)),
    22: nav(prev_on(21), num(1, 22) + ELL + "".join(num(n, 22) for n in (19, 20, 21, 22)), NEXT_OFF),
}
TOTAL = 22

# (이름, 페이지, 라이브를 비트는 함수) — 하나하나가 결정 53의 조건이거나 번호 규칙이다
MUTANTS = [
    ("현재 페이지 표시가 span.selected가 아니다", 9, lambda s: s.replace('class="selected"', 'class="current"')),
    ("현재 페이지가 span 없이 맨 숫자다", 1, lambda s: s.replace('<span class="selected">1</span>', "1")),
    ("생략 부호에 href가 생겼다", 9, lambda s: s.replace('<a class="paging-num" >', '<a class="paging-num" href="#">', 1)),
    ("끝 클래스가 밑줄이다(no_more_prev)", 1, lambda s: s.replace("no-more-prev", "no_more_prev")),
    ("끝 클래스가 밑줄이다(no_more_next)", 22, lambda s: s.replace("no-more-next", "no_more_next")),
    ("끝인데 href가 있다", 22, lambda s: s.replace('paging-next no-more-next" >', 'paging-next no-more-next" href="#">')),
    ("이전이 끝이 아닌데 비활성이다", 9, lambda s: s.replace('paging-prev " href="/?page=8"', 'paging-prev no-more-prev"')),
    ("창이 ±2로 줄었다(12가 빠짐)", 9, lambda s: s.replace(num(12, 9), "")),
    ("생략 부호 글자가 바뀌었다(…)", 9, lambda s: s.replace("···", "…")),
    ("nav.paging이 없다", 1, lambda s: s.replace('class="paging"', 'class="pager"')),
]


def live30():
    """라이브가 30페이지로 늘었을 때 — 숫자만 다르고 모양은 같다. 거짓 경고가 나면 안 된다."""
    return {
        1: LIVE[1].replace("/?page=22", "/?page=30").replace(">22<", ">30<"),
        9: LIVE[9].replace("/?page=22", "/?page=30").replace(">22<", ">30<"),
        30: nav(prev_on(29), num(1, 30) + ELL + "".join(num(n, 30) for n in (27, 28, 29, 30)), NEXT_OFF),
    }


# verify_paging_fixture를 그대로 돌린다(fetch만 바꿔치기) — 대조기 바깥의 짝짓기·총수·못 받은 페이지 처리까지.
# (이름, 홈 html, {페이지: html 또는 None(=404)}, 기대: "same" 같다 · "warn" 경고 · "partial" 일부만 대조)
def e2e_cases():
    l30 = live30()
    return [
        ("라이브 그대로 — 1·9·22 같다", LIVE[1], {9: LIVE[9], 22: LIVE[22]}, "same"),
        ("라이브 30쪽 — 숫자만 늘었다", l30[1], {9: l30[9], 30: l30[30]}, "same"),
        ("9페이지를 못 받았다 — 「1·9·22 같다」라고 하면 안 된다", LIVE[1], {9: None, 22: LIVE[22]}, "partial"),
        ("9페이지의 selected가 바뀌었다", LIVE[1], {9: LIVE[9].replace('"selected"', '"current"'), 22: LIVE[22]}, "warn"),
        ("홈 번호가 깨져 총수를 못 읽는다 — 미검증으로 숨지 않는다",
         LIVE[1].replace('<span class="">2</span>', '<span class="">&#32;2</span>'), {}, "warn"),
        ("링크가 data-href로 옮겨 갔다", LIVE[1].replace(' href="', ' data-href="'), {9: LIVE[9], 22: LIVE[22]}, "warn"),
    ]


def run_e2e(label, home, pages, want):
    for lst in (V.ERRORS, V.WARNINGS, V.INFO, V.UNVERIFIED):
        del lst[:]

    def fake_fetch(url, **_kw):
        doc = pages.get(int(url.rsplit("=", 1)[1]))
        return (200, doc, url) if doc else (404, "", url)
    V.fetch = fake_fetch
    V.time = types.SimpleNamespace(sleep=lambda _s: None)
    V.verify_paging_fixture("https://x.example", home)
    warned = [w for w in V.WARNINGS if w["code"] == "V018"]
    same = [m for m in V.INFO if m.startswith("페이징 —")]
    unv = [u for u in V.UNVERIFIED if u["code"] == "V018"]
    got = ("warn" if warned else
           "partial" if same and "나머지는 대조하지 못했다" in same[0] and unv else
           "same" if same and not unv else "?")
    ok = got == want
    print(("  OK  " if ok else "  !!  ") + "V018 끝까지 — %s (기대 %s, 결과 %s)%s" % (
        label, want, got, "" if ok else ": " + repr(warned or same or unv)))
    return not ok


def main():
    mod = V.load_renderer()
    if mod is None:
        print("  !!  render.py를 불러오지 못했다")
        sys.exit(1)
    block, lit = V.skin_paging()
    fixtures = V.fixture_navs(mod, block)
    fails = 0
    if sorted(fixtures) != [1, 9, mod.PAGING_TOTAL]:
        print("  !!  프리뷰가 그리는 페이지가 1·9·끝이 아니다: %s" % sorted(fixtures))
        sys.exit(1)

    def fixture_for(cur):
        return fixtures[mod.PAGING_TOTAL if cur == TOTAL else cur]

    for cur, live in sorted(LIVE.items()):
        got = V.paging_drift(fixture_for(cur), live, cur, TOTAL, mod.paging_items, lit)
        ok = not got
        fails += not ok
        print(("  OK  " if ok else "  !!  ") + "라이브 %d페이지(2026-10-09) ↔ 프리뷰 — 같아야 함%s"
              % (cur, "" if ok else ": " + "; ".join(got)))
    for label, cur, f in MUTANTS:
        mutated = f(LIVE[cur])
        assert mutated != LIVE[cur], "변이가 아무것도 바꾸지 않았다: " + label
        got = V.paging_drift(fixture_for(cur), mutated, cur, TOTAL, mod.paging_items, lit)
        ok = bool(got)
        fails += not ok
        print(("  OK  " if ok else "  !!  ") + "갈림을 잡아야 함 — %s%s" % (label, "" if ok else " (놓쳤다)"))

    # 스킨이 앵커에 class를 더해도(배포 전이라 라이브엔 없다) 티스토리의 갈림으로 읽지 않는다
    fx = fixture_for(1).replace("paging-prev ", "paging-prev paging-arrow ", 1)
    got = V.paging_drift(fx, LIVE[1], 1, TOTAL, mod.paging_items, lit | {"paging-arrow"})
    fails += bool(got)
    print(("  OK  " if not got else "  !!  ") + "스킨이 글자로 쓴 class는 상태로 세지 않는다%s"
          % ("" if not got else ": " + "; ".join(got)))

    for case in e2e_cases():
        fails += run_e2e(*case)
    print("\n실패 %d건" % fails)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
