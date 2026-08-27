#!/usr/bin/env python3
"""BND008이 **실제로 켜지는지**, 그리고 **엉뚱한 것을 잡지 않는지** 확인한다.

`test-js-dom-classes.py`와 같은 이유로 있다 — 린트를 더할 때 물어야 할 것은
"규칙을 썼는가"가 아니라 "그 규칙이 이 조건을 재현하는가"다(CLAUDE.md).

BND008은 오탐이 특히 쉬운 자리다. 첫 판이 `.entry-tags a::before`를 잡았는데,
거기 장식은 **자손** <a>에 붙어 있어서 치환자가 비면 <a>째 사라진다 — 잡을
대상이 아니었다. 그래서 이 파일에는 "떠야 한다" 케이스와 "뜨면 안 된다"
케이스가 같이 있다.

사용: python3 .claude/skills/skin-qa-check/scripts/test-empty-decor.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LINT = os.path.join(HERE, "lint.py")
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

CSS = "src/styles/components.css"
SKIN = "src/skin.html"


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


def run(root):
    r = subprocess.run([sys.executable, LINT, "--json"], cwd=root,
                       capture_output=True, text=True)
    return json.loads(r.stdout)


def codes(res, code):
    return [it["message"] for it in res["errors"] + res["warnings"] if it["code"] == code]


# ─────────────────────────────── 변형 ───────────────────────────────

def m_guard_gone(root):
    """홈 카드의 :empty 가드를 지운다 — 결함이 있던 그때 상태."""
    edit(root, CSS, lambda s: s.replace(".post-rp:empty { display: none; }", ""))


def m_side_guard_gone(root):
    """사이드바 가드를 지운다. :empty와 :has()가 **따로** 선 두 규칙이다(결정 48 —
    한 선택자 목록으로 묶으면 :has 미지원 브라우저에서 통째로 죽는다). 둘 다 지워야
    가드가 없는 상태가 된다 — 하나만 남아도 BND008은 가드가 있다고 본다."""
    edit(root, CSS, lambda s: s
         .replace(".side-rp:empty { display: none; }", "")
         .replace(".side-rp:has(> span:empty) { display: none; }", ""))


def m_guard_in_comment(root):
    """가드를 주석 안으로만 남긴다 — 살아 있는 규칙이 아니다."""
    edit(root, CSS, lambda s: s.replace(
        ".post-rp:empty { display: none; }",
        "/* .post-rp:empty { display: none; } */"))


def m_new_decor_no_guard(root):
    """장식을 새로 더한다. 가드를 잊으면 다음 사람이 같은 실패를 반복한다."""
    edit(root, CSS, lambda s: s + '\n.post-date::before { content: "작성 "; }\n')


def m_label_in_markup(root):
    """라벨을 마크업으로 옮기면 이 검사의 대상이 아니다 —
    치환자만 담은 요소가 아니게 되기 때문이다."""
    edit(root, CSS, lambda s: s.replace(".post-rp:empty { display: none; }", ""))
    edit(root, SKIN, lambda s: s.replace(
        '<span class="post-rp">[##_list_rep_rp_cnt_##]</span>',
        '<span class="post-rp">댓글 [##_list_rep_rp_cnt_##]</span>'))


def m_padded_substitution(root):
    """치환자를 제 줄로 내린다. 가드는 그대로 있지만 **죽는다** —
    값이 사라져도 공백 텍스트 노드가 남아 :empty가 절대 참이 되지 않는다
    (layout.css:9의 함정). 초록불인 채로 결함이 돌아오는 자리다."""
    edit(root, SKIN, lambda s: s.replace(
        '<span class="post-rp">[##_list_rep_rp_cnt_##]</span>',
        '<span class="post-rp">\n                [##_list_rep_rp_cnt_##]\n              </span>'))


def m_padded_but_has_guard(root):
    """공백이 있어도 :has() 가드면 산다 — 자식 노드를 보는 선택자라
    공백 텍스트 노드에 걸리지 않는다. 사이드바가 이미 그 형태다."""
    edit(root, SKIN, lambda s: s.replace(
        '<span class="side-rp">[##_rctps_rep_rp_cnt_##]</span>',
        '<span class="side-rp">\n                [##_rctps_rep_rp_cnt_##]\n              </span>'))


def m_descendant_decor(root):
    """자손을 꾸미는 장식은 잡지 않는다.
    `.entry-tags`에는 :empty 가드가 **없지만** 장식이 `.entry-tags a::before`라
    치환자가 비면 <a>째 사라진다. 첫 판이 여기서 오탐했다."""
    return None  # 저장소 그대로가 이미 이 조건이다


# (이름, 변형, BND008에 있어야 할 문자열 / False = 뜨면 안 된다)
CASES = [
    ("기준선 — 손대지 않은 저장소",          None,                  False),
    ("홈 카드 가드 삭제",                    m_guard_gone,          "post-rp"),
    ("사이드바 :has() 가드 삭제",            m_side_guard_gone,     "side-rp"),
    ("가드가 주석 안에만 있음",              m_guard_in_comment,    "post-rp"),
    ("장식만 새로 더함",                     m_new_decor_no_guard,  "post-date"),
    ("라벨이 마크업에 있으면 대상 아님",     m_label_in_markup,     False),
    ("자손 장식은 잡지 않는다",              m_descendant_decor,    False),
    ("치환자 앞뒤 공백 — 가드가 죽는다",     m_padded_substitution, "post-rp"),
    (":has() 가드는 공백에도 산다",          m_padded_but_has_guard, False),
]


def main():
    failed = 0
    for name, mutate, want in CASES:
        tmp = tempfile.mkdtemp(prefix="decor-fixture-")
        try:
            build_fixture(tmp)
            if mutate:
                mutate(tmp)
            got = codes(run(tmp), "BND008")
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
