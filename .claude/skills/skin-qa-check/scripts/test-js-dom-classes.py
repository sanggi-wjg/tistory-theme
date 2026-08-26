#!/usr/bin/env python3
"""BND006·BND007이 **실제로 켜지는지** 확인한다.

이 저장소에서 검증 도구가 통과 신호를 위조한 적이 세 번 있다(CLAUDE.md).
린트를 더할 때 물어야 할 것은 "규칙을 썼는가"가 아니라 **"그 규칙이 이 조건을
재현하는가"**다. 그래서 각 케이스는 저장소 사본을 일부러 망가뜨리고,
망가뜨린 그 코드가 뜨는지 본다. 초록불만 보고 넘어가지 않기 위한 장치다.

사용: python3 .claude/skills/skin-qa-check/scripts/test-js-dom-classes.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LINT = os.path.join(HERE, "lint.py")
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

CSS_DIR = "src/styles"
JS_DIR = "src/js"
DOC = "docs/hooks.md"


def build_fixture(dst):
    """린트가 읽는 것만 복사한다. dist에서 읽는 것은 style.css 하나뿐이다."""
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


def edit_dir(root, rel, fn):
    """디렉터리 안 모든 파일에 적용. 최소 한 파일은 바뀌어야 한다."""
    changed = False
    for base, _, files in os.walk(os.path.join(root, rel)):
        for f in sorted(files):
            p = os.path.join(base, f)
            s = open(p, encoding="utf-8").read()
            out = fn(s)
            if out != s:
                open(p, "w", encoding="utf-8").write(out)
                changed = True
    assert changed, "변형이 아무것도 바꾸지 못했다: %s" % rel


def run(root):
    r = subprocess.run([sys.executable, LINT, "--json"], cwd=root,
                       capture_output=True, text=True)
    return json.loads(r.stdout)


def codes(res, code):
    return [it["message"] for it in res["errors"] + res["warnings"] if it["code"] == code]


# ─────────────────────────────── 케이스 ───────────────────────────────
# (이름, 변형 함수 or None, 기대: BND006에 있어야 할 문자열 or False, BND007도 같은 식)

def m_css_gone(root):
    """CSS에서 .code-copy 규칙을 통째로 없앤다 — JS는 계속 그 클래스를 붙인다."""
    edit_dir(root, CSS_DIR, lambda s: s.replace(".code-copy", ".xxcopy"))


def m_css_prefix_only(root):
    """.code-copy → .code-copy-btn. 부분일치로 통과하면 안 된다."""
    edit_dir(root, CSS_DIR, lambda s: s.replace(".code-copy", ".code-copy-btn"))


def m_css_in_comment(root):
    """규칙은 없고 **주석에만** 이름이 남았다. 주석은 규칙이 아니다."""
    m_css_gone(root)
    with open(os.path.join(root, CSS_DIR, "components.css"), "a", encoding="utf-8") as f:
        f.write("\n/* .code-copy — 복사 버튼. 규칙은 위에 있다(고 착각하기 쉬운 자리) */\n")


def m_css_in_declaration(root):
    """규칙은 없고 **선언 값에만** 이름이 남았다."""
    m_css_gone(root)
    with open(os.path.join(root, CSS_DIR, "components.css"), "a", encoding="utf-8") as f:
        f.write('\n.debug-probe::after { content: ".code-copy"; }\n')


def m_js_renamed(root):
    """JS만 이름을 바꿨다. 문서와 CSS는 죽은 이름을 붙들고 있다."""
    edit_dir(root, JS_DIR, lambda s: s.replace("heading-anchor", "heading-anchor-v2"))


def m_doc_new_class(root):
    """문서에 클래스를 더하고 CSS를 안 썼다 — §5.6이 노리는 바로 그 순서."""
    edit(root, DOC, lambda s: s.replace(
        "| `.cat-tree` |", "| `.brand-new` | 시험용 | 어딘가 |\n| `.cat-tree` |", 1))


def m_section_renamed(root):
    """§5.6 절이 사라지면 검사가 통째로 꺼진다 — 조용히 꺼지면 안 된다."""
    edit(root, DOC, lambda s: s.replace("### 5.6 JS가 새로 만드는 DOM",
                                        "### 5.6a JS가 새로 만드는 DOM", 1))


def m_exception_no_reason(root):
    """예외 줄에서 이유를 지운다. 이름만 적힌 줄은 예외가 아니다."""
    edit(root, DOC, lambda s: re.sub(
        r"- `\.external-link` —[^\n]*\n(?:  [^\n]*\n)*", "- `.external-link`\n", s, count=1))


def m_second_exception(root):
    """예외를 하나 더 등재한다. **첫 예외 줄이 줄바꿈으로 이어져 있다** —
    이어지는 줄에서 목록이 끝났다고 판단하면 두 번째 예외가 조용히 무시된다."""
    m_css_gone(root)
    edit(root, DOC, lambda s: s.replace(
        "  손대지 않으려고 붙이는 **표식**이라 스타일이 붙을 자리가 없다.\n",
        "  손대지 않으려고 붙이는 **표식**이라 스타일이 붙을 자리가 없다.\n"
        "- `.code-copy` — 시험용. 두 번째 예외가 읽히는지 보는 자리다.\n", 1))


def m_js_comment_only(root):
    """JS에서 이름을 바꾸고 **주석에 옛 이름을 남긴다.** 주석은 사용처가 아니다."""
    m_js_renamed(root)
    with open(os.path.join(root, JS_DIR, "heading-anchor.js"), "a", encoding="utf-8") as f:
        f.write("\n// heading-anchor 는 예전 이름이다. 지금은 heading-anchor-v2.\n")


def m_exception_heading_gone(root):
    """예외 목록 제목을 지운다. 예외가 풀려 **시끄럽게** 실패해야 한다."""
    edit(root, DOC, lambda s: s.replace("**CSS 규칙이 없는 것이 정상인 클래스**",
                                        "CSS 규칙이 없는 것이 정상인 클래스", 1))


CASES = [
    ("기준선 — 손대지 않은 저장소",        None,                    False,            False),
    ("CSS 규칙 삭제",                      m_css_gone,              ".code-copy",     False),
    ("CSS에 접두만 남음",                  m_css_prefix_only,       ".code-copy",     False),
    ("이름이 주석에만 있음",               m_css_in_comment,        ".code-copy",     False),
    ("이름이 선언 값에만 있음",            m_css_in_declaration,    ".code-copy",     False),
    ("JS만 이름을 바꿈",                   m_js_renamed,            False,            ".heading-anchor"),
    ("문서에만 등재, CSS 없음",            m_doc_new_class,         ".brand-new",     ".brand-new"),
    ("§5.6 절이 사라짐",                   m_section_renamed,       "§5.6 절을",      False),
    ("예외에 이유가 없음",                 m_exception_no_reason,   ".external-link", False),
    ("예외 목록 제목이 사라짐",            m_exception_heading_gone, ".external-link", False),
    ("예외 둘, 첫째가 줄바꿈",             m_second_exception,      False,            False),
    ("JS 주석에만 옛 이름이 남음",         m_js_comment_only,       False,            ".heading-anchor"),
]


def main():
    failed = 0
    for name, mutate, want6, want7 in CASES:
        tmp = tempfile.mkdtemp(prefix="lint-fixture-")
        try:
            build_fixture(tmp)
            if mutate:
                mutate(tmp)
            res = run(tmp)
            got6, got7 = codes(res, "BND006"), codes(res, "BND007")
            problems = []
            for code, want, got in (("BND006", want6, got6), ("BND007", want7, got7)):
                if want is False:
                    if got:
                        problems.append("%s가 뜨면 안 되는데 떴다: %s" % (code, got[0][:80]))
                elif not got:
                    problems.append("%s가 떠야 하는데 조용했다" % code)
                elif not any(want in g for g in got):
                    problems.append("%s는 떴지만 '%s'를 짚지 않았다: %s"
                                    % (code, want, got[0][:80]))
            if problems:
                failed += 1
                print("❌ %s" % name)
                for p in problems:
                    print("     %s" % p)
            else:
                print("✅ %s" % name)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print("\n%d/%d 통과" % (len(CASES) - failed, len(CASES)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
