#!/usr/bin/env python3
"""BND009가 **실제로 켜지는지** 확인한다.

`BND009`는 `skin.html`이 내보내는 클래스에 CSS 규칙이 있는지 본다. 이 축은
2026-08-27까지 통째로 비어 있었다 — `BND004`는 JS가 *찾는* 이름만, `BND006`은
JS가 *만드는* 이름만 보므로 **마크업이라는 가장 큰 표면(142종)이 어느 쪽에도
안 걸렸다.**

예외 목록이 있는 검사는 «켜지는가»와 «과하게 켜지지 않는가»를 같이 봐야 한다.
그래서 "떠야 한다" 케이스와 **"뜨면 안 된다"** 케이스를 함께 둔다
(`BND008`의 오탐 케이스와 같은 이유).

사용: python3 .claude/skills/skin-qa-check/scripts/test-markup-css.py
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
SKIN = "src/skin.html"
DOC = "docs/hooks.md"

HEADING = "### CSS 규칙이 없는 것이 정상인 마크업 클래스"


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


def edit_dir(root, rel, fn):
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


def messages(res, code):
    return [it["message"] for it in res["errors"] + res["warnings"] if it["code"] == code]


# ─────────────────────────────── 케이스 ───────────────────────────────

def m_markup_renamed(root):
    """마크업에서만 이름을 바꿨다. CSS는 죽은 이름을 붙들고 있다 —
    이 검사가 존재하는 이유 그 자체다."""
    edit(root, SKIN, lambda s: s.replace('class="post-title"', 'class="card-title"'))


def m_css_gone(root):
    """CSS 규칙만 지웠다. 마크업은 계속 그 클래스를 내보낸다."""
    edit_dir(root, CSS_DIR, lambda s: s.replace(".post-title", ".xx-title"))


def m_css_in_declaration(root):
    """규칙은 없고 **선언 값에만** 이름이 남았다. 그건 규칙이 아니다."""
    m_css_gone(root)
    with open(os.path.join(root, CSS_DIR, "components.css"), "a", encoding="utf-8") as f:
        f.write('\n.debug-probe::after { content: ".post-title"; }\n')


def m_css_prefix_only(root):
    """`.post-title` → `.post-title-main`. 부분일치로 통과하면 안 된다."""
    edit_dir(root, CSS_DIR, lambda s: s.replace(".post-title", ".post-title-main"))


def m_exception_no_reason(root):
    """예외 줄에서 이유를 지운다. 이름만 적힌 줄은 예외가 아니다 (결정 40)."""
    edit(root, DOC, lambda s: s.replace(
        "- `.postnav-prev` — `.postnav-item`의 기본 배치가",
        "- `.postnav-prev`\n  `.postnav-item`의 기본 배치가", 1))


def m_heading_gone(root):
    """예외 목록 제목을 바꾼다. 검사가 조용히 꺼지지 않고 **시끄럽게** 실패해야 한다."""
    edit(root, DOC, lambda s: s.replace(HEADING, "### 규칙 없는 마크업 클래스", 1))


def m_heading_quoted_in_prose(root):
    """제목을 **산문에 인용만** 한다. 그것을 목록으로 착각하면 안 된다 —
    첫 판이 부분문자열로 찾다가 `####`로 승격시킨 제목까지 통과시켰다."""
    m_heading_gone(root)
    edit(root, DOC, lambda s: s.replace(
        "## 8. 상태 클래스 한눈에",
        "예외는 「%s」 절에 적는다.\n\n## 8. 상태 클래스 한눈에" % HEADING[4:], 1))


def m_new_container(root):
    """규칙 없는 컨테이너 클래스를 마크업에 새로 넣는다.
    예외에 없으므로 떠야 한다 — 「아직 안 한 일」이 조용히 지나가면 안 된다."""
    edit(root, SKIN, lambda s: s.replace(
        '<main class="layout" id="main">',
        '<main class="layout brand-new-wrap" id="main">', 1))


# ── 뜨면 **안 되는** 케이스 ──

def m_exempt_still_quiet(root):
    """예외에 등재된 이름(`.side-count`)의 규칙이 원래 없다. 조용해야 한다."""
    return None  # 기준선과 같다. 이름만 다르게 두어 의도를 남긴다


def m_tistory_class_in_markup(root):
    """클래스 자리가 통째로 치환자인 것(`[##_list_style_##]`·`[##_tag_class_##]`)은
    값이 티스토리에서 온다. 우리가 규칙을 보장할 수 없으므로 잡으면 안 된다."""
    edit(root, SKIN, lambda s: s.replace(
        '<div class="post-list [##_list_style_##]">',
        '<div class="post-list [##_list_style_##] [##_list_conform_##]">', 1))


def m_comment_only_class(root):
    """**주석 안**의 class 속성은 렌더되지 않는다. 잡으면 오탐이다."""
    edit(root, SKIN, lambda s: s.replace(
        '<footer class="site-footer">',
        '<!-- 예전에는 <div class="footer-legacy-wrap"> 였다 -->\n<footer class="site-footer">', 1))


CASES = [
    # (이름, 변형, 기대 문자열 or False)
    ("기준선 — 손대지 않은 저장소",           None,                     False),
    ("마크업만 개명, CSS는 그대로",           m_markup_renamed,         ".card-title"),
    ("CSS 규칙만 삭제",                       m_css_gone,               ".post-title"),
    ("이름이 선언 값에만 남음",               m_css_in_declaration,     ".post-title"),
    ("CSS에 접두만 남음",                     m_css_prefix_only,        ".post-title"),
    ("규칙 없는 새 컨테이너 클래스",          m_new_container,          ".brand-new-wrap"),
    ("예외에 이유가 없음",                    m_exception_no_reason,    ".postnav-prev"),
    ("예외 목록 제목이 사라짐",               m_heading_gone,           "찾지 못했다"),
    ("제목이 산문에 인용만 되어 있음",        m_heading_quoted_in_prose, "찾지 못했다"),
    # 뜨면 안 되는 것들
    ("예외 등재분은 조용하다",                m_exempt_still_quiet,     False),
    ("클래스 자리가 치환자",                  m_tistory_class_in_markup, False),
    ("주석 안의 class 속성",                  m_comment_only_class,     False),
]


def main():
    failed = 0
    for name, mutate, want in CASES:
        tmp = tempfile.mkdtemp(prefix="markup-css-")
        try:
            build_fixture(tmp)
            if mutate:
                mutate(tmp)
            got = messages(run(tmp), "BND009")
            problem = None
            if want is False:
                if got:
                    problem = "뜨면 안 되는데 떴다: %s" % got[0][:100]
            elif not got:
                problem = "떠야 하는데 조용했다"
            elif not any(want in g for g in got):
                problem = "떴지만 '%s'를 짚지 않았다: %s" % (want, got[0][:100])
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
