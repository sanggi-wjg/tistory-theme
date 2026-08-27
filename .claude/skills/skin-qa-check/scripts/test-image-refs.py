#!/usr/bin/env python3
"""TOK007이 **실제로 켜지는지**, 그리고 **엉뚱한 것을 잡지 않는지** 확인한다.

`test-empty-decor.py`와 같은 이유로 있다 — 린트를 더할 때 물어야 할 것은
"규칙을 썼는가"가 아니라 "그 규칙이 이 조건을 재현하는가"다(CLAUDE.md).

TOK007이 보는 실패는 **화면에도 린트에도 안 나타나던 것**이다. 기본 이미지가
`data:` 인라인에서 업로드 WebP 30장으로 바뀌면서(결정 5·6 개정) "변수는 정의돼
있는데 파일이 없다"가 가능해졌다. CSS는 `url()`이 404여도 조용하다.

「뜨면 안 되는」 케이스가 절반인 이유는 이 검사가 **꺼질 수 있기** 때문이다.
dist가 없으면 안 도는 것이 정상인데, 안 도는 것과 통과하는 것을 구분하지
않으면 «초록불인데 아무것도 안 보는 상태»가 된다 (결정 40).

사용: python3 .claude/skills/skin-qa-check/scripts/test-image-refs.py
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

STYLE = "dist/style.css"
IMAGES = "dist/images"
REF_RE = re.compile(r"""url\(\s*['"]?((?:\.{1,2}/)*images/[^'")]+?)['"]?\s*\)""")


def build_fixture(dst):
    """저장소 사본. 합성 픽스처로 대체하지 않는다 —
    실제 빌드 산출물을 보지 않으면 이 검사가 무엇을 보는지 증명하지 못한다."""
    for d in ("src", "docs", "data"):
        shutil.copytree(os.path.join(REPO, d), os.path.join(dst, d))
    os.makedirs(os.path.join(dst, "dist"))
    shutil.copy(os.path.join(REPO, STYLE), os.path.join(dst, STYLE))
    shutil.copytree(os.path.join(REPO, IMAGES), os.path.join(dst, IMAGES))


def refs(root):
    css = open(os.path.join(root, STYLE), encoding="utf-8").read()
    return [m.group(1) for m in REF_RE.finditer(css)]


def edit(root, rel, fn):
    p = os.path.join(root, rel)
    s = open(p, encoding="utf-8").read()
    out = fn(s)
    assert out != s, "변형이 아무것도 바꾸지 못했다: %s" % rel
    open(p, "w", encoding="utf-8").write(out)


def run(root):
    r = subprocess.run([sys.executable, LINT, "--json"], cwd=root,
                       capture_output=True, text=True)
    if not r.stdout.strip():
        raise AssertionError("lint.py가 아무것도 내지 않았다:\n%s" % r.stderr[-800:])
    return json.loads(r.stdout)


def codes(res, code):
    return [it["message"] for it in res["errors"] + res["warnings"] if it["code"] == code]


# ─────────────────────────────── 변형 ───────────────────────────────

def m_file_gone(root):
    """업로드를 한 장 빠뜨린 상태. 스킨 편집기에서 가장 흔한 실수다."""
    name = os.path.basename(refs(root)[0])
    os.remove(os.path.join(root, IMAGES, name))
    return name


def m_version_bump(root):
    """참조만 다음 버전으로 올린 상태 — package.json의 placeholderVersion을
    올리고 파일을 다시 만들지 않으면 정확히 이 모양이 된다."""
    bumped = []

    def bump(s):
        return re.sub(r"\.v(\d+)\.webp",
                      lambda m: bumped.append(".v%d.webp" % (int(m.group(1)) + 1)) or bumped[-1],
                      s, count=1)
    edit(root, STYLE, bump)
    return bumped[0]


def m_dist_gone(root):
    """dist를 통째로 지운다. 검사가 **안 도는** 것이 정상이다 —
    images/ 경로는 dist 기준 상대경로라 src에는 판정할 근거가 없다."""
    shutil.rmtree(os.path.join(root, "dist"))


# (이름, 변형, TOK007에 있어야 할 문자열 / False = 뜨면 안 된다)
CASES = [
    ("기준선 — 손대지 않은 사본",          None,           False),
    ("업로드 누락 — webp 한 장 삭제",       m_file_gone,    True),
    ("버전 불일치 — 참조만 .v+1 로",        m_version_bump, True),
    ("dist가 없으면 안 돈다",               m_dist_gone,    False),
]


def preflight():
    """빌드가 새 구조가 아니면 **실패한다.** 조용히 통과하면 이 테스트는
    "검사가 있다"만 증명하고 "검사가 이 조건을 본다"는 증명하지 못한다."""
    for rel in (STYLE, IMAGES):
        if not os.path.exists(os.path.join(REPO, rel)):
            print("❌ %s 가 없다 — `npm run build` 를 먼저 돌려라." % rel)
            sys.exit(1)
    if not refs(REPO):
        print("❌ dist/style.css에 url(./images/…) 참조가 하나도 없다.")
        print("   빌드가 새 구조가 아니다(기본 이미지가 아직 data: 인라인이다) — "
              "`npm run build` 를 먼저 돌려라.")
        print("   여기서 통과시키면 TOK007이 켜지는지 아닌지를 아무도 모르게 된다.")
        sys.exit(1)


def main():
    preflight()
    failed = 0
    for name, mutate, want in CASES:
        tmp = tempfile.mkdtemp(prefix="imgref-fixture-")
        try:
            build_fixture(tmp)
            needle = mutate(tmp) if mutate else None
            got = codes(run(tmp), "TOK007")
            problem = None
            if want is False:
                if got:
                    problem = "뜨면 안 되는데 떴다: %s" % got[0][:120]
            elif not got:
                problem = "떠야 하는데 조용했다"
            elif len(got) != 1:
                problem = "TOK007이 %d건 떴다 — 1건이어야 한다" % len(got)
            elif needle and needle not in got[0]:
                problem = "떴지만 '%s'를 짚지 않았다: %s" % (needle, got[0][:120])
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
