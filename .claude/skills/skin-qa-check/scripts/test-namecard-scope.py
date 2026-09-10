#!/usr/bin/env python3
"""TIS005가 **실제로 켜지는지**, 그리고 **엉뚱한 것을 잡지 않는지** 확인한다.

`test-empty-decor.py`·`test-js-dom-classes.py`와 같은 이유로 있다 — 린트를 더할 때
물어야 할 것은 "규칙을 썼는가"가 아니라 "그 규칙이 이 조건을 재현하는가"다(CLAUDE.md).
새 린트는 자기가 켜지는지 스스로 증명하지 못한다.

TIS005는 오탐·미탐이 둘 다 쉬운 자리다.
- **미탐**: `… .tt_btn_subscribe`는 `… .tt_btn_subscribe.type2`의 부분문자열이다.
  단순 `in` 검사면 구독 중 상태만 덮고 기본 상태를 안 덮어도 통과한다.
- **오탐**: 접두 **앞에** 뭔가를 더 붙이거나(더 강한 특이도) 선택자를 쉼표로 묶는 것은
  정상이다. 그걸 잡으면 CSS를 쓸 수 없게 된다.

⚠ 실저장소의 CSS 문자열을 하드코딩하지 않는다. 2026-08-27에 `test-empty-decor.py`가
   그렇게 했다가 `.side-rp` 규칙을 둘로 쪼개자 깨졌다. 여기서는 접두를 `lint.py`의
   상수에서, marker를 `data/tistory-hardcoded-colors.json`에서 읽어 **그것으로**
   변형을 만든다 — CSS 작성자가 주석·순서·값을 바꿔도 테스트는 따라간다.

사용: python3 .claude/skills/skin-qa-check/scripts/test-namecard-scope.py
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LINT = os.path.join(HERE, "lint.py")
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

CSS = "src/styles/tistory.css"
KNOWN = "data/tistory-hardcoded-colors.json"


def load_lint_module():
    spec = importlib.util.spec_from_file_location("_lint_under_test", LINT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LINTMOD = load_lint_module()


def spec_of(root=REPO):
    """접두는 **json이 정본**이고 `lint.py`의 `NAMECARD_PREFIX`는 그것이 없을 때 쓰는
    기본값일 뿐이다 — 린트와 같은 순서로 읽어야 둘이 갈렸을 때 테스트가 린트를 따라간다."""
    d = json.load(open(os.path.join(root, KNOWN), encoding="utf-8"))
    return d.get("namecardPrefix", LINTMOD.NAMECARD_PREFIX), d.get("namecardRules", [])


PREFIX, RULES = spec_of()


def needle(marker):
    return PREFIX + (" " + marker if marker else "")


def marker_of(component):
    for r in RULES:
        if r["component"] == component:
            return r["marker"]
    raise AssertionError("json에 없는 component: %s" % component)


def build_fixture(dst):
    for d in ("src", "docs", "data"):
        shutil.copytree(os.path.join(REPO, d), os.path.join(dst, d))
    os.makedirs(os.path.join(dst, "dist"))
    shutil.copy(os.path.join(REPO, "dist", "style.css"),
                os.path.join(dst, "dist", "style.css"))


def edit(root, rel, fn):
    p = os.path.join(root, rel)
    s = open(p, encoding="utf-8").read()
    out = fn(s)
    assert out != s, "변형이 아무것도 바꾸지 못했다: %s" % rel
    open(p, "w", encoding="utf-8").write(out)


def find_rule(css, sel):
    """`sel`로 시작하는 규칙 하나의 (시작, 끝) — 선택자 끝이 `{`인 것만 본다."""
    i = css.find(sel)
    while i != -1:
        j = i + len(sel)
        while j < len(css) and css[j] in " \t\r\n":
            j += 1
        if j < len(css) and css[j] == "{":
            end = css.find("}", j)
            assert end != -1, "닫는 중괄호를 찾지 못했다: %s" % sel
            return i, end + 1
        i = css.find(sel, i + 1)
    raise AssertionError("규칙을 찾지 못했다 (CSS가 바뀌었나): %s" % sel)


def run(root):
    r = subprocess.run([sys.executable, LINT, "--json"], cwd=root,
                       capture_output=True, text=True)
    # 린트는 오류가 있으면 1, 없으면 0으로 끝난다. 그 밖의 코드는 **린트가 죽은 것**이다
    # (import 오류·JSON 파싱 실패 등). 그대로 두면 json.loads가 나는 자리에서
    # 「JSONDecodeError」만 보이고 진짜 원인인 스택트레이스는 버려진다.
    if r.returncode not in (0, 1):
        raise AssertionError("린트가 비정상 종료했다 (rc=%d)\n--- stderr ---\n%s"
                             % (r.returncode, r.stderr.strip()[:2000]))
    return json.loads(r.stdout)


def codes(res, code):
    return [it["message"] for it in res["errors"] + res["warnings"] if it["code"] == code]


# ─────────────────────────────── 변형 ───────────────────────────────

def m_prefix_shortened(root):
    """접두에서 `.entry-main `을 뗀다 — (0,3,0) → (0,2,0). 화면상으로는 지금
    프리뷰 순서에서 이길 수도 있다(우리가 뒤일 때). 특이도로 지는 것은 눈에 안 보인다."""
    short = PREFIX.replace(".entry-main ", "", 1)
    assert short != PREFIX
    edit(root, CSS, lambda s: s.replace(PREFIX, short))


def m_single_marker_weak(root):
    """블로그 이름 한 자리만 약하게 쓴다. 나머지 다섯은 멀쩡하다 —
    «부분적으로 동작하는 것이 더 찾기 어렵다»(결정 35)."""
    m = marker_of("블로그 이름")
    edit(root, CSS, lambda s: s.replace(needle(m), ".tt_box_namecard " + m))


def m_base_button_dropped(root):
    """구독 버튼 **기본** 규칙만 지운다. `.type2`와 ` .tt_txt_g`는 남는다 —
    부분문자열 검사였다면 여기서 통과했을 자리다(이 테스트의 핵심 케이스)."""
    def cut(s):
        a, b = find_rule(s, needle(marker_of("구독 버튼 테두리")))
        return s[:a] + s[b:]
    edit(root, CSS, cut)


def m_rule_in_comment(root):
    """설명 규칙을 주석 안으로만 남긴다 — 살아 있는 규칙이 아니다."""
    def wrap(s):
        a, b = find_rule(s, needle(marker_of("블로그 설명")))
        return s[:a] + "/* " + s[a:b] + " */" + s[b:]
    edit(root, CSS, wrap)


def m_single_quotes(root):
    """속성 선택자를 홑따옴표로 바꾼다. CSS로는 유효하고 브라우저에서도 먹는다 —
    그런데도 잡는 것은 **의도한 엄격함**이다(TIS002·TIS003과 같다). 형식을 하나로
    못박는 대가로 검사가 확실해진다. 형식을 바꾸려면 json의 namecardPrefix를 함께 바꾼다."""
    edit(root, CSS, lambda s: s.replace('[data-tistory-react-app="Namecard"]',
                                        "[data-tistory-react-app='Namecard']"))


def m_stronger_prefix(root):
    """접두 **앞에** body id를 더한다 — 더 강해질 뿐이다. 잡으면 안 된다."""
    edit(root, CSS, lambda s: s.replace(PREFIX, "#tt-body-page " + PREFIX))


def m_comma_grouped(root):
    """선택자를 쉼표로 묶는다. 흔한 정리 방식이고 특이도는 그대로다 — 잡으면 안 된다."""
    n = needle(marker_of("블로그 설명"))

    def group(s):
        a, _ = find_rule(s, n)
        return s[:a] + n + ",\n" + s[a:]
    edit(root, CSS, group)


def m_property_swapped(root):
    """선택자는 (0,4,0) 그대로 두고 **속성만** 바꾼다 — 2026-09-10 리뷰어가 재현한 상태다.
    규칙이 버젓이 있어 「고쳤다」고 읽히는데 그 자리는 상대 #888이 그대로 이긴다.
    선택자 존재만 보던 첫 판이 여기서 오류 0을 냈다."""
    n = needle(marker_of("블로그 설명"))

    def swap(s):
        a, b = find_rule(s, n)
        return s[:a] + n + " {\n  font-size: 12px;\n}" + s[b:]
    edit(root, CSS, swap)


def m_shorthand(root):
    """`border-color`를 단축 `border`로 쓴다 — 덮은 것이 맞다. 잡으면 안 된다.
    (`background-color` ← `background`도 같다. `min-height`는 단축이 없다.)"""
    n = needle(marker_of("구독 버튼 테두리"))

    def short(s):
        a, b = find_rule(s, n)
        return s[:a] + n + " {\n  border: 1px solid var(--hairline-strong);\n}" + s[b:]
    edit(root, CSS, short)


def m_untouched(root):
    return None


# (이름, 변형, TIS005 메시지에 있어야 할 문자열 / False = 뜨면 안 된다)
CASES = [
    ("기준선 — 손대지 않은 저장소",              m_untouched,          False),
    ("접두에서 .entry-main 제거 → (0,2,0)",      m_prefix_shortened,   "카드 배경"),
    ("한 자리만 약하게 — 나머지는 멀쩡",         m_single_marker_weak, "블로그 이름"),
    ("구독 버튼 기본 규칙만 삭제(.type2는 남음)", m_base_button_dropped, "구독 버튼 테두리"),
    ("규칙이 주석 안에만 있음",                  m_rule_in_comment,    "블로그 설명"),
    ("속성 선택자 홑따옴표 — 형식 이탈",         m_single_quotes,      "카드 배경"),
    ("선택자는 그대로, 속성만 바꿈",             m_property_swapped,   "블로그 설명"),
    ("접두 앞에 body id 추가 — 더 강하다",       m_stronger_prefix,    False),
    ("쉼표로 묶은 선택자 목록",                  m_comma_grouped,      False),
    ("단축 border로 덮은 것도 덮은 것이다",      m_shorthand,          False),
]


def main():
    failed = 0
    for name, mutate, want in CASES:
        tmp = tempfile.mkdtemp(prefix="namecard-fixture-")
        try:
            build_fixture(tmp)
            if mutate:
                mutate(tmp)
            got = codes(run(tmp), "TIS005")
            problem = None
            if want is False:
                if got:
                    problem = "뜨면 안 되는데 떴다: %s" % got[0][:120]
            elif not got:
                problem = "떠야 하는데 조용했다"
            elif not any(want in g for g in got):
                problem = "떴지만 '%s'를 짚지 않았다: %s" % (want, got[0][:120])
            if problem:
                failed += 1
                print("❌ %s\n     %s" % (name, problem))
            else:
                print("✅ %s" % name)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print("\n%d/%d 통과" % (len(CASES) - failed, len(CASES)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
