#!/usr/bin/env python3
"""일반 부류 검사 3종 + test:codes가 실제로 켜지는가 — 저장소 사본을 망가뜨려 확인한다.

  SYN001  scripts/check-css.mjs   괄호(파일 끝·시작 `}`)·속성 오타·값 오타
  SYN002  lint.py                 닫는 태그 삭제·닫지 않는 <div>·자기 닫힘 <div/>
  BND004  lint.py                 마크업+CSS에서만 개명(접두 공유)
  test:codes                      lint.py에서 호출을 지우면 빨간불

규칙을 썼다는 것과 그 규칙이 조건을 재현한다는 것은 다르다(결정 40). 변형은 **append·삭제**
같은 안정된 앵커만 쓴다 — 살아 있는 문자열을 하드코딩하면 정당한 리팩터가 이 테스트를 깨뜨린다
(하네스 리뷰 6번 — test-empty-decor.py가 `.side-rp` 규칙을 쪼개자 깨졌다).

  python3 .claude/skills/skin-qa-check/scripts/test-syntax-checks.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
LINT_REL = os.path.join(".claude", "skills", "skin-qa-check", "scripts", "lint.py")
CODES_REL = os.path.join(".claude", "skills", "skin-qa-check", "scripts", "test-lint-codes.py")
SKILL_REL = os.path.join(".claude", "skills", "skin-qa-check", "SKILL.md")
CHECK_CSS = os.path.join("scripts", "check-css.mjs")


def make_copy():
    tmp = tempfile.mkdtemp(prefix="syntax-")
    for d in ("src", "docs", "data", "scripts"):
        shutil.copytree(os.path.join(ROOT, d), os.path.join(tmp, d))
    os.makedirs(os.path.join(tmp, ".claude", "skills", "skin-qa-check", "scripts"))
    for rel in (LINT_REL, CODES_REL, SKILL_REL):
        shutil.copy(os.path.join(ROOT, rel), os.path.join(tmp, rel))
    if os.path.isdir(os.path.join(ROOT, "dist")):
        shutil.copytree(os.path.join(ROOT, "dist"), os.path.join(tmp, "dist"))
    os.symlink(os.path.join(ROOT, "node_modules"), os.path.join(tmp, "node_modules"))
    return tmp


def edit(root, rel, fn):
    p = os.path.join(root, rel)
    s = open(p, encoding="utf-8").read()
    out = fn(s)
    assert out != s, "변형이 아무것도 바꾸지 못했다: %s" % rel
    open(p, "w", encoding="utf-8").write(out)


def lint_codes(root, code):
    r = subprocess.run([sys.executable, LINT_REL, "--json"], cwd=root, capture_output=True, text=True)
    d = json.loads(r.stdout)
    return [it["message"] for it in d["errors"] + d["warnings"] if it["code"] == code]


def css_check(root):
    r = subprocess.run(["node", CHECK_CSS], cwd=root, capture_output=True, text=True)
    return r.returncode, r.stdout


CASES = []


def case(name, expect_hit):
    def deco(fn):
        CASES.append((name, fn, expect_hit))
        return fn
    return deco


# ── SYN001 ──
@case("SYN001 기준선 — 손대지 않은 사본은 0건", False)
def c_css_base(root):
    return css_check(root)[0] != 0


@case("SYN001 파일 끝 닫히지 않은 `{` (EOF가 닫아 줘도 잡아야 한다)", True)
def c_css_eof(root):
    edit(root, "src/styles/components.css", lambda s: s + "\n.x { color: var(--ink);\n")
    return css_check(root)[0] != 0


@case("SYN001 파일 시작의 여는 괄호 없는 `}`", True)
def c_css_stray(root):
    edit(root, "src/styles/base.css", lambda s: "}\n" + s)
    return css_check(root)[0] != 0


@case("SYN001 속성 이름 오타 + 값 오타", True)
def c_css_typo(root):
    edit(root, "src/styles/base.css", lambda s: s + "\n.y { colr: red; display: flx; }\n")
    rc, out = css_check(root)
    return rc != 0 and "colr" in out and "flx" in out


@case("SYN001 오탐 방지 — 문자열 안 줄 잇기와 url() 안의 `{`는 정상", False)
def c_css_ok(root):
    edit(root, "src/styles/base.css",
         lambda s: s + '\n.z::before { content: "a\\\nb"; background: url(data:image/svg+xml,%3Csvg%3E{); }\n')
    return css_check(root)[0] != 0


# ── SYN002 ──
@case("SYN002 닫는 태그 하나 삭제", True)
def c_html_close(root):
    edit(root, "src/skin.html", lambda s: s.replace("</section>", "", 1))
    return bool(lint_codes(root, "SYN002"))


@case("SYN002 닫지 않는 <div> 삽입", True)
def c_html_open(root):
    edit(root, "src/skin.html", lambda s: s.replace("<main ", "<div class=\"x\"><main ", 1))
    return bool(lint_codes(root, "SYN002"))


@case("SYN002 자기 닫힘 <div/> — 브라우저는 여는 태그로 읽는다", True)
def c_html_selfclose(root):
    edit(root, "src/skin.html", lambda s: s.replace("<main ", "<div class=\"x\"/><main ", 1))
    return bool(lint_codes(root, "SYN002"))


# ── BND004 ──
@case("BND004 마크업+CSS에서만 개명(접두 공유) — JS는 옛 이름", True)
def c_bnd004(root):
    edit(root, "src/skin.html", lambda s: s.replace('class="entry-body"', 'class="entry-body-v2"'))
    for f in os.listdir(os.path.join(root, "src", "styles")):
        edit(root, os.path.join("src", "styles", f),
             lambda s: re.sub(r"\.entry-body(?![\w-])", ".entry-body-v2", s)) if ".entry-body" in open(os.path.join(root, "src", "styles", f), encoding="utf-8").read() else None
    return any("entry-body" in m for m in lint_codes(root, "BND004"))


# ── test:codes ──
@case("test:codes — lint.py에서 규칙 호출을 지우면 빨간불", True)
def c_codes(root):
    edit(root, LINT_REL, lambda s: re.sub(r'err\("TIS004"', 'err("TISXXX"', s))
    r = subprocess.run([sys.executable, CODES_REL], cwd=root, capture_output=True, text=True)
    return r.returncode != 0 and "TIS004" in r.stdout


def main():
    if not os.path.isdir(os.path.join(ROOT, "node_modules", "css-tree")):
        print("❌ node_modules/css-tree 가 없다 — npm install 먼저")
        sys.exit(1)
    failed = 0
    for name, fn, expect in CASES:
        tmp = make_copy()
        try:
            hit = fn(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        ok = hit == expect
        print("  %s  %s" % ("✅" if ok else "❌", name))
        if not ok:
            failed += 1
    print("\n%d/%d 통과" % (len(CASES) - failed, len(CASES)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
